#!/usr/bin/env node
// build-copy.mjs
// The "build:copy" step of `npm run build`. Runs after build:css and
// build:js have already produced dist/css/main.min.css and
// dist/js/main.min.js. This script:
//
//   1. Ensures dist/ exists.
//   2. Copies src/assets/ -> dist/assets/ recursively, as-is.
//   3. Copies src/index.html -> dist/index.html, REWRITING the stylesheet
//      href and script src from the unbundled source paths
//      (css/main.css, js/main.js) to the bundled/minified output paths
//      (css/main.min.css, js/main.min.js).
//
// Step 3 is the one that matters most: without it, dist/index.html would
// still reference src files that don't exist in dist/, and the production
// build would 404 on its own CSS/JS. This is a plain Node script (no
// dependencies beyond the standard library) rather than an inline sed
// command specifically so it behaves identically on any platform running
// esbuild, instead of depending on GNU vs BSD sed differences.

import { existsSync, mkdirSync, cpSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(__dirname, '..');

const srcDir = join(frontendRoot, 'src');
const distDir = join(frontendRoot, 'dist');

const srcHtmlPath = join(srcDir, 'index.html');
const distHtmlPath = join(distDir, 'index.html');

const srcAssetsDir = join(srcDir, 'assets');
const distAssetsDir = join(distDir, 'assets');

// 1. Ensure dist/ exists.
if (!existsSync(distDir)) {
  mkdirSync(distDir, { recursive: true });
}

// 2. Copy assets/ recursively.
if (existsSync(srcAssetsDir)) {
  cpSync(srcAssetsDir, distAssetsDir, { recursive: true });
} else {
  console.warn(`[build-copy] Warning: ${srcAssetsDir} does not exist, skipping asset copy.`);
}

// 3. Copy index.html with the stylesheet/script paths rewritten to the
// bundled output files. Matches the exact source-path attribute values
// written by index.html today; if those markup lines change, update the
// replacements below to match.
if (!existsSync(srcHtmlPath)) {
  console.error(`[build-copy] Error: ${srcHtmlPath} does not exist.`);
  process.exit(1);
}

let html = readFileSync(srcHtmlPath, 'utf8');

const replacements = [
  { from: 'href="css/main.css"', to: 'href="css/main.min.css"' },
  { from: 'src="js/main.js"', to: 'src="js/main.min.js"' },
];

for (const { from, to } of replacements) {
  if (!html.includes(from)) {
    console.error(
      `[build-copy] Error: expected to find ${JSON.stringify(from)} in src/index.html but it was not present. ` +
        'The source markup may have changed - update scripts/build-copy.mjs to match, otherwise dist/index.html ' +
        'would silently keep pointing at unbundled source paths that do not exist in dist/.',
    );
    process.exit(1);
  }
  html = html.replaceAll(from, to);
}

writeFileSync(distHtmlPath, html, 'utf8');

console.log('[build-copy] Wrote dist/index.html (paths rewritten to css/main.min.css, js/main.min.js).');
console.log(`[build-copy] Copied ${srcAssetsDir} -> ${distAssetsDir}.`);
