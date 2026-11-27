import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

// Sigurnosna pravila (vidi .claude/skills/frostbite-frontend/SKILL.md):
// bez ubacivanja HTML-a, bez eval-a, bez pohrane u pregledaču, API samo kroz src/api/client.ts.
const unsafeHtml = [
  { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: 'Zabranjeno: XSS. Prikazujte tekst.' },
  { selector: "AssignmentExpression > MemberExpression[property.name=/^(innerHTML|outerHTML)$/]", message: 'Zabranjeno: XSS.' },
  { selector: "CallExpression[callee.property.name=/^(insertAdjacentHTML|write|writeln)$/]", message: 'Zabranjeno: XSS.' },
  { selector: "Literal[value=/^\\s*javascript:/i]", message: 'Zabranjeni javascript: URL-ovi.' },
];

export default defineConfig(
  { ignores: ['dist', 'node_modules'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, tseslint.configs.recommended, reactHooks.configs.flat.recommended],
    languageOptions: { globals: globals.browser },
    rules: {
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
      'no-restricted-syntax': ['error', ...unsafeHtml],
      'no-restricted-globals': ['error',
        { name: 'localStorage', message: 'Ne čuvati podatke u pregledaču (sigurnost).' },
        { name: 'sessionStorage', message: 'Ne čuvati podatke u pregledaču (sigurnost).' },
        { name: 'indexedDB', message: 'Ne čuvati podatke u pregledaču (sigurnost).' },
        { name: 'fetch', message: 'Koristite api() iz src/api/client.ts (CSRF, same-origin).' },
      ],
      'no-restricted-properties': ['error',
        { object: 'window', property: 'localStorage' },
        { object: 'window', property: 'sessionStorage' },
        { object: 'window', property: 'fetch' },
        { object: 'console', property: 'log', message: 'Bez logovanja (lični podaci).' },
      ],
    },
  },
  {
    // jedini izuzetak za pohranu u pregledaču: izbor teme ('light' | 'dark')
    files: ['src/lib/theme.ts'],
    rules: { 'no-restricted-globals': ['error', 'sessionStorage', 'indexedDB', 'fetch'] },
  },
  {
    // E2E testovi (Playwright): fixture funkcija `use` nije React hook
    files: ['e2e/**/*.ts', 'playwright.config.ts'],
    rules: { 'react-hooks/rules-of-hooks': 'off' },
  },
  {
    // jedino mjesto koje smije zvati fetch
    files: ['src/api/client.ts'],
    rules: { 'no-restricted-globals': 'off' },
  },
);
