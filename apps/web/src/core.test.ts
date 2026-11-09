import { describe, expect, it } from "vitest";
import { bytesToBase64, computePeaks, encodeWav, isSilent, planChunks } from "./audio";
import { formatClock, toSrt, toTxt, toVtt, type Segment } from "./formats";
import { handleTranscribe } from "../functions/api/transcribe";
import { postChunk, QuotaError, runChunks, runWithLanguage, type ChunkStatus } from "./transcribe";

const segments: Segment[] = [
  { start: 0, end: 2.5, text: " Halo dunia " },
  { start: 61.2, end: 3725.04, text: "Kedua" },
  { start: 3726, end: 3727, text: "   " },
];

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

const signal = new AbortController().signal;

describe("audio", () => {
  it("memotong audio tanpa celah dan di titik sepi", () => {
    const rate = 100;
    const samples = new Float32Array(150 * rate).fill(0.5);
    samples.fill(0, 57 * rate, 58 * rate);
    const ranges = planChunks(samples, rate);
    expect(ranges[0].start).toBe(0);
    expect(ranges[0].end).toBeGreaterThanOrEqual(57 * rate);
    expect(ranges[0].end).toBeLessThanOrEqual(58 * rate);
    ranges.slice(1).forEach((range, i) => expect(range.start).toBe(ranges[i].end));
    expect(ranges[ranges.length - 1].end).toBe(samples.length);
  });

  it("audio pendek menjadi satu potongan", () => {
    expect(planChunks(new Float32Array(1000), 100)).toEqual([{ start: 0, end: 1000 }]);
  });

  it("mengenali keheningan", () => {
    expect(isSilent(new Float32Array(100))).toBe(true);
    expect(isSilent(new Float32Array(100).fill(0.2))).toBe(false);
  });

  it("menulis WAV yang dikenali server", () => {
    const wav = encodeWav(new Float32Array(10));
    expect(wav.length).toBe(64);
    expect(bytesToBase64(wav).startsWith("UklGR")).toBe(true);
  });

  it("menormalkan puncak gelombang", () => {
    expect(computePeaks(new Float32Array([0.25, 0.25, 0.5, 0.5]), 2)).toEqual([0.5, 1]);
  });
});

describe("format", () => {
  it("menulis waktu jam", () => {
    expect(formatClock(65)).toBe("01:05");
    expect(formatClock(3725)).toBe("1:02:05");
  });

  it("TXT melewati segmen kosong", () => {
    expect(toTxt(segments)).toBe("Halo dunia\n\nKedua");
  });

  it("SRT memakai koma dan nomor urut", () => {
    expect(toSrt(segments)).toBe(
      "1\n00:00:00,000 --> 00:00:02,500\nHalo dunia\n\n2\n00:01:01,200 --> 01:02:05,040\nKedua\n",
    );
  });

  it("VTT punya kepala dan titik", () => {
    const vtt = toVtt(segments);
    expect(vtt.startsWith("WEBVTT\n\n00:00:00.000 --> 00:00:02.500\n")).toBe(true);
  });
});

describe("pengiriman", () => {
  it("menggeser waktu sesuai posisi potongan", async () => {
    const fetchFn = (async () =>
      jsonResponse({ text: "a", language: "id", segments: [{ start: 1, end: 2, text: "a" }] })) as typeof fetch;
    const result = await postChunk({ base64: "x", language: "id", offsetSeconds: 60, signal, fetchFn });
    expect(result.segments).toEqual([{ text: "a", start: 61, end: 62 }]);
  });

  it("mengulang saat server gagal sementara", async () => {
    let calls = 0;
    const fetchFn = (async () => {
      calls += 1;
      return calls === 1 ? jsonResponse({}, 502) : jsonResponse({ text: "", language: null, segments: [] });
    }) as typeof fetch;
    await postChunk({ base64: "x", language: "id", offsetSeconds: 0, signal, fetchFn, retryDelaysMs: [0] });
    expect(calls).toBe(2);
  });

  it("tidak mengulang saat kuota habis", async () => {
    let calls = 0;
    const fetchFn = (async () => {
      calls += 1;
      return jsonResponse({}, 429);
    }) as typeof fetch;
    await expect(
      postChunk({ base64: "x", language: "id", offsetSeconds: 0, signal, fetchFn, retryDelaysMs: [0] }),
    ).rejects.toBeInstanceOf(QuotaError);
    expect(calls).toBe(1);
  });

  it("berhenti mengambil potongan baru saat kuota habis", async () => {
    const seen: number[] = [];
    const statuses: Record<number, ChunkStatus> = {};
    const summary = await runChunks({
      indexes: [0, 1, 2, 3],
      concurrency: 1,
      signal,
      send: async (index) => {
        seen.push(index);
        if (index === 1) throw new QuotaError("quota");
        return { language: "id", segments: [] };
      },
      onStatus: (index, status) => {
        statuses[index] = status;
      },
    });
    expect(summary.quotaExhausted).toBe(true);
    expect(seen).toEqual([0, 1]);
    expect(statuses[0]).toBe("done");
    expect(statuses[1]).toBe("pending");
  });

  it("menandai potongan yang gagal dan tetap lanjut", async () => {
    const statuses: Record<number, ChunkStatus> = {};
    await runChunks({
      indexes: [0, 1],
      concurrency: 1,
      signal,
      send: async (index) => {
        if (index === 0) throw new Error("rusak");
        return { language: "id", segments: [] };
      },
      onStatus: (index, status) => {
        statuses[index] = status;
      },
    });
    expect(statuses).toEqual({ 0: "failed", 1: "done" });
  });
});

describe("penguncian bahasa", () => {
  it("bagian pertama menentukan bahasa bagian lain", async () => {
    const used: string[] = [];
    const locks: string[] = [];
    await runWithLanguage({
      indexes: [0, 1, 2],
      concurrency: 1,
      signal,
      language: "auto",
      locked: null,
      onLock: (code) => locks.push(code),
      onStatus: () => undefined,
      send: async (_index, _signal, language) => {
        used.push(language);
        return { language: used.length === 1 ? "id" : "es", segments: [] };
      },
    });
    expect(used).toEqual(["auto", "id", "id"]);
    expect(locks).toEqual(["id"]);
  });

  it("pilihan manual tidak dideteksi ulang", async () => {
    const used: string[] = [];
    await runWithLanguage({
      indexes: [0, 1],
      concurrency: 1,
      signal,
      language: "jw-id",
      locked: null,
      onLock: () => undefined,
      onStatus: () => undefined,
      send: async (_index, _signal, language) => {
        used.push(language);
        return { language: "id", segments: [] };
      },
    });
    expect(used).toEqual(["jw-id", "jw-id"]);
  });
});

describe("API", () => {
  const post = async (language: string): Promise<{ status: number; input: Record<string, unknown> }> => {
    let input: Record<string, unknown> = {};
    const response = await handleTranscribe(
      new Request(`https://x.test/api/transcribe?language=${language}`, { method: "POST", body: "UklGRabc" }),
      {
        AI: {
          run: async (_model, received) => {
            input = received;
            return { text: "a", segments: [] };
          },
        },
      },
    );
    return { status: response.status, input };
  };

  it("campuran Jawa memakai bahasa Indonesia dan petunjuk kosakata", async () => {
    const { status, input } = await post("jw-id");
    expect(status).toBe(200);
    expect(input.language).toBe("id");
    expect(typeof input.initial_prompt).toBe("string");
  });

  it("deteksi otomatis tidak mengirim bahasa", async () => {
    const { input } = await post("auto");
    expect(input.language).toBe(undefined);
  });

  it("menolak kode bahasa aneh", async () => {
    const { status } = await post("x;y");
    expect(status).toBe(400);
  });
});
