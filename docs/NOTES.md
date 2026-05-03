# Architecture Notes — Keylogger

## Why pynput?

`pynput` wraps OS-level input hooks on all three major platforms:
- **Linux** — uses Xlib (X11) or evdev depending on display server
- **macOS** — uses the Quartz event tap API (requires Accessibility permission)
- **Windows** — uses `SetWindowsHookEx(WH_KEYBOARD_LL, ...)` under the hood

Rolling our own hook would require three separate platform implementations and
is out of scope for this educational project. pynput gives us a clean
`Listener` abstraction with identical callback signatures.

## Buffer-then-flush vs. write-per-key

Writing to disk on every keystroke is:
1. Slow (many small I/O ops)
2. Noisy on disk (detectable by monitoring tools more easily)

Accumulating in an in-memory list and flushing on a timer is the conventional
approach. The buffer is protected by a `threading.Lock` so the listener thread
and the flush thread don't race.

## Log rotation

Unbounded logs grow large quickly when capturing all input. A simple size-based
rotation renames the current log to `keylog.txt.YYYYMMDD_HHMMSS` and starts a
fresh file. This keeps individual files manageable.

## parser.py design

The parser is a completely separate tool — intentionally offline/forensic. It
reads an existing log file, strips control-token noise, and extracts:
- Session boundaries (marked by `===` headers written at logger startup)
- Word frequency (useful for reconstructing typed content)
- Trigram frequency (useful for language/typing-pattern analysis)
- Backspace rate (can indicate transcription difficulty, incorrect passwords, etc.)

## Ethical & Legal Notes

This code is written purely for malware-analysis and forensics education:
- Understand how keyloggers work so you can detect and remove them
- Study the Windows `WH_KEYBOARD_LL` hook chain
- Practice writing IOCs (indicators of compromise) for keylogger detection

**Never run this on a machine you don't own or don't have explicit written
permission to monitor.** Deploying a keylogger without consent is a crime in
virtually every jurisdiction.
