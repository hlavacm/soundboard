// @ts-check
// Audio logic without the DOM, so it can be tested with a fake AudioContext.

/** @typedef {{ name: string, file: string, emoji?: string, group?: string }} Sound */

export const FADE = 1; // seconds, loop crossfade length
export const DEFAULT_GROUP = 'Effects';

/**
 * Groups consecutive effects with the same group (keeps the order from sounds.json).
 * @param {Sound[]} sfx
 * @returns {{ name: string, items: Sound[] }[]}
 */
export function groupSfx(sfx) {
  /** @type {{ name: string, items: Sound[] }[]} */
  const groups = [];
  for (const item of sfx) {
    const name = item.group || DEFAULT_GROUP;
    const last = groups.at(-1);
    if (last && last.name === name) last.items.push(item);
    else groups.push({ name, items: [item] });
  }
  return groups;
}

/** @param {BaseAudioContext} ctx */
export function createPlayer(ctx) {
  const loopBus = ctx.createGain();
  const sfxBus = ctx.createGain();
  loopBus.connect(ctx.destination);
  sfxBus.connect(ctx.destination);

  /** @type {{ key: unknown, src: AudioBufferSourceNode, gain: GainNode } | null} */
  let current = null;
  /** @type {Set<AudioBufferSourceNode>} */
  const playing = new Set();

  /** @param {AudioParam} param @param {number} to */
  function ramp(param, to) {
    const t = ctx.currentTime;
    param.cancelScheduledValues(t);
    param.setValueAtTime(param.value, t);
    param.linearRampToValueAtTime(to, t + FADE);
  }

  return {
    loopBus,
    sfxBus,

    /** @returns {unknown} key of the loop playing right now, or null */
    get currentLoop() {
      return current ? current.key : null;
    },

    get sfxCount() {
      return playing.size;
    },

    /**
     * Toggles a loop: another loop = crossfade, the same one = stop. At most one plays at a time.
     * @param {unknown} key
     * @param {AudioBuffer} buffer
     * @returns {boolean} true if loop `key` is now playing
     */
    toggleLoop(key, buffer) {
      const old = current;
      current = null;
      if (old) {
        ramp(old.gain.gain, 0);
        old.src.stop(ctx.currentTime + FADE);
        if (old.key === key) return false;
      }
      const gain = ctx.createGain();
      gain.gain.value = 0;
      gain.connect(loopBus);
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.loop = true;
      src.connect(gain);
      src.start();
      ramp(gain.gain, 1);
      current = { key, src, gain };
      return true;
    },

    /**
     * Plays an effect; effects may overlap.
     * @param {AudioBuffer} buffer
     * @param {() => void} [onEnd]
     */
    playSfx(buffer, onEnd) {
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(sfxBus);
      src.onended = () => {
        playing.delete(src);
        onEnd?.();
      };
      src.start();
      playing.add(src);
    },

    stopSfx() {
      for (const src of playing) src.stop();
    },
  };
}
