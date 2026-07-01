import { defineConfig } from 'tsup';

// The plugin is loaded by mystmd as a single ESM module. We bundle everything
// (except node builtins) so the emitted dist/index.js is self-contained and can
// be referenced directly from myst.yml `plugins:`.
export default defineConfig({
  entry: { index: 'src/index.ts', cli: 'src/cli.ts' },
  format: ['esm'],
  target: 'node18',
  platform: 'node',
  bundle: true,
  clean: true,
  sourcemap: false,
  dts: false,
  shims: false,
  // mystmd only loads plugins whose file extension is `.mjs`.
  outExtension: () => ({ js: ".mjs" }),
});
