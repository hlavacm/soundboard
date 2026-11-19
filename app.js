// @ts-check
import { createPlayer, groupSfx } from './player.js';

/** @typedef {import('./player.js').Sound} Sound */

/** @template {HTMLElement} T @param {string} id @returns {T} */
const $ = (id) => /** @type {T} */ (document.getElementById(id));

// UI-only Czech labels for the Czech voice lines; sounds.json keeps the stable English keys
/** @type {Record<string, string>} */
const GROUP_LABELS = { Czech: 'Česky' };
/** @type {Record<string, string>} keyed by file, the stable identifier in sounds.json */
const NAME_LABELS = {
  'sounds/sfx/coffee.mp3': 'Pauza na kafe',
  'sounds/sfx/applause.mp3': 'Potlesk, prosím',
  'sounds/sfx/worksforme.mp3': 'U mě to funguje',
  'sounds/sfx/whobrokeprod.mp3': 'Kdo rozbil produkci?',
  'sounds/sfx/bomb.mp3': 'To je bomba',
  'sounds/sfx/next.mp3': 'Další, prosím',
};

// leftover from an earlier PWA version on the same origin: an old service worker would serve stale cached files
navigator.serviceWorker?.getRegistrations().then((regs) => {
  for (const r of regs) r.unregister();
});

const ctx = new AudioContext();
const player = createPlayer(ctx);
const loopVol = /** @type {HTMLInputElement} */ ($('loopVol'));
const sfxVol = /** @type {HTMLInputElement} */ ($('sfxVol'));
player.loopBus.gain.value = Number(loopVol.value);
player.sfxBus.gain.value = Number(sfxVol.value);

/** @type {WakeLockSentinel | null} */
let wakeLock = null;

// browsers only allow audio after the first click; also keep the screen awake
async function requestWakeLock() {
  if (!wakeLock || wakeLock.released) wakeLock = await navigator.wakeLock?.request('screen').catch(() => null);
}

document.addEventListener(
  'click',
  () => {
    if (ctx.state !== 'running') ctx.resume().catch(() => {});
    requestWakeLock();
  },
  true,
);
// iOS releases the wake lock when the page is hidden; ask again once it is visible
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') requestWakeLock();
});

/**
 * @param {Sound} item
 * @param {(b: HTMLButtonElement, buf: AudioBuffer) => void} onTap
 */
function tile(item, onTap) {
  const b = document.createElement('button');
  const e = document.createElement('span');
  e.className = 'e';
  e.textContent = item.emoji || '🔊';
  b.append(e, NAME_LABELS[item.file] ?? item.name);
  b.disabled = true;
  fetch(item.file)
    .then((r) => {
      if (!r.ok) throw new Error(String(r.status));
      return r.arrayBuffer();
    })
    .then((a) => ctx.decodeAudioData(a))
    .then((buf) => {
      b.onclick = () => onTap(b, buf);
      b.disabled = false;
    })
    .catch((err) => {
      b.title = `Cannot load ${item.file}`;
      console.warn(item.file, err);
    });
  return b;
}

/** @param {HTMLButtonElement} b @param {AudioBuffer} buf */
function onLoop(b, buf) {
  document.querySelector('#loops .on')?.classList.remove('on');
  if (player.toggleLoop(b, buf)) b.classList.add('on');
}

/** @type {WeakMap<HTMLButtonElement, number>} how many instances of an effect are playing right now */
const active = new WeakMap();

/** @param {HTMLButtonElement} b @param {AudioBuffer} buf */
function onSfx(b, buf) {
  active.set(b, (active.get(b) ?? 0) + 1);
  b.classList.add('on');
  player.playSfx(buf, () => {
    const n = (active.get(b) ?? 1) - 1;
    active.set(b, n);
    if (n === 0) b.classList.remove('on');
  });
}

fetch('sounds.json')
  .then((r) => r.json())
  .then((/** @type {{ loops: Sound[], sfx: Sound[] }} */ { loops, sfx }) => {
    for (const it of loops) $('loops').append(tile(it, onLoop));
    for (const { name, items } of groupSfx(sfx)) {
      const section = document.createElement('section');
      section.className = 'group';
      const h = document.createElement('h2');
      h.textContent = GROUP_LABELS[name] ?? name;
      const grid = document.createElement('div');
      grid.className = 'grid';
      grid.append(...items.map((it) => tile(it, onSfx)));
      section.append(h, grid);
      $('main').append(section);
    }
  })
  .catch((err) => console.error('Cannot load sounds.json', err));

loopVol.oninput = () => (player.loopBus.gain.value = Number(loopVol.value));
sfxVol.oninput = () => (player.sfxBus.gain.value = Number(sfxVol.value));
$('stopBtn').onclick = () => player.stopSfx();
