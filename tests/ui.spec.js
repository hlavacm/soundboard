import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const sounds = JSON.parse(readFileSync(new URL('../sounds.json', import.meta.url), 'utf8'));
const tile = (page, name) => page.getByRole('button', { name });

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'warning' && errors.push(m.text()));
  await page.goto('/');
  // all sounds were fetched and decoded
  await expect(page.locator('#loops button')).toHaveCount(sounds.loops.length);
  await expect(page.locator('main button')).toHaveCount(sounds.sfx.length);
  // all 55 files fetched and decoded can take a while on a loaded machine (parallel make test)
  await expect(page.locator('button:disabled')).toHaveCount(0, { timeout: 15000 });
  expect(errors).toEqual([]);
});

test('effect groups follow the order in sounds.json', async ({ page }) => {
  await expect(page.locator('main h2')).toHaveText(['Announcer', 'Dev life', 'Cute', 'Česky', 'Jingles', 'Effects']);
});

test('the Czech section is shown in Czech in the UI, not the English keys from sounds.json', async ({ page }) => {
  await expect(page.getByRole('button', { name: /Pauza na kafe/ })).toHaveCount(1);
  await expect(page.getByRole('button', { name: /Kdo rozbil produkci/ })).toHaveCount(1);
  await expect(page.getByRole('button', { name: /Další, prosím/ })).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Coffee break' })).toHaveCount(0);
});

test('at most one loop plays at a time', async ({ page }) => {
  const active = page.locator('#loops button.on');

  await tile(page, 'Arcade').click();
  await expect(active).toHaveText([/Arcade/]);

  await tile(page, 'Lo-fi chill').click();
  await expect(active).toHaveText([/Lo-fi chill/]);

  await tile(page, 'Lo-fi chill').click();
  await expect(active).toHaveCount(0);
});

test('effects light up while playing and STOP ends them', async ({ page }) => {
  const drumroll = tile(page, 'Drumroll');
  const siren = tile(page, 'Siren');
  await drumroll.click();
  await siren.click();
  await expect(page.locator('main button.on')).toHaveCount(2);

  await page.getByRole('button', { name: /STOP/ }).click();
  await expect(page.locator('main button.on')).toHaveCount(0);
});

test('a short effect turns off by itself when it ends', async ({ page }) => {
  const coin = tile(page, 'Coin');
  await coin.click();
  await expect(coin).toHaveClass(/on/);
  await expect(coin).not.toHaveClass(/on/, { timeout: 10000 });
});
