import type { Sentence } from "../api/client";

function snapTo(t: number, boundaries: number[], tolerance: number): number {
  let best = t;
  let bestDiff = Infinity;
  for (const b of boundaries) {
    const diff = Math.abs(b - t);
    if (diff <= tolerance && diff < bestDiff) {
      best = b;
      bestDiff = diff;
    }
  }
  return best;
}

/**
 * Pull each edge onto a sentence boundary only when it lands within `tolerance` seconds of one
 * (start to sentence starts, end to sentence ends); otherwise keep it where it was dropped.
 */
export function snapToSentences(sentences: Sentence[], start: number, end: number, tolerance: number) {
  const s = snapTo(start, sentences.map((x) => x.start_sec), tolerance);
  const e = snapTo(end, sentences.map((x) => x.end_sec), tolerance);
  return e > s ? { start: s, end: e } : { start, end };
}
