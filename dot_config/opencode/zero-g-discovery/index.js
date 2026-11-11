import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export default {
  id: "zero-g-model-discovery",
  async setup(ctx) {
    const config = JSON.parse(readFileSync(join(homedir(), ".config/opencode/opencode.json"), "utf8"));
    const provider = config.providers["zero-g"];
    const token = process.env.ZERO_G_TOKEN;
    if (!token) {
      console.warn("[zero-g] Model discovery failed: ZERO_G_TOKEN is not set");
      return;
    }

    let models;
    try {
      const url = new URL("models", `${provider.settings.baseURL.replace(/\/$/, "")}/`);
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        redirect: "error",
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = await response.json();
      if (!Array.isArray(body.data)) throw new Error("invalid model list");
      models = [...new Map(body.data.filter((model) => typeof model?.id === "string" && model.id.length > 0).map((model) => [model.id, model])).values()];
    } catch (error) {
      console.warn(`[zero-g] Model discovery failed: ${error.message}`);
      return;
    }

    await ctx.provider.transform((editor) => {
      const id = "zero-g";
      if (!editor.get(id)) {
        editor.add({
          info: { id, name: provider.name, package: provider.package, activation: "enabled", settings: provider.settings, headers: { authorization: `Bearer ${token}` } },
          models: [],
        });
      } else {
        editor.update(id, (draft) => {
          draft.headers = { ...draft.headers, authorization: `Bearer ${token}` };
        });
      }
      const existing = [...editor.get(id).models.values()];
      const existingIDs = new Set(existing.map((model) => model.id));
      editor.models.set(id, [...existing, ...models.filter((model) => !existingIDs.has(model.id)).map((model) => {
        const context = Number.isSafeInteger(model.context_window) && model.context_window > 0 ? model.context_window : 200000;
        const output = Number.isSafeInteger(model.max_output_tokens) && model.max_output_tokens > 0 ? model.max_output_tokens : Math.min(32000, context);
        const modalities = (value) => Array.isArray(value) && value.length ? value.filter((item) => typeof item === "string") : ["text"];
        const efforts = Array.isArray(model.supported_reasoning_efforts) ? model.supported_reasoning_efforts.filter((effort) => typeof effort === "string" && effort.length > 0) : [];
        return {
          id: model.id, modelID: model.id, providerID: id, name: model.display_name || model.name || model.id,
          capabilities: { tools: true, input: modalities(model.input_modalities), output: modalities(model.output_modalities) },
          variants: [...new Set(efforts)].map((effort) => ({ id: effort, settings: { reasoningEffort: effort } })),
          time: { released: 0 }, cost: [], status: "active", enabled: true,
          limit: { context, output },
        };
      })]);
    });
    await ctx.provider.reload();
  },
};
