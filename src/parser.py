"""
parser.py — Offline log parser / report generator for keylog.txt files.

Reads a keylog produced by keylogger.py and generates a summary:
  - Session list with timestamps
  - Top-N most-frequent character sequences (trigrams)
  - Detected typed words (whitespace/Enter delimited)
  - Basic statistics: total keystrokes, backspace rate

Usage:
    python parser.py <logfile> [--top 20] [--min-word 3]
"""

import argparse
import collections
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Strip timestamp annotations like [12:34:56.789]
_TS_RE = re.compile(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]")

# Recognised control tokens
_CTRL = {
    "[ENTER]", "[TAB]", "[BKSP]", "[DEL]", "[ESC]", "[CAPS]",
    "[CTRL]", "[ALT]", "[WIN]", "[UP]", "[DOWN]", "[LEFT]", "[RIGHT]",
    "[HOME]", "[END]", "[PGUP]", "[PGDN]",
}
_FN_RE = re.compile(r"\[F\d{1,2}\]")
_VK_RE = re.compile(r"\[\d+\]")


def strip_control_tokens(text: str) -> str:
    """Replace control tokens with spaces so word extraction works."""
    text = _TS_RE.sub("", text)
    text = _FN_RE.sub(" ", text)
    text = _VK_RE.sub(" ", text)
    for tok in _CTRL:
        text = text.replace(tok, " ")
    return text


def parse_sessions(path: Path) -> list[dict]:
    """Split the log file into sessions based on the '===' headers."""
    content = path.read_text(encoding="utf-8", errors="replace")
    raw_sessions = re.split(r"={3,}", content)

    sessions = []
    i = 0
    while i < len(raw_sessions) - 1:
        header_block = raw_sessions[i].strip()
        # Session header line follows the first separator
        body = raw_sessions[i + 1] if (i + 1) < len(raw_sessions) else ""
        ts_match = re.search(r"Session started: (.+)", header_block + body)
        timestamp = ts_match.group(1).strip() if ts_match else "unknown"
        # The actual keystrokes are in the *next* block after the header line
        keystroke_block = raw_sessions[i + 2] if (i + 2) < len(raw_sessions) else ""
        sessions.append({"timestamp": timestamp, "raw": keystroke_block})
        i += 3

    # Fallback: no session markers found
    if not sessions:
        sessions.append({"timestamp": "unknown", "raw": content})

    return sessions


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def extract_words(raw: str, min_len: int) -> list[str]:
    clean = strip_control_tokens(raw)
    return [w for w in re.findall(r"[a-zA-Z0-9_@.\-]+", clean) if len(w) >= min_len]


def trigram_freq(raw: str, top_n: int) -> list[tuple[str, int]]:
    clean = strip_control_tokens(raw)
    clean = re.sub(r"\s+", " ", clean)
    tris = [clean[i:i+3] for i in range(len(clean) - 2)]
    return collections.Counter(tris).most_common(top_n)


def count_backspaces(raw: str) -> int:
    return raw.count("[BKSP]")


def count_keystrokes(raw: str) -> int:
    clean = _TS_RE.sub("", raw)
    # Count each visible char plus each bracketed token
    tokens = re.findall(r"\[.+?\]|.", clean)
    return len(tokens)


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(sessions: list[dict], top_n: int, min_word: int) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("KEYSTROKE LOG ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"Sessions found : {len(sessions)}")
    lines.append("")

    all_raw = "\n".join(s["raw"] for s in sessions)
    total_ks  = count_keystrokes(all_raw)
    total_bks = count_backspaces(all_raw)
    bk_rate   = (total_bks / total_ks * 100) if total_ks else 0

    lines.append(f"Total keystrokes : {total_ks}")
    lines.append(f"Backspaces       : {total_bks}  ({bk_rate:.1f}% of all keys)")
    lines.append("")

    for idx, sess in enumerate(sessions, 1):
        lines.append(f"{'─'*60}")
        lines.append(f"Session {idx}  |  started: {sess['timestamp']}")
        lines.append(f"{'─'*60}")

        ks   = count_keystrokes(sess["raw"])
        bks  = count_backspaces(sess["raw"])
        words = extract_words(sess["raw"], min_word)
        word_freq = collections.Counter(words).most_common(top_n)
        tris = trigram_freq(sess["raw"], top_n)

        lines.append(f"  Keystrokes  : {ks}")
        lines.append(f"  Backspaces  : {bks}")
        lines.append(f"  Unique words: {len(set(words))}")
        lines.append("")

        if word_freq:
            lines.append(f"  Top-{top_n} words:")
            for word, cnt in word_freq:
                lines.append(f"    {cnt:5d}  {word}")
            lines.append("")

        if tris:
            lines.append(f"  Top-{top_n} trigrams:")
            for tri, cnt in tris:
                lines.append(f"    {cnt:5d}  {repr(tri)}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyse a keylog.txt file")
    p.add_argument("logfile", help="Path to the log file produced by keylogger.py")
    p.add_argument("--top",      type=int, default=20, help="Show top N items (default: 20)")
    p.add_argument("--min-word", type=int, default=3,  help="Min word length (default: 3)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.logfile)
    if not path.exists():
        sys.exit(f"[!] File not found: {path}")

    sessions = parse_sessions(path)
    report   = render_report(sessions, args.top, args.min_word)
    print(report)


if __name__ == "__main__":
    main()
