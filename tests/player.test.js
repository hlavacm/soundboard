import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createPlayer, DEFAULT_GROUP, FADE, groupSfx } from '../player.js';

// Minimal fake AudioContext: records what the player does with the nodes.
class Param {
  value = 1;
  target = null;
  cancelScheduledValues() {}
  setValueAtTime(v) {
    this.value = v;
  }
  linearRampToValueAtTime(v, t) {
    this.target = { v, t };
  }
}
class Node {
  connect(n) {
    this.out = n;
  }
}
class Gain extends Node {
  gain = new Param();
}
class Source extends Node {
  buffer = null;
  loop = false;
  started = false;
  stoppedAt = null;
  onended = null;
  start() {
    this.started = true;
  }
  stop(t = 0) {
    this.stoppedAt = t;
  }
}
function fakeCtx() {
  const ctx = {
    currentTime: 10,
    destination: new Node(),
    sources: [],
    createGain: () => new Gain(),
    createBufferSource() {
      const s = new Source();
      ctx.sources.push(s);
      return s;
    },
  };
  return ctx;
}

test('groupSfx groups consecutive effects and keeps the order', () => {
  const s = (name, group) => ({ name, file: `${name}.mp3`, group });
  const groups = groupSfx([s('a', 'X'), s('b', 'X'), s('c'), s('d', 'X')]);
  assert.deepEqual(
    groups.map((g) => [g.name, g.items.map((i) => i.name)]),
    [
      ['X', ['a', 'b']],
      [DEFAULT_GROUP, ['c']],
      ['X', ['d']],
    ],
  );
});

test('a loop starts with a fade-in and looping enabled', () => {
  const ctx = fakeCtx();
  const p = createPlayer(ctx);
  assert.equal(p.toggleLoop('a', 'bufA'), true);
  const [src] = ctx.sources;
  assert.equal(src.buffer, 'bufA');
  assert.equal(src.loop, true);
  assert.equal(src.started, true);
  assert.deepEqual(src.out.gain.target, { v: 1, t: 10 + FADE });
  assert.equal(src.out.out, p.loopBus);
  assert.equal(p.currentLoop, 'a');
});

test('switching loops crossfades and only one keeps playing', () => {
  const ctx = fakeCtx();
  const p = createPlayer(ctx);
  p.toggleLoop('a', 'bufA');
  p.toggleLoop('b', 'bufB');
  const [a, b] = ctx.sources;
  assert.deepEqual(a.out.gain.target, { v: 0, t: 10 + FADE });
  assert.equal(a.stoppedAt, 10 + FADE);
  assert.equal(b.started, true);
  assert.equal(p.currentLoop, 'b');
});

test('clicking the active loop again stops it', () => {
  const ctx = fakeCtx();
  const p = createPlayer(ctx);
  p.toggleLoop('a', 'bufA');
  assert.equal(p.toggleLoop('a', 'bufA'), false);
  assert.equal(ctx.sources.length, 1);
  assert.equal(ctx.sources[0].stoppedAt, 10 + FADE);
  assert.equal(p.currentLoop, null);
});

test('effects overlap, report their end and STOP stops them all', () => {
  const ctx = fakeCtx();
  const p = createPlayer(ctx);
  let ended = 0;
  p.playSfx('x', () => ended++);
  p.playSfx('x', () => ended++);
  assert.equal(p.sfxCount, 2);
  assert.ok(ctx.sources.every((s) => s.started && s.out === p.sfxBus && !s.loop));

  ctx.sources[0].onended();
  assert.equal(p.sfxCount, 1);
  assert.equal(ended, 1);

  p.stopSfx();
  assert.equal(ctx.sources[1].stoppedAt, 0);
});
