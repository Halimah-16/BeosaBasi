/** Pengolahan audio di browser: dekode, potong di titik sepi, encode WAV. */

export const SAMPLE_RATE = 16000;
export const CHUNK_SECONDS = 60;
const QUIET_SEARCH_SECONDS = 5;
const QUIET_WINDOW_SECONDS = 0.05;
const SILENCE_RMS = 0.002;

export interface ChunkRange {
  start: number;
  end: number;
}

export async function decodeToMono(file: File): Promise<Float32Array> {
  const bytes = await file.arrayBuffer();
  // decodeAudioData otomatis me-resample ke sample rate konteks.
  const context = new OfflineAudioContext(1, 1, SAMPLE_RATE);
  const decoded = await context.decodeAudioData(bytes);
  const mono = new Float32Array(decoded.length);
  for (let channel = 0; channel < decoded.numberOfChannels; channel += 1) {
    const data = decoded.getChannelData(channel);
    for (let i = 0; i < data.length; i += 1) {
      mono[i] += data[i] / decoded.numberOfChannels;
    }
  }
  return mono;
}

function quietestPoint(samples: Float32Array, from: number, to: number, windowSize: number): number {
  let best = to;
  let bestEnergy = Number.POSITIVE_INFINITY;
  for (let start = from; start + windowSize <= to; start += windowSize) {
    let energy = 0;
    for (let i = start; i < start + windowSize; i += 1) {
      energy += samples[i] * samples[i];
    }
    if (energy < bestEnergy) {
      bestEnergy = energy;
      best = start + Math.floor(windowSize / 2);
    }
  }
  return best;
}

/** Bagi audio jadi potongan ±60 detik, dipotong di bagian tersepi agar kata tidak terbelah. */
export function planChunks(samples: Float32Array, rate: number = SAMPLE_RATE): ChunkRange[] {
  const chunkSize = CHUNK_SECONDS * rate;
  const searchSize = QUIET_SEARCH_SECONDS * rate;
  const windowSize = Math.max(1, Math.floor(QUIET_WINDOW_SECONDS * rate));
  const ranges: ChunkRange[] = [];
  let start = 0;
  while (samples.length - start > chunkSize) {
    const hardEnd = start + chunkSize;
    const end = quietestPoint(samples, hardEnd - searchSize, hardEnd, windowSize);
    ranges.push({ start, end });
    start = end;
  }
  if (start < samples.length) ranges.push({ start, end: samples.length });
  return ranges;
}

export function isSilent(samples: Float32Array): boolean {
  if (samples.length === 0) return true;
  let energy = 0;
  for (let i = 0; i < samples.length; i += 1) energy += samples[i] * samples[i];
  return Math.sqrt(energy / samples.length) < SILENCE_RMS;
}

export function computePeaks(samples: Float32Array, bars: number): number[] {
  const peaks: number[] = [];
  const step = samples.length / bars;
  let highest = 0;
  for (let bar = 0; bar < bars; bar += 1) {
    const from = Math.floor(bar * step);
    const to = Math.floor((bar + 1) * step);
    let peak = 0;
    // Cukup sampel berjarak; bentuk gelombang tidak butuh setiap titik.
    const skip = Math.max(1, Math.floor((to - from) / 400));
    for (let i = from; i < to; i += skip) peak = Math.max(peak, Math.abs(samples[i]));
    peaks.push(peak);
    highest = Math.max(highest, peak);
  }
  return highest > 0 ? peaks.map((peak) => peak / highest) : peaks;
}

export function encodeWav(samples: Float32Array, rate: number = SAMPLE_RATE): Uint8Array {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeText = (offset: number, text: string): void => {
    for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
  };
  writeText(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeText(8, "WAVE");
  writeText(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeText(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return new Uint8Array(buffer);
}

export function bytesToBase64(bytes: Uint8Array): string {
  const parts: string[] = [];
  const blockSize = 0x8000;
  for (let i = 0; i < bytes.length; i += blockSize) {
    parts.push(String.fromCharCode(...bytes.subarray(i, i + blockSize)));
  }
  return btoa(parts.join(""));
}
