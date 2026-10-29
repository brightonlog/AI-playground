// Section length accepted by POST /shorts (spec 7). Keep in sync with the backend.
export const SHORT_MIN_SEC = 15;
export const SHORT_MAX_SEC = 60;
// How often the playhead reads the player's time.
export const PLAYHEAD_POLL_MS = 250;
// A dragged edge sticks to a sentence boundary only within this distance.
export const SNAP_TOLERANCE_SEC = 0.5;
// Step for the fine-adjust buttons.
export const NUDGE_SEC = 0.5;
// Waveform zoom steps in pixels per second; 0 fits the whole video.
export const ZOOM_LEVELS = [0, 2, 5, 10, 20, 50];
// Edited output length limits (backend output_min_sec / output_max_sec).
export const OUTPUT_MIN_SEC = 5;
export const OUTPUT_MAX_SEC = 60;
// How often to check whether the re-rendered preview is ready.
export const PREVIEW_POLL_MS = 1000;
// Text limits of edit operations (backend schemas/edit.py).
export const TITLE_MAX = 30;
export const NARRATION_MAX = 40;
export const WORD_MAX = 20;
// Pauses at least this long are suggested as cuts.
export const SILENCE_GAP_SEC = 0.5;
