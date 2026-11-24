import { test, expect } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type {
  Model,
  PluginContext,
  ProviderDraft,
  ProviderEditor,
} from "../dot_config/opencode/models-discovery/index.ts";

function required<T>(value: T | undefined): T {
  if (value === undefined) throw new Error("Missing fixture value");
  return value;
}

const home = mkdtempSync(join(tmpdir(), "models-discovery-"));
const previousConfig = process.env.XDG_CONFIG_HOME;
process.env.XDG_CONFIG_HOME = join(home, ".config");
mkdirSync(join(home, ".config/opencode"), { recursive: true });
const plugin = (
  await import("../dot_config/opencode/models-discovery/index.ts")
).default;

function config(providers: Record<string, unknown>) {
  writeFileSync(
    join(home, ".config/opencode/opencode.jsonc"),
    `// Commented config\n${JSON.stringify({ providers })}`,
  );
}
function fixture() {
  const providers = new Map<string, ProviderDraft>();
  const editor: ProviderEditor = {
    get: (id) => providers.get(id),
    add: ({ info, models }) =>
      providers.set(info.id, {
        ...info,
        models: new Map(models.map((model) => [model.id, model])),
      }),
    update: (id, update) => update(required(providers.get(id))),
    models: {
      set: (id, models) => {
        required(providers.get(id)).models = new Map(
          models.map((model) => [model.id, model]),
        );
      },
    },
  };
  const ctx: PluginContext = {
    location: {},
    integration: {
      connection: {
        active: async () => undefined,
        resolve: async () => undefined,
      },
    },
    provider: { transform: async (fn) => fn(editor), reload: async () => {} },
  };
  return { providers, ctx };
}
const provider = (baseURL: string, env?: string) => ({
  name: baseURL,
  package: "@opencode/ai/providers/openai-compatible",
  settings: { baseURL },
  ...(env ? { env: [env] } : {}),
});

test("discovers configured providers and preserves per-model metadata", async () => {
  const oldFetch = globalThis.fetch;
  const oldToken = process.env.TEST_DISCOVERY_TOKEN;
  process.env.TEST_DISCOVERY_TOKEN = "test-secret";
  config({
    first: provider("https://one.invalid/v1", "TEST_DISCOVERY_TOKEN"),
    second: provider("https://two.invalid/v1"),
  });
  const calls: [string, string | null][] = [];
  globalThis.fetch = (async (
    input: RequestInfo | URL,
    options?: RequestInit,
  ) => {
    const url = new URL(
      typeof input === "string" || input instanceof URL
        ? input.toString()
        : input.url,
    );
    calls.push([
      url.hostname,
      new Headers(options?.headers).get("Authorization"),
    ]);
    return Response.json({
      data:
        url.hostname === "one.invalid"
          ? [
              {
                id: "capable",
                supports_tools: true,
                input_modalities: ["text", "image"],
                output_modalities: ["text"],
                context_window: 64000,
                max_output_tokens: 4096,
                supported_reasoning_efforts: ["low", "high"],
              },
            ]
          : [
              { id: "unknown" },
              {
                id: "unsupported",
                supports_tools: false,
                input_modalities: [],
              },
            ],
    });
  }) as typeof fetch;
  try {
    const { providers, ctx } = fixture();
    await plugin.setup(ctx);
    expect(calls).toEqual([
      ["one.invalid", "Bearer test-secret"],
      ["two.invalid", null],
    ]);
    const capable = required(
      required(providers.get("first")).models.get("capable"),
    );
    expect(capable.capabilities).toEqual({
      tools: true,
      input: ["text", "image"],
      output: ["text"],
    });
    expect(capable.limit).toEqual({ context: 64000, output: 4096 });
    expect(capable.variants.map((variant) => variant.id)).toEqual([
      "low",
      "high",
    ]);
    expect(
      required(required(providers.get("second")).models.get("unsupported"))
        .capabilities,
    ).toEqual({ tools: false, input: [], output: ["text"] });
    expect(
      required(required(providers.get("second")).models.get("unknown")).limit,
    ).toEqual({
      context: 8192,
      output: 1024,
    });
  } finally {
    globalThis.fetch = oldFetch;
    if (oldToken === undefined) delete process.env.TEST_DISCOVERY_TOKEN;
    else process.env.TEST_DISCOVERY_TOKEN = oldToken;
  }
});

test("failed refresh keeps models and does not log secrets", async () => {
  const oldFetch = globalThis.fetch,
    oldWarn = console.warn;
  config({ first: provider("https://one.invalid/v1") });
  const warnings: string[] = [];
  console.warn = (message) => warnings.push(message);
  globalThis.fetch = Object.assign(
    async () => {
      throw new Error("secret-in-error");
    },
    { preconnect: oldFetch.preconnect },
  );
  try {
    const { providers, ctx } = fixture();
    providers.set("first", {
      models: new Map([["existing", { id: "existing" } as Model]]),
    });
    await plugin.setup(ctx);
    expect(required(providers.get("first")).models.has("existing")).toBe(true);
    expect(warnings).toEqual(["[models-discovery] Discovery failed for first"]);
  } finally {
    globalThis.fetch = oldFetch;
    console.warn = oldWarn;
  }
});

process.on("exit", () => {
  if (previousConfig === undefined) delete process.env.XDG_CONFIG_HOME;
  else process.env.XDG_CONFIG_HOME = previousConfig;
  rmSync(home, { recursive: true, force: true });
});
