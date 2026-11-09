/** Mengirim potongan audio ke /api/transcribe, beberapa sekaligus, dengan percobaan ulang. */

import type { Segment } from "./formats";

export type ChunkStatus = "pending" | "working" | "done" | "silent" | "failed";

export interface ChunkResult {
  segments: Segment[];
  language: string | null;
}

export class QuotaError extends Error {}

export type SendChunk = (index: number, signal: AbortSignal) => Promise<ChunkResult>;

const RETRY_DELAYS_MS = [1000, 3000];

export interface ApiFetchOptions {
  base64: string;
  language: string;
  offsetSeconds: number;
  signal: AbortSignal;
  fetchFn?: typeof fetch;
  retryDelaysMs?: number[];
}

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export async function postChunk(options: ApiFetchOptions): Promise<ChunkResult> {
  const { base64, language, offsetSeconds, signal } = options;
  const fetchFn = options.fetchFn ?? ((...args: Parameters<typeof fetch>) => fetch(...args));
  const delays = options.retryDelaysMs ?? RETRY_DELAYS_MS;
  const url = `/api/transcribe?language=${encodeURIComponent(language)}`;

  for (let attempt = 0; ; attempt += 1) {
    let lastError: Error;
    try {
      const response = await fetchFn(url, { method: "POST", body: base64, signal });
      if (response.status === 429) throw new QuotaError("quota");
      if (response.ok) {
        const data = (await response.json()) as {
          text: string;
          language: string | null;
          segments: Segment[];
        };
        const segments =
          data.segments.length > 0
            ? data.segments
            : data.text.length > 0
              ? [{ start: 0, end: 0, text: data.text }]
              : [];
        return {
          language: data.language,
          segments: segments.map((segment) => ({
            text: segment.text,
            start: segment.start + offsetSeconds,
            end: segment.end + offsetSeconds,
          })),
        };
      }
      const failure = new Error(`status ${response.status}`);
      if (response.status < 500) throw Object.assign(failure, { permanent: true });
      lastError = failure;
    } catch (error) {
      if (error instanceof QuotaError) throw error;
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      if (error instanceof Error && "permanent" in error) throw error;
      lastError = error instanceof Error ? error : new Error(String(error));
    }
    if (attempt >= delays.length) throw lastError;
    await wait(delays[attempt], signal);
  }
}

export interface RunOptions {
  indexes: number[];
  send: SendChunk;
  signal: AbortSignal;
  concurrency?: number;
  onStatus: (index: number, status: ChunkStatus, result?: ChunkResult) => void;
}

export interface RunSummary {
  quotaExhausted: boolean;
  cancelled: boolean;
}

export async function runChunks(options: RunOptions): Promise<RunSummary> {
  const { indexes, send, signal, onStatus } = options;
  const summary: RunSummary = { quotaExhausted: false, cancelled: false };
  let next = 0;

  const worker = async (): Promise<void> => {
    while (next < indexes.length && !summary.quotaExhausted && !signal.aborted) {
      const index = indexes[next];
      next += 1;
      onStatus(index, "working");
      try {
        onStatus(index, "done", await send(index, signal));
      } catch (error) {
        if (error instanceof QuotaError) {
          summary.quotaExhausted = true;
          onStatus(index, "pending");
        } else if (error instanceof DOMException && error.name === "AbortError") {
          onStatus(index, "pending");
        } else {
          onStatus(index, "failed");
        }
      }
    }
  };

  await Promise.all(Array.from({ length: options.concurrency ?? 3 }, worker));
  summary.cancelled = signal.aborted;
  return summary;
}
