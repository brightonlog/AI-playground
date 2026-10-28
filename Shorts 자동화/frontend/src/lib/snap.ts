import type { Sentence } from "../api/client";

/** Snap a range to sentence boundaries: start to the nearest sentence start, end to the nearest end. */
export function snapToSentences(sentences: Sentence[], start: number, end: number) {
  if (sentences.length === 0) return { start, end };
  const nearest = (values: number[], t: number) =>
    values.reduce((best, v) => (Math.abs(v - t) < Math.abs(best - t) ? v : best));
  const snappedStart = nearest(
    sentences.map((s) => s.start_sec),
    start,
  );
  const ends = sentences.map((s) => s.end_sec).filter((e) => e > snappedStart);
  return { start: snappedStart, end: ends.length ? nearest(ends, end) : end };
}
