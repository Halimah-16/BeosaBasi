/**
 * POST /api/transcribe?language=id
 *
 * Badan permintaan: satu potongan audio WAV yang sudah di-base64 (teks polos).
 * Browser yang memotong dan meng-encode audio, supaya Function tidak menghabiskan
 * batas waktu CPU. Audio tidak disimpan: hanya diteruskan ke Workers AI.
 */

const MODEL = "@cf/openai/whisper-large-v3-turbo";
const MAX_BODY_CHARS = 6 * 1024 * 1024;
const WAV_BASE64_PREFIX = "UklGR"; // "RIFF" dalam base64

/**
 * Model lebih kuat di bahasa Indonesia daripada Jawa, jadi rekaman campuran
 * ditranskrip sebagai Indonesia dengan contoh kosakata Jawa sebagai petunjuk.
 */
const PRESETS = new Map([
  [
    "jw-id",
    {
      language: "id",
      prompt:
        "Obrolan campuran bahasa Jawa dan bahasa Indonesia. Aku ora ngerti, kowe arep nang ndi? " +
        "Piye kabare, Mas? Wis mangan durung? Iya, sampun. Sakjane aku yo pengen, tapi rung iso. Matur nuwun, Mbak.",
    },
  ],
]);

interface WhisperSegment {
  start?: number;
  end?: number;
  text?: string;
}

interface WhisperOutput {
  text?: string;
  segments?: WhisperSegment[];
  transcription_info?: { language?: string };
}

export interface TranscribeEnv {
  AI: { run(model: string, input: Record<string, unknown>): Promise<WhisperOutput> };
}

function fail(status: number, code: string, message: string): Response {
  return Response.json({ code, message }, { status });
}

function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("Origin");
  if (origin === null) return true; // bukan permintaan lintas situs dari browser
  try {
    return new URL(origin).host === new URL(request.url).host;
  } catch {
    return false;
  }
}

function isQuotaError(error: unknown): boolean {
  const text = error instanceof Error ? error.message : String(error);
  return /4006|neuron|daily free allocation/i.test(text);
}

export async function handleTranscribe(request: Request, env: TranscribeEnv): Promise<Response> {
  if (!isSameOrigin(request)) {
    return fail(403, "forbidden", "Permintaan dari situs lain ditolak.");
  }
  if (!env.AI) {
    return fail(500, "not_configured", "Layanan transkripsi belum terhubung ke server.");
  }

  const language = new URL(request.url).searchParams.get("language") ?? "auto";
  const preset = PRESETS.get(language);
  if (language !== "auto" && !preset && !/^[a-z]{2,3}$/.test(language)) {
    return fail(400, "bad_language", "Kode bahasa tidak dikenali.");
  }

  const declaredLength = Number(request.headers.get("Content-Length") ?? "0");
  if (declaredLength > MAX_BODY_CHARS) {
    return fail(413, "too_large", "Potongan audio terlalu besar.");
  }
  const audio = await request.text();
  if (audio.length > MAX_BODY_CHARS) {
    return fail(413, "too_large", "Potongan audio terlalu besar.");
  }
  if (!audio.startsWith(WAV_BASE64_PREFIX)) {
    return fail(400, "bad_audio", "Data audio tidak valid.");
  }

  const input: Record<string, unknown> = {
    audio,
    vad_filter: true,
    condition_on_previous_text: false,
  };
  if (preset) {
    input.language = preset.language;
    input.initial_prompt = preset.prompt;
  } else if (language !== "auto") {
    input.language = language;
  }

  let output: WhisperOutput;
  try {
    output = await env.AI.run(MODEL, input);
  } catch (error) {
    if (isQuotaError(error)) {
      return fail(429, "quota_exhausted", "Kuota transkripsi hari ini sudah habis.");
    }
    console.error("transcribe_failed", error instanceof Error ? error.message : "unknown");
    return fail(502, "model_error", "Mesin transkripsi gagal memproses bagian ini.");
  }

  const segments = (output.segments ?? [])
    .map((segment) => ({
      start: segment.start ?? 0,
      end: segment.end ?? segment.start ?? 0,
      text: (segment.text ?? "").trim(),
    }))
    .filter((segment) => segment.text.length > 0);

  return Response.json({
    text: (output.text ?? "").trim(),
    language: output.transcription_info?.language ?? null,
    segments,
  });
}

export const onRequestPost = (context: { request: Request; env: TranscribeEnv }): Promise<Response> =>
  handleTranscribe(context.request, context.env);
