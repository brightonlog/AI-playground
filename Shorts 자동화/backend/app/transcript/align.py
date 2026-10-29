"""Put human caption text onto Whisper words, keeping Whisper's word timing."""

from difflib import SequenceMatcher

from app.core.config import get_settings


def _chars(texts: list[str]) -> tuple[str, list[int]]:
    """Text without spaces, and the index of the item each character came from."""
    chars, owner = [], []
    for i, text in enumerate(texts):
        for ch in text:
            if not ch.isspace():
                chars.append(ch)
                owner.append(i)
    return "".join(chars), owner


def align_words(words: list[str], caption: str) -> list[str] | None:
    """Caption text split along Whisper word boundaries, or None when they match too poorly.

    Matching is per character with spaces removed, because captions and Whisper space Korean
    differently. Caption characters with no Whisper counterpart join the word before them;
    caption text before the first or after the last match (outside the section) is dropped.
    """
    spoken, owner = _chars(words)
    target, _ = _chars([caption])
    if not spoken or not target:
        return None
    matcher = SequenceMatcher(None, spoken, target, autojunk=False)
    blocks = [b for b in matcher.get_matching_blocks() if b.size]
    if not blocks or sum(b.size for b in blocks) / len(spoken) < get_settings().caption_align_min:
        return None
    lo, hi = blocks[0].b, blocks[-1].b + blocks[-1].size  # caption span covering the section
    out = [""] * len(words)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        j1, j2 = max(j1, lo), min(j2, hi)
        if j1 >= j2 or tag == "delete":
            continue
        if tag == "insert":
            out[owner[max(i1 - 1, 0)]] += target[j1:j2]
            continue
        # equal / replace: spread caption chars over the Whisper chars they stand in for
        for k in range(j1, j2):
            src = i1 + (k - j1) * (i2 - i1) // (j2 - j1)
            out[owner[src]] += target[k]
    return [new or old.strip() for new, old in zip(out, words, strict=True)]
