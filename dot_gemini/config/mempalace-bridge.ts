#!/usr/bin/env bun
/** Bridge agy's stdio MCP transport to MemPalace's Streamable HTTP endpoint. */
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

function loadToken(): string {
  const envToken = process.env.MEMPALACE_MCP_HTTP_TOKEN?.trim();
  if (envToken) return envToken;
  let found = "";
  try {
    const file = readFileSync(
      join(homedir(), ".config", "ai-agents", "secrets.env"),
      "utf8",
    );
    for (const rawLine of file.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      const match = line.match(
        /^(?:export\s+)?MEMPALACE_MCP_HTTP_TOKEN\s*=\s*(.*)$/,
      );
      if (!match) continue;
      let value = (match[1] ?? "").trim();
      if (
        (value.startsWith('"') && value.endsWith('"') && value.length >= 2) ||
        (value.startsWith("'") && value.endsWith("'") && value.length >= 2)
      ) {
        value = value.slice(1, -1);
      } else {
        value = value.replace(/\s+#.*$/, "").trim();
      }
      if (value && !/[\r\n]/.test(value)) found = value;
    }
  } catch {
    // Missing or unreadable secrets file; handled below.
  }
  return found;
}

const url = "https://mempalace.delnegend.com/mcp";
const token = loadToken();
if (!token) throw new Error("MEMPALACE_MCP_HTTP_TOKEN is not set");

type Message = {
  jsonrpc?: string;
  id?: string | number | null;
  method?: string;
  result?: { protocolVersion?: string };
};
let sessionId = "";
let protocolVersion = "";
const emit = (message: unknown) =>
  process.stdout.write(`${JSON.stringify(message)}\n`);

function headers(): Record<string, string> {
  const result: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-MemPalace-Wing": "coding",
    Accept: "application/json, text/event-stream",
  };
  if (sessionId) result["Mcp-Session-Id"] = sessionId;
  if (protocolVersion) result["MCP-Protocol-Version"] = protocolVersion;
  return result;
}

function deliver(message: Message, initialize: boolean) {
  if (initialize && message.result?.protocolVersion)
    protocolVersion = message.result.protocolVersion;
  emit(message);
}

async function readEvents(response: Response, initialize = false) {
  if (!response.body) throw new Error("Missing event stream");
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  let data: string[] = [];
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let newline: number;
    while ((newline = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, newline).replace(/\r$/, "");
      buffer = buffer.slice(newline + 1);
      if (!line) {
        if (data.length) deliver(JSON.parse(data.join("\n")), initialize);
        data = [];
      } else if (line.startsWith("data:")) {
        data.push(line.slice(5).replace(/^ /, ""));
      }
    }
  }
}

async function listen() {
  try {
    const response = await fetch(url, {
      headers: headers(),
      redirect: "error",
    });
    if (
      response.ok &&
      response.headers.get("content-type")?.includes("text/event-stream")
    )
      await readEvents(response);
  } catch {
    // The server may not offer a standalone event stream.
  }
}

async function send(message: Message) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { ...headers(), "Content-Type": "application/json" },
      body: JSON.stringify(message),
      redirect: "error",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const initialize = message.method === "initialize";
    if (initialize) sessionId = response.headers.get("Mcp-Session-Id") || "";
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/event-stream"))
      await readEvents(response, initialize);
    else if (contentType.includes("application/json"))
      deliver((await response.json()) as Message, initialize);
  } catch (error) {
    const detail =
      error instanceof Error && /^HTTP \d+$/.test(error.message)
        ? error.message
        : "request failed";
    if ("id" in message)
      emit({
        jsonrpc: "2.0",
        id: message.id,
        error: {
          code: -32603,
          message: `MemPalace transport error: ${detail}`,
        },
      });
    else console.error("MemPalace transport error");
  }
}

const reader = Bun.stdin
  .stream()
  .pipeThrough(new TextDecoderStream())
  .getReader();
let buffer = "";
async function handle(line: string) {
  let message: Message;
  try {
    message = JSON.parse(line);
  } catch {
    console.error("Invalid MCP message from agy");
    return;
  }
  if (message.method === "initialize") {
    await send(message);
    if (sessionId) void listen();
  } else if (message.method === "notifications/initialized") {
    await send(message);
  } else {
    void send(message);
  }
}
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += value;
  let newline: number;
  while ((newline = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, newline).replace(/\r$/, "");
    buffer = buffer.slice(newline + 1);
    await handle(line);
  }
}
if (buffer) await handle(buffer.replace(/\r$/, ""));
process.exit(0);
