import fs from "node:fs/promises";

const root = new URL("../", import.meta.url);
let pluginRoot = root;
try {
  await fs.access(new URL("plugin/plugin.json", root));
  pluginRoot = new URL("plugin/", root);
} catch {}
const manifest = JSON.parse(await fs.readFile(new URL("plugin.json", pluginRoot), "utf8"));
let api = await fs.readFile(new URL("vendor/decky-api-1.1.3/index.js", root), "utf8");
const importLine = "import _manifest from '@decky/manifest';";
if (!api.includes(importLine) || !api.includes('export * from "./types";')) {
  throw new Error("Unexpected @decky/api input; inspect the pinned package before rebuilding");
}
api = api.replace(importLine, `const _manifest = ${JSON.stringify(manifest)};`)
  .replace('export * from "./types";', "")
  .replace(/^export const /gm, "const ");
const panel = await fs.readFile(new URL("src/panel.js", root), "utf8");
const output = `// Ayaneo3 Fans. Bundled @decky/api 1.1.3; see LICENSE.decky-api.\n${api}\n${panel}`;
await fs.mkdir(new URL("dist/", pluginRoot), { recursive: true });
await fs.writeFile(new URL("dist/index.js", pluginRoot), output);
