/** Konversi transkrip ke TXT, SRT, VTT, dan DOCX tanpa dependensi tambahan. */

export interface Segment {
  start: number;
  end: number;
  text: string;
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(rest).padStart(2, "0");
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`;
}

function cueTime(seconds: number, separator: string): string {
  const millis = Math.max(0, Math.round(seconds * 1000));
  const hours = Math.floor(millis / 3600000);
  const minutes = Math.floor((millis % 3600000) / 60000);
  const secs = Math.floor((millis % 60000) / 1000);
  const rest = millis % 1000;
  const pad = (value: number, size = 2): string => String(value).padStart(size, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(secs)}${separator}${pad(rest, 3)}`;
}

/** Baris diapit spasi dibuang dan baris kosong dihapus: keduanya merusak blok SRT/VTT. */
function cueText(text: string): string {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");
}

function usable(segments: Segment[]): Segment[] {
  return segments.filter((segment) => segment.text.trim().length > 0);
}

export function toTxt(segments: Segment[]): string {
  return usable(segments)
    .map((segment) => segment.text.trim())
    .join("\n\n");
}

export function toSrt(segments: Segment[]): string {
  return usable(segments)
    .map(
      (segment, index) =>
        `${index + 1}\n${cueTime(segment.start, ",")} --> ${cueTime(segment.end, ",")}\n${cueText(segment.text)}\n`,
    )
    .join("\n");
}

export function toVtt(segments: Segment[]): string {
  const cues = usable(segments)
    .map(
      (segment) =>
        `${cueTime(segment.start, ".")} --> ${cueTime(segment.end, ".")}\n${cueText(segment.text).replace(/-->/g, "->")}\n`,
    )
    .join("\n");
  return `WEBVTT\n\n${cues}`;
}

function escapeXml(text: string): string {
  return (
    text
      // Karakter kontrol tidak sah di XML 1.0 dan membuat Word menolak berkas.
      // eslint-disable-next-line no-control-regex
      .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f￾￿]/g, "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
  );
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

/** ZIP tanpa kompresi (metode store): cukup untuk DOCX yang valid. */
function zipStore(files: { name: string; data: string }[]): Uint8Array {
  const encoder = new TextEncoder();
  const entries = files.map((file) => {
    const name = encoder.encode(file.name);
    const data = encoder.encode(file.data);
    return { name, data, crc: crc32(data) };
  });
  const localSize = entries.reduce((sum, e) => sum + 30 + e.name.length + e.data.length, 0);
  const centralSize = entries.reduce((sum, e) => sum + 46 + e.name.length, 0);
  const output = new Uint8Array(new ArrayBuffer(localSize + centralSize + 22));
  const view = new DataView(output.buffer);
  const utf8Flag = 0x0800;
  const dosDate = 0x5a21; // 2025-01-01, agar keluaran deterministik

  let offset = 0;
  const offsets: number[] = [];
  for (const entry of entries) {
    offsets.push(offset);
    view.setUint32(offset, 0x04034b50, true);
    view.setUint16(offset + 4, 20, true);
    view.setUint16(offset + 6, utf8Flag, true);
    view.setUint16(offset + 12, dosDate, true);
    view.setUint32(offset + 14, entry.crc, true);
    view.setUint32(offset + 18, entry.data.length, true);
    view.setUint32(offset + 22, entry.data.length, true);
    view.setUint16(offset + 26, entry.name.length, true);
    output.set(entry.name, offset + 30);
    output.set(entry.data, offset + 30 + entry.name.length);
    offset += 30 + entry.name.length + entry.data.length;
  }

  const centralStart = offset;
  entries.forEach((entry, index) => {
    view.setUint32(offset, 0x02014b50, true);
    view.setUint16(offset + 4, 20, true);
    view.setUint16(offset + 6, 20, true);
    view.setUint16(offset + 8, utf8Flag, true);
    view.setUint16(offset + 14, dosDate, true);
    view.setUint32(offset + 16, entry.crc, true);
    view.setUint32(offset + 20, entry.data.length, true);
    view.setUint32(offset + 24, entry.data.length, true);
    view.setUint16(offset + 28, entry.name.length, true);
    view.setUint32(offset + 42, offsets[index], true);
    output.set(entry.name, offset + 46);
    offset += 46 + entry.name.length;
  });

  view.setUint32(offset, 0x06054b50, true);
  view.setUint16(offset + 8, entries.length, true);
  view.setUint16(offset + 10, entries.length, true);
  view.setUint32(offset + 12, offset - centralStart, true);
  view.setUint32(offset + 16, centralStart, true);
  return output;
}

export function toDocx(segments: Segment[]): Uint8Array {
  const paragraphs = usable(segments)
    .map((segment) => {
      const stamp = `<w:r><w:rPr><w:color w:val="5A6385"/></w:rPr><w:t xml:space="preserve">[${formatClock(segment.start)}] </w:t></w:r>`;
      const body = `<w:r><w:t xml:space="preserve">${escapeXml(segment.text.trim())}</w:t></w:r>`;
      return `<w:p>${stamp}${body}</w:p>`;
    })
    .join("");
  const header = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
  return zipStore([
    {
      name: "[Content_Types].xml",
      data: `${header}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>`,
    },
    {
      name: "_rels/.rels",
      data: `${header}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>`,
    },
    {
      name: "word/document.xml",
      data: `${header}<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>${paragraphs}<w:sectPr/></w:body></w:document>`,
    },
  ]);
}
