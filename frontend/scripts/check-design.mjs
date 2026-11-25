// Provjera pravila dizajna (.claude/skills/frostbite-frontend/SKILL.md):
//  1. nigdje gradijenti
//  2. boje samo u src/styles/tokens.css (komponente koriste var(--...))
//  3. bez vanjskih resursa u CSS-u (fontovi i slike su lokalni; CSP default-src 'self')
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const SCAN = ['src', 'public', 'index.html'];
const TOKENS = 'src/styles/tokens.css';

const rules = [
  { name: 'gradijent', re: /gradient/i, files: /\.(css|tsx?|svg|html)$/ },
  { name: 'hardkodirana boja (koristite token iz tokens.css)', re: /#[0-9a-f]{3,8}\b|\b(rgb|rgba|hsl|hsla|oklch)\(/i,
    files: /\.(css|tsx)$/, skip: (f) => f === TOKENS },
  { name: 'vanjski resurs', re: /(url\(\s*['"]?(https?:)?\/\/|@import\s+['"]?(https?:)?\/\/)/i, files: /\.css$/ },
];

function* walk(p) {
  const abs = join(ROOT, p);
  if (statSync(abs).isDirectory()) {
    for (const e of readdirSync(abs)) yield* walk(join(p, e));
  } else {
    yield p;
  }
}

let failed = 0;
for (const entry of SCAN) {
  for (const file of walk(entry)) {
    const rel = relative('.', file);
    const text = readFileSync(join(ROOT, file), 'utf8');
    for (const rule of rules) {
      if (!rule.files.test(rel) || rule.skip?.(rel)) continue;
      text.split('\n').forEach((line, i) => {
        if (rule.re.test(line)) {
          console.error(`${rel}:${i + 1}  ${rule.name}: ${line.trim()}`);
          failed++;
        }
      });
    }
  }
}

if (failed) {
  console.error(`\nProvjera dizajna: ${failed} prekršaj(a).`);
  process.exit(1);
}
console.error('Provjera dizajna: OK');
