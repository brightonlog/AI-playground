'use strict';
// Text hygiene for everything that reaches disk or the terminal.

// C0/C1 controls (incl. ESC), DEL, zero-width, bidi overrides/isolates, BOM, line/para separators.
const UNSAFE = /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\u2060-\u2069\ufeff]/g;

const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)/g,
  /\bsk-[A-Za-z0-9_-]{8,}/g, // OpenAI / Anthropic style
  /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}/g, // GitHub
  /\bgithub_pat_[A-Za-z0-9_]{20,}/g,
  /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g, // AWS access key id
  /\bAIza[0-9A-Za-z_-]{30,}/g, // Google API key
  /\bxox[abprs]-[A-Za-z0-9-]{10,}/g, // Slack
  /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}/g, // JWT
  /\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{12,}/g,
  /\b[a-z][a-z0-9+.-]*:\/\/[^\s/:@]+:[^\s/@]+@/gi, // scheme://user:pass@
  /\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\b\s*(?:[:=]|is)\s*\S+/gi,
  /(?:비밀번호|암호)\s*(?:[:=]|은|는)\s*\S+/g, // no \b: it only sees ASCII word characters
];

const MASK = '[redacted]';
const SCAN_LIMIT = 4000; // only this much of a prompt is ever inspected

function clean(value, max) {
  if (typeof value !== 'string') return '';
  const out = value.replace(/[\r\n\t]+/g, ' ').replace(UNSAFE, '').replace(/ {2,}/g, ' ').trim();
  if (!max || out.length <= max) return out;
  return Array.from(out).slice(0, max - 1).join('') + '…';
}

// Mask BEFORE truncating so a secret straddling the cut cannot leak its head.
function maskSecrets(value) {
  if (typeof value !== 'string') return '';
  let out = value.slice(0, SCAN_LIMIT);
  for (const re of SECRET_PATTERNS) out = out.replace(re, MASK);
  return out;
}

function safeText(value, max) {
  return clean(maskSecrets(value), max);
}

module.exports = { clean, safeText };
