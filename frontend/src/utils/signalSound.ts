export const SOUND_STORAGE_KEY = "paopaoquant_sound_enabled";

export function readSoundEnabled(): boolean {
  try {
    return localStorage.getItem(SOUND_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function writeSoundEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(SOUND_STORAGE_KEY, String(enabled));
  } catch {
    /* ignore quota / private mode */
  }
}

function playTone(
  ctx: AudioContext,
  frequency: number,
  durationSec: number,
  type: OscillatorType = "sine"
) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  const t0 = ctx.currentTime;
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.exponentialRampToValueAtTime(0.22, t0 + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + durationSec);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + durationSec + 0.05);
}

class SignalSoundPlayer {
  private ctx: AudioContext | null = null;

  async unlock(): Promise<void> {
    if (!this.ctx) {
      const Ctx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext;
      if (!Ctx) return;
      this.ctx = new Ctx();
    }
    if (this.ctx.state === "suspended") {
      await this.ctx.resume();
    }
  }

  playBuy(): void {
    if (!this.ctx) return;
    playTone(this.ctx, 880, 0.14, "sine");
    window.setTimeout(() => {
      if (this.ctx) playTone(this.ctx, 1175, 0.1, "sine");
    }, 90);
  }

  playSell(): void {
    if (!this.ctx) return;
    playTone(this.ctx, 440, 0.18, "triangle");
    window.setTimeout(() => {
      if (this.ctx) playTone(this.ctx, 330, 0.14, "triangle");
    }, 120);
  }
}

export const signalSound = new SignalSoundPlayer();
