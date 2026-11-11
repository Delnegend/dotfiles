import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const configDir = process.env.XDG_CONFIG_HOME ? join(process.env.XDG_CONFIG_HOME, "opencode") : join(homedir(), ".config/opencode");
const positive = (value) => Number.isSafeInteger(value) && value > 0;
const modalities = (value) => Array.isArray(value) ? value.filter((item) => typeof item === "string") : ["text"];

export default {
  id: "models-discovery",
  async setup(ctx) {
    const providers = {};
    try {
      for (const dir of [configDir, ctx.location?.directory, ctx.location?.directory && join(ctx.location.directory, ".opencode")].filter(Boolean)) {
        for (const file of ["opencode.json", "opencode.jsonc"]) {
          const path = join(dir, file);
          if (!existsSync(path)) continue;
          const configured = Bun.JSON5.parse(readFileSync(path, "utf8")).providers ?? {};
          for (const [id, value] of Object.entries(configured)) {
            const previous = providers[id] ?? {};
            providers[id] = { ...previous, ...value, settings: { ...previous.settings, ...value.settings }, headers: { ...previous.headers, ...value.headers } };
          }
        }
      }
    } catch {
      console.warn("[models-discovery] Invalid configuration");
      return;
    }

    const candidates = Object.entries(providers).filter(([, provider]) =>
      provider?.package === "@opencode/ai/providers/openai-compatible" && typeof provider.settings?.baseURL === "string"
    );
    const results = await Promise.all(candidates.map(async ([id, provider]) => {
      let credential;
      try {
        const connection = await ctx.integration.connection.active(id);
        credential = connection && await ctx.integration.connection.resolve(connection);
      } catch {
        console.warn(`[models-discovery] Credentials unavailable for ${id}`);
        return null;
      }
      const token = credential?.type === "key" ? credential.key : credential?.type === "oauth" ? credential.access : (provider.env ?? []).map((name) => process.env[name]).find(Boolean) || provider.settings?.apiKey;
      if (provider.env?.length && !token && !provider.headers?.Authorization && !provider.headers?.authorization) {
        console.warn(`[models-discovery] Missing credentials for ${id}`);
        return null;
      }
      try {
        const url = new URL("models", `${provider.settings.baseURL.replace(/\/$/, "")}/`);
        const headers = { ...provider.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
        const response = await fetch(url, { headers, redirect: "error", signal: AbortSignal.timeout(10000) });
        if (!response.ok) throw new Error();
        const body = await response.json();
        if (!Array.isArray(body.data)) throw new Error();
        const models = [...new Map(body.data.filter((model) => typeof model?.id === "string" && model.id.length > 0).map((model) => [model.id, model])).values()];
        if (Array.isArray(body.errors) && body.errors.length) throw new Error();
        return { id, provider, headers, models };
      } catch {
        console.warn(`[models-discovery] Discovery failed for ${id}`);
        return null;
      }
    }));

    const succeeded = results.filter(Boolean);
    if (!succeeded.length) return;
    await ctx.provider.transform((editor) => {
      for (const { id, provider, headers, models } of succeeded) {
        if (!editor.get(id)) {
          editor.add({ info: { id, name: provider.name ?? id, package: provider.package, activation: "enabled", settings: provider.settings, headers }, models: [] });
        } else if (Object.keys(headers).length) {
          editor.update(id, (draft) => { draft.headers = { ...draft.headers, ...headers }; });
        }
        const existing = editor.get(id)?.models ?? new Map();
        const discovered = models.map((model) => {
          const context = positive(model.context_window) ? model.context_window : 8192;
          const output = positive(model.max_output_tokens) ? model.max_output_tokens : Math.min(1024, context);
          const efforts = Array.isArray(model.supported_reasoning_efforts) ? model.supported_reasoning_efforts.filter((effort) => typeof effort === "string" && effort.length > 0) : [];
          return {
            id: model.id, modelID: model.id, providerID: id, name: model.display_name || model.name || model.id,
            capabilities: { tools: model.supports_tools === true, input: modalities(model.input_modalities), output: modalities(model.output_modalities) },
            variants: [...new Set(efforts)].map((effort) => ({ id: effort, settings: { reasoningEffort: effort } })),
            time: { released: 0 }, cost: [], status: "active", enabled: true,
            limit: { context, output },
          };
        });
        const ids = new Set(discovered.map((model) => model.id));
        editor.models.set(id, [...existing.values()].filter((model) => !ids.has(model.id)).concat(discovered));
      }
    });
    await ctx.provider.reload();
  },
};
