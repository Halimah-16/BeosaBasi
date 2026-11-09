import React, { useMemo, useRef, useState } from "react";
import {
  bytesToBase64,
  computePeaks,
  decodeToMono,
  encodeWav,
  isSilent,
  planChunks,
  SAMPLE_RATE,
  type ChunkRange,
} from "./audio";
import { formatClock, toDocx, toSrt, toTxt, toVtt, type Segment } from "./formats";
import { postChunk, runWithLanguage, type ChunkResult, type ChunkStatus } from "./transcribe";

const MAX_FILE_BYTES = 200 * 1024 * 1024;
const MAX_SECONDS = 120 * 60;
const WAVE_BARS = 140;

const LANGUAGES: { code: string; label: string }[] = [
  { code: "auto", label: "Deteksi otomatis" },
  { code: "id", label: "Indonesia" },
  { code: "en", label: "Inggris" },
  { code: "jw-id", label: "Campuran Jawa dan Indonesia" },
  { code: "jw", label: "Jawa" },
  { code: "su", label: "Sunda" },
  { code: "ms", label: "Melayu" },
  { code: "ar", label: "Arab" },
  { code: "zh", label: "Mandarin" },
  { code: "ja", label: "Jepang" },
  { code: "ko", label: "Korea" },
  { code: "hi", label: "Hindi" },
  { code: "th", label: "Thai" },
  { code: "vi", label: "Vietnam" },
  { code: "tl", label: "Tagalog" },
  { code: "nl", label: "Belanda" },
  { code: "de", label: "Jerman" },
  { code: "fr", label: "Prancis" },
  { code: "es", label: "Spanyol" },
  { code: "pt", label: "Portugis" },
  { code: "it", label: "Italia" },
  { code: "ru", label: "Rusia" },
  { code: "tr", label: "Turki" },
];

interface LoadedAudio {
  name: string;
  samples: Float32Array;
  ranges: ChunkRange[];
  peaks: number[];
}

type Phase = "empty" | "reading" | "ready" | "running" | "finished";

function baseName(name: string): string {
  return name.replace(/\.[^.]+$/, "") || "transkrip";
}

function saveFile(content: BlobPart, type: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function languageName(code: string): string {
  try {
    return new Intl.DisplayNames(["id"], { type: "language" }).of(code) ?? code;
  } catch {
    return code;
  }
}

function Waveform(props: { audio: LoadedAudio; statuses: ChunkStatus[] }): React.JSX.Element {
  const { audio, statuses } = props;
  const statusForBar = (bar: number): ChunkStatus => {
    const position = ((bar + 0.5) / WAVE_BARS) * audio.samples.length;
    const index = audio.ranges.findIndex((range) => position < range.end);
    return statuses[index] ?? "pending";
  };
  return (
    <svg
      className="wave"
      viewBox={`0 0 ${WAVE_BARS * 6} 96`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Bentuk gelombang audio dan bagian yang sudah ditranskrip"
    >
      {audio.peaks.map((peak, bar) => {
        const height = Math.max(3, peak * 92);
        return (
          <rect
            key={bar}
            className={`bar bar-${statusForBar(bar)}`}
            x={bar * 6 + 1}
            y={(96 - height) / 2}
            width={4}
            height={height}
          />
        );
      })}
    </svg>
  );
}

export default function App(): React.JSX.Element {
  const [phase, setPhase] = useState<Phase>("empty");
  const [audio, setAudio] = useState<LoadedAudio | null>(null);
  const [language, setLanguage] = useState("auto");
  const [statuses, setStatuses] = useState<ChunkStatus[]>([]);
  const [results, setResults] = useState<Record<number, ChunkResult>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const lockedLanguageRef = useRef<string | null>(null);

  const ordered = useMemo(
    () =>
      Object.keys(results)
        .map(Number)
        .sort((a, b) => a - b),
    [results],
  );
  const segments: Segment[] = useMemo(
    () => ordered.flatMap((index) => results[index].segments),
    [ordered, results],
  );
  const detected = useMemo(() => {
    const codes = new Set(ordered.map((index) => results[index].language).filter(Boolean) as string[]);
    return [...codes].map(languageName).join(", ");
  }, [ordered, results]);

  const finishedCount = statuses.filter((status) => status === "done" || status === "silent").length;
  const failedCount = statuses.filter((status) => status === "failed").length;
  const unfinishedCount = statuses.length - finishedCount;
  const percent = statuses.length > 0 ? Math.round((finishedCount / statuses.length) * 100) : 0;
  const durationSeconds = audio ? audio.samples.length / SAMPLE_RATE : 0;

  async function chooseFile(file: File): Promise<void> {
    setError(null);
    setNotice(null);
    setResults({});
    setStatuses([]);
    setAudio(null);
    lockedLanguageRef.current = null;
    if (file.size > MAX_FILE_BYTES) {
      setError("Berkas lebih dari 200 MB. Pilih berkas yang lebih kecil atau potong dulu rekamannya.");
      setPhase("empty");
      return;
    }
    setPhase("reading");
    try {
      const samples = await decodeToMono(file);
      if (samples.length / SAMPLE_RATE > MAX_SECONDS) {
        setError("Rekaman lebih dari 2 jam. Potong dulu menjadi beberapa berkas.");
        setPhase("empty");
        return;
      }
      const ranges = planChunks(samples);
      setAudio({ name: file.name, samples, ranges, peaks: computePeaks(samples, WAVE_BARS) });
      setStatuses(
        ranges.map((range): ChunkStatus => (isSilent(samples.subarray(range.start, range.end)) ? "silent" : "pending")),
      );
      setPhase("ready");
    } catch {
      setError("Browser tidak bisa membaca berkas ini. Coba format MP3, WAV, M4A, atau MP4.");
      setPhase("empty");
    }
  }

  async function start(): Promise<void> {
    if (!audio) return;
    const indexes = statuses.flatMap((status, index) =>
      status === "pending" || status === "failed" ? [index] : [],
    );
    setError(null);
    setNotice(null);
    setPhase("running");
    const controller = new AbortController();
    abortRef.current = controller;

    const summary = await runWithLanguage({
      indexes,
      signal: controller.signal,
      language,
      locked: lockedLanguageRef.current,
      onLock: (code) => {
        lockedLanguageRef.current = code;
      },
      send: (index, signal, activeLanguage) => {
        const range = audio.ranges[index];
        const wav = encodeWav(audio.samples.subarray(range.start, range.end));
        return postChunk({
          base64: bytesToBase64(wav),
          language: activeLanguage,
          offsetSeconds: range.start / SAMPLE_RATE,
          signal,
        });
      },
      onStatus: (index, status, result) => {
        setStatuses((current) => current.map((value, i) => (i === index ? status : value)));
        if (result) setResults((current) => ({ ...current, [index]: result }));
      },
    });

    abortRef.current = null;
    setPhase("finished");
    if (summary.quotaExhausted) {
      setNotice("Kuota harian sudah habis. Kuota terisi lagi pukul 07.00 WIB. Hasil yang sudah jadi tetap bisa disimpan.");
    }
  }

  function reset(): void {
    abortRef.current?.abort();
    setAudio(null);
    setStatuses([]);
    setResults({});
    setError(null);
    setNotice(null);
    setPhase("empty");
    if (inputRef.current) inputRef.current.value = "";
  }

  function editSegment(chunk: number, position: number, text: string): void {
    setResults((current) => ({
      ...current,
      [chunk]: {
        ...current[chunk],
        segments: current[chunk].segments.map((segment, i) => (i === position ? { ...segment, text } : segment)),
      },
    }));
  }

  async function copyText(): Promise<void> {
    await navigator.clipboard.writeText(toTxt(segments));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  const name = audio ? baseName(audio.name) : "transkrip";
  const running = phase === "running";

  return (
    <div className="page">
      <header className={dragging ? "stage stage-drag" : "stage"}
        onDragOver={(event) => {
          event.preventDefault();
          if (!running) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file && !running) void chooseFile(file);
        }}
      >
        <div className="stage-inner">
          <p className="brand">BeosaBasi</p>
          <h1>Kirim audionya, terima teksnya.</h1>

          {audio ? (
            <div className="track">
              <div className="track-meta">
                <span className="track-name">{audio.name}</span>
                <span>{formatClock(durationSeconds)}</span>
              </div>
              <Waveform audio={audio} statuses={statuses} />
            </div>
          ) : (
            <button type="button" className="drop" disabled={phase === "reading"} onClick={() => inputRef.current?.click()}>
              {phase === "reading" ? (
                <span>Membaca audio…</span>
              ) : (
                <>
                  <strong>Pilih berkas audio atau video</strong>
                  <span>atau jatuhkan di sini. MP3, WAV, M4A, atau MP4, sampai 2 jam.</span>
                </>
              )}
            </button>
          )}
          <input
            ref={inputRef}
            className="visually-hidden"
            type="file"
            accept="audio/*,video/*"
            aria-label="Berkas audio atau video"
            tabIndex={-1}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void chooseFile(file);
            }}
          />

          {audio && (
            <div className="controls">
              {phase === "ready" && (
                <>
                  <label className="field">
                    <span>Bahasa dalam rekaman</span>
                    <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                      {LANGUAGES.map((item) => (
                        <option key={item.code} value={item.code}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="primary" onClick={() => void start()}>
                    Transkrip audio
                  </button>
                  <button type="button" className="quiet" onClick={reset}>
                    Ganti berkas
                  </button>
                </>
              )}
              {running && (
                <>
                  <p className="progress" role="status">
                    Menyalin {percent}% ({finishedCount} dari {statuses.length} bagian)
                  </p>
                  <button type="button" className="quiet" onClick={() => abortRef.current?.abort()}>
                    Hentikan
                  </button>
                </>
              )}
              {phase === "finished" && (
                <>
                  {unfinishedCount > 0 && !notice && (
                    <button type="button" className="primary" onClick={() => void start()}>
                      {failedCount > 0 ? `Ulangi ${failedCount} bagian yang gagal` : "Lanjutkan transkrip"}
                    </button>
                  )}
                  <button type="button" className="quiet" onClick={reset}>
                    Transkrip audio lain
                  </button>
                </>
              )}
            </div>
          )}

          {error && (
            <p className="message" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="message" role="status">
              {notice}
            </p>
          )}
        </div>
      </header>

      <main className="sheet">
        {segments.length > 0 ? (
          <>
            <div className="sheet-head">
              <div>
                <h2>Transkrip</h2>
                {language === "auto" && detected && <p className="detected">Bahasa terdeteksi: {detected}</p>}
              </div>
              <div className="exports" aria-label="Simpan transkrip">
                <button type="button" onClick={() => void copyText()}>
                  {copied ? "Tersalin" : "Salin teks"}
                </button>
                <button type="button" onClick={() => saveFile(toTxt(segments), "text/plain;charset=utf-8", `${name}.txt`)}>
                  TXT
                </button>
                <button
                  type="button"
                  onClick={() =>
                    saveFile(
                      toDocx(segments) as BlobPart,
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                      `${name}.docx`,
                    )
                  }
                >
                  DOCX
                </button>
                <button type="button" onClick={() => saveFile(toSrt(segments), "application/x-subrip;charset=utf-8", `${name}.srt`)}>
                  SRT
                </button>
                <button type="button" onClick={() => saveFile(toVtt(segments), "text/vtt;charset=utf-8", `${name}.vtt`)}>
                  VTT
                </button>
              </div>
            </div>
            <ol className="lines">
              {ordered.flatMap((chunk) =>
                results[chunk].segments.map((segment, position) => (
                  <li key={`${chunk}-${position}`}>
                    <time>{formatClock(segment.start)}</time>
                    <textarea
                      aria-label={`Teks pada menit ${formatClock(segment.start)}`}
                      rows={Math.max(1, Math.ceil(segment.text.length / 68))}
                      value={segment.text}
                      onChange={(event) => editSegment(chunk, position, event.target.value)}
                    />
                  </li>
                )),
              )}
            </ol>
          </>
        ) : phase === "finished" && failedCount === 0 && !notice ? (
          <p className="hint">Tidak ada ucapan yang terdengar di rekaman ini.</p>
        ) : (
          !running && (
            <p className="hint">
              Audio diproses oleh Cloudflare Workers AI dan tidak disimpan di sini. Transkrip hanya ada di browser ini,
              jadi simpan dulu sebelum menutup halaman.
            </p>
          )
        )}
      </main>
    </div>
  );
}
