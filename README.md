# Keylogger

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

> **Difficulty:** Beginner | **Language:** Python | **Requires:** pynput

Educational keystroke logger with a companion offline forensics analyser. Captures keystrokes to a rotating log file using OS-level input hooks, then lets you parse sessions, extract word frequency, and compute backspace rates. Built to understand how keyloggers work — so you can detect and remove them.

---

## What You'll Build

Two tools:

| Tool | Purpose |
|------|---------|
| `keylogger.py` | Captures keystrokes to a rotating log file with optional timestamps |
| `parser.py` | Offline forensics analyser — extracts words, trigrams, and session stats from a log file |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Input capture | `pynput` (wraps OS hooks: `WH_KEYBOARD_LL` / Xlib / Quartz) |
| Concurrency | `threading.Thread` + `threading.Lock` |
| Log rotation | Size-based file rename |

---

## Project Structure

```
02-keylogger/
├── README.md
├── .gitignore
├── src/
│   ├── keylogger.py      ← Keystroke listener + log manager
│   ├── parser.py         ← Offline log analyser
│   └── requirements.txt
└── docs/
    └── NOTES.md          ← Architecture decisions
```

---

## Installation

```bash
cd 02-keylogger/src
pip install -r requirements.txt
```

**macOS:** You must grant Terminal (or your IDE) **Accessibility** permission under
`System Preferences → Privacy & Security → Accessibility`.

---

## Usage

### Logger

```bash
# Basic — logs to keylog.txt, flushes every 10 s
python keylogger.py

# Custom path and flush interval
python keylogger.py --log /tmp/session.log --interval 5

# Disable per-key timestamps (smaller file)
python keylogger.py --no-timestamps

# Rotate after 1 MB
python keylogger.py --max-size 1024
```

Stop the logger with **Ctrl+C**.

**Example log output:**
```
============================================================
Session started: 2026-04-28T14:32:10
============================================================
[14:32:11.042]H[14:32:11.098]e[14:32:11.154]l[14:32:11.198]l[14:32:11.242]o
[ENTER]
[14:32:13.001]p[14:32:13.055]a[14:32:13.108]s[14:32:13.155]s[BKSP][BKSP]...
```

### Parser

```bash
# Analyse a log file
python parser.py keylog.txt

# Show top 30 words, ignore words shorter than 4 chars
python parser.py keylog.txt --top 30 --min-word 4
```

**Example output:**
```
============================================================
KEYSTROKE LOG ANALYSIS REPORT
============================================================
Sessions found : 2
Total keystrokes : 1 842
Backspaces       : 47  (2.6% of all keys)

Session 1  |  started: 2026-04-28T14:32:10
  Keystrokes  : 920
  Unique words: 88

  Top-5 words:
      12  the
       8  password
       7  login
```

---

## How It Works

### pynput Listener
`pynput.keyboard.Listener` registers a low-level hook with the OS:
- **Windows** — `SetWindowsHookEx(WH_KEYBOARD_LL)` in a background thread
- **Linux** — Xlib `XRecord` extension or evdev
- **macOS** — `CGEventTap` via the Quartz framework

Every key-down event fires `on_press(key)`. The callback converts the key to a
string token and appends it to an in-memory buffer.

### Thread-safe buffer
```
Listener thread  →  append to buf (Lock)  →  Flush thread (every N sec)  →  file
```
The flush thread wakes on a timer, drains the buffer under the lock, and writes
the chunk to disk. This minimises I/O calls and avoids losing keystrokes if the
process is killed between flushes.

### Log rotation
Once the log exceeds `--max-size` KB it is renamed to `keylog.txt.YYYYMMDD_HHMMSS`
and a new session header is written to a fresh file.

---

---

## Defensive Detection

| Detection Method | What to Look For |
|-----------------|-----------------|
| Process list | Unexpected Python processes or packed executables |
| Startup entries | Registry `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| File system | Unusual `.txt`/`.enc` files in temp or AppData directories |
| Keyboard hook audit | `GetRegisteredRawInputDevices`, Sysinternals Process Monitor |

---

## Challenges & Extensions

- Add **email exfiltration** — send log chunks via SMTP on flush (lab only)
- Add **clipboard capture** using `pyperclip` or Win32 clipboard API
- Add **screenshot trigger** — capture screen when specific hot-keys are pressed
- Implement **log encryption** (Fernet / AES) so raw text is never written to disk
- Write a **detector** that enumerates all registered low-level keyboard hooks
- Package as `.exe` with PyInstaller, submit to VirusTotal, study the detections

---

## References

- [pynput documentation](https://pynput.readthedocs.io/)
- [Windows Hook Chains — MSDN](https://docs.microsoft.com/en-us/windows/win32/winmsg/hooks)
- [macOS CGEventTap — Apple Developer](https://developer.apple.com/documentation/coregraphics/1454426-cgeventtapcreate)
- MITRE ATT&CK: [T1056.001 — Keylogging](https://attack.mitre.org/techniques/T1056/001/)

---

## Ethical Use

This tool is for **educational and authorized forensic use only**. Only run it on
machines you own or have explicit written permission to monitor. Recording keystrokes
without consent is illegal under the CFAA, GDPR, and equivalent laws worldwide.

---

