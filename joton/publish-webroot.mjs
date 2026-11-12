// Kopiuje stronę do public_html witryny na Jotonie (panel Enhance) – sprawdzone przy OpenGenTree.
// Użycie: node scripts/publish-webroot.mjs [katalog=public]
// Joton uruchamia skrypt budowy w /var/www/<witryna>/deploys/<commit>/, public_html = ../../public_html.
import { existsSync, mkdirSync, readdirSync, statSync, renameSync, copyFileSync, chmodSync, accessSync, rmSync, constants } from 'fs';
import { join, resolve, basename, dirname, relative } from 'path';

const fail = (m) => { console.error(`✗ publish: ${m}`); process.exit(1); };
const src = resolve(process.argv[2] ?? 'public');
const here = process.cwd();

let target = process.env.WEBROOT;
if (!target) {
  if (basename(dirname(here)) !== 'deploys') fail(`uruchom z <witryna>/deploys/<commit>/ (jest: ${here}) albo ustaw WEBROOT`);
  target = resolve(here, '../../public_html');
}
if (!existsSync(join(src, 'index.html'))) fail(`brak ${src}/index.html`);
if (!existsSync(target)) fail(`brak katalogu ${target}`);
try { accessSync(target, constants.W_OK); } catch { fail(`brak prawa zapisu do ${target}`); }

const files = [];
const walk = (d) => { for (const n of readdirSync(d)) { const p = join(d, n); if (statSync(p).isDirectory()) walk(p); else files.push(relative(src, p)); } };
walk(src);
files.sort((a, b) => (a === 'index.html') - (b === 'index.html'));   // index.html na końcu

const temps = [];
try {
  for (const f of files) {
    const dest = join(target, f);
    mkdirSync(dirname(dest), { recursive: true, mode: 0o755 });
    const tmp = join(dirname(dest), `.publish-${process.pid}-${basename(f)}`);
    temps.push(tmp);
    copyFileSync(join(src, f), tmp);
    chmodSync(tmp, 0o644);
    renameSync(tmp, dest);
  }
} catch (e) {
  for (const t of temps) rmSync(t, { force: true });
  fail(e.message);
}
console.log(`✓ opublikowano ${files.length} plików do ${target}`);
