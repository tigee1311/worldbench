import { access, copyFile, cp, mkdir, readFile, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "dist");
const files = ["index.html", "styles.css", "script.js", "vercel.json"];
const requiredAssets = [
  "assets/screenshots/checkpoint-proof.png",
  "assets/screenshots/terminal-gate-result.png"
];

for (const path of [...files, ...requiredAssets]) {
  await access(resolve(root, path));
}

const html = await readFile(resolve(root, "index.html"), "utf8");
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]));
const anchors = [...html.matchAll(/href="#([^"]+)"/g)].map((match) => match[1]);
for (const anchor of anchors) {
  if (!ids.has(anchor)) {
    throw new Error(`Missing anchor target: #${anchor}`);
  }
}

const localPaths = [
  ...html.matchAll(/(?:href|poster|src)="\/(?!\/)([^"?#]+)[^"]*"/g)
].map((match) => match[1]);
for (const path of new Set(localPaths)) {
  await access(resolve(root, path));
}

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });

for (const file of files) {
  await copyFile(resolve(root, file), resolve(output, file));
}
await cp(resolve(root, "assets/screenshots"), resolve(output, "assets/screenshots"), { recursive: true });

console.log(`Built static site at ${output}`);
