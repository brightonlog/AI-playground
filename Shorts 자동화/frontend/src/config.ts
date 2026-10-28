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
