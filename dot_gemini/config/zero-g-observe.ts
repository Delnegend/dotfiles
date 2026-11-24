#!/usr/bin/env bun
/** Best-effort PostInvocation collection for the interactive Antigravity CLI. */
import {
  constants,
  closeSync,
  fstatSync,
  lstatSync,
  openSync,
  readSync,
  realpathSync,
  statSync,
} from "node:fs";
import { homedir } from "node:os";
import { join, relative, isAbsolute } from "node:path";

const MAX_INPUT = 1024 * 1024;
const MAX_TRANSCRIPT = 2 * 1024 * 1024;

async function collect(): Promise<void> {
  const base = (process.env.ZERO_G_URL ?? "").replace(/\/+$/, "");
  const key = process.env.ZERO_G_VIRTUAL_KEY ?? "";
  if (!base || !key) return;

  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += bytes.length;
    if (size > MAX_INPUT) return;
    chunks.push(bytes);
  }
  const event = JSON.parse(Buffer.concat(chunks, size).toString("utf8"));
  const {
    transcriptPath: path,
    initialNumSteps: start,
    conversationId: conversation,
    modelName: model,
  } = event;
  if (
    typeof path !== "string" ||
    typeof conversation !== "string" ||
    !conversation ||
    typeof model !== "string" ||
    !model ||
    !Number.isSafeInteger(start) ||
    start < 0
  )
    return;

  const root = realpathSync(join(homedir(), ".gemini/antigravity-cli/brain"));
  if (lstatSync(path).isSymbolicLink()) return;
  const fd = openSync(
    path,
    constants.O_RDONLY | constants.O_NONBLOCK | (constants.O_NOFOLLOW ?? 0),
  );
  let data: Buffer;
  let offset: number;
  try {
    const info = fstatSync(fd);
    if (!info.isFile()) return;
    // Linux exposes the opened file's actual path; elsewhere verify its identity
    // against the resolved path after opening.
    const resolved =
      process.platform === "linux"
        ? realpathSync(`/proc/self/fd/${fd}`)
        : realpathSync(path);
    const rel = relative(root, resolved);
    if (rel === ".." || rel.startsWith("../") || isAbsolute(rel)) return;
    const current = lstatSync(path);
    const target = statSync(resolved);
    if (
      current.isSymbolicLink() ||
      current.dev !== info.dev ||
      current.ino !== info.ino ||
      target.dev !== info.dev ||
      target.ino !== info.ino
    )
      return;
    offset = Math.max(0, info.size - MAX_TRANSCRIPT);
    data = Buffer.allocUnsafe(MAX_TRANSCRIPT);
    data = data.subarray(0, readSync(fd, data, 0, MAX_TRANSCRIPT, offset));
  } finally {
    closeSync(fd);
  }
  if (offset) {
    const newline = data.indexOf(10);
    if (newline < 0) return;
    data = data.subarray(newline + 1);
  }

  let record: Record<string, unknown> | undefined;
  for (const line of data.toString("utf8").split(/\r?\n/)) {
    try {
      const candidate = JSON.parse(line);
      if (
        candidate &&
        typeof candidate === "object" &&
        !Array.isArray(candidate) &&
        candidate.source === "MODEL" &&
        candidate.status === "DONE" &&
        Number.isSafeInteger(candidate.step_index) &&
        candidate.step_index >= start &&
        (!record || candidate.step_index < (record.step_index as number))
      )
        record = candidate;
    } catch {
      // Ignore malformed transcript records.
    }
  }
  if (!record) return;
  const count = (name: string) => {
    const value = record![name];
    return typeof value === "number" &&
      Number.isSafeInteger(value) &&
      value >= 0
      ? value
      : null;
  };
  await fetch(`${base}/v1/agy/observations`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      conversation_id: conversation,
      step_index: record.step_index,
      model,
      input_tokens: count("input_tokens"),
      output_tokens: count("output_tokens"),
      request: { lastUserInput: event.lastUserInput ?? null },
      response: record,
    }),
    redirect: "manual",
    signal: AbortSignal.timeout(2000),
  });
}

const deadline = setTimeout(() => {
  process.stdout.write("{}\n", () => process.exit(0));
}, 4000);
try {
  await collect();
} catch {
  // Collection must never interfere with the CLI.
} finally {
  clearTimeout(deadline);
  process.stdout.write("{}\n");
}
