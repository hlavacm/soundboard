// Feature test: sounds.json matches the files in sounds/.
import assert from 'node:assert/strict';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { test } from 'node:test';

const root = new URL('../', import.meta.url);
const { loops, sfx } = JSON.parse(readFileSync(new URL('sounds.json', root), 'utf8'));
const all = [...loops, ...sfx];

test('every sound has a name and a file in the right folder', () => {
  assert.ok(loops.length > 0 && sfx.length > 0);
  for (const s of loops) assert.match(s.file, /^sounds\/loops\/[\w-]+\.(wav|mp3|m4a)$/, s.name);
  for (const s of sfx) assert.match(s.file, /^sounds\/sfx\/[\w-]+\.(wav|mp3|m4a)$/, s.name);
  for (const s of all) assert.ok(s.name?.trim(), JSON.stringify(s));
});

test('all files exist and none is listed twice', () => {
  const missing = all.filter((s) => !existsSync(new URL(s.file, root))).map((s) => s.file);
  assert.deepEqual(missing, []);
  assert.equal(new Set(all.map((s) => s.file)).size, all.length);
});

test('sounds/ has no stray file missing from sounds.json', () => {
  const listed = new Set(all.map((s) => s.file));
  const onDisk = ['loops', 'sfx'].flatMap((d) => readdirSync(new URL(`sounds/${d}`, root)).map((f) => `sounds/${d}/${f}`));
  assert.deepEqual(
    onDisk.filter((f) => !listed.has(f)),
    [],
  );
});
