import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import globals from 'globals';

export default tseslint.config(
  { ignores: ['node_modules/**', '.venv/**', '.tools/**', 'dist/**', 'test-results/**', 'playwright-report/**', 'packages/contracts/api.d.ts'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { languageOptions: { globals: { ...globals.node, ...globals.browser } } },
);
