#!/usr/bin/env bun
/** Read the Zero-G virtual key without printing any other local secrets. */
const path = `${process.env.HOME}/.omp/agent/.env`;
try {
  const child = Bun.spawnSync(["bash", "-c", 'source "$1" >/dev/null && printf "%s" "${ZERO_G_TOKEN:-}"', "zero-g-key", path], { stdout: "pipe", stderr: "ignore" });
  if (child.exitCode !== 0) throw new Error("Cannot load credentials");
  const token = new TextDecoder().decode(child.stdout).trim();
  if (!token || /[\r\n]/.test(token)) throw new Error("Missing or invalid ZERO_G_TOKEN");
  process.stdout.write(`${token}\n`);
} catch {
  console.error(`Cannot read a valid ZERO_G_TOKEN from ${path}`);
  process.exitCode = 1;
}
export {};
