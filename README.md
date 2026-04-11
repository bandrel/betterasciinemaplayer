# Bettercast

A modern asciinema player for the terminal with full media-player controls.

Bettercast replays `.cast` recordings (v2 and v3) with seeking, variable playback speed, text search, bookmarks, and a visual progress bar — features missing from `asciinema play`.

## Installation

```bash
uv tool install .
```

Or run directly:

```bash
uv run bettercast recording.cast
```

## Usage

```bash
bettercast <file.cast> [--speed 1.0] [--idle-threshold 2.0] [--no-idle-compress]
```

| Flag | Description |
|------|-------------|
| `--speed` | Initial playback speed (default: 1.0) |
| `--idle-threshold` | Skip idle gaps longer than this many seconds (default: 2.0) |
| `--no-idle-compress` | Disable idle time compression |

## Keyboard Shortcuts

### Playback

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Left` / `Right` | Seek backward / forward 5 seconds |
| `Shift+Left` / `Shift+Right` | Seek backward / forward 30 seconds |
| `Home` / `End` | Jump to start / end |
| `.` / `,` | Step forward / backward one frame |
| `[` / `]` | Decrease / increase speed by 0.5x |
| `l` | Toggle loop mode |

### Navigation

| Key | Action |
|-----|--------|
| `/` | Open search |
| `n` / `N` | Next / previous search match |
| `g` | Go to timestamp (enter MM:SS or H:MM:SS) |
| `Escape` | Dismiss search or timestamp overlay |

### Bookmarks

| Key | Action |
|-----|--------|
| `m` | Bookmark current position |
| `b` | Open bookmark list |
| `{` / `}` | Jump to previous / next bookmark |

In the bookmark list:

| Key | Action |
|-----|--------|
| `Up` / `Down` | Navigate bookmarks |
| `Enter` | Jump to selected bookmark |
| `d` | Delete selected bookmark |
| `Escape` | Close bookmark list |

### Other

| Key | Action |
|-----|--------|
| `c` | Copy visible screen text to clipboard |
| `?` | Toggle full help overlay |
| `q` | Quit |

## Supported Formats

- **Asciicast v2** — absolute timestamps, `width`/`height` header
- **Asciicast v3** — relative (delta) timestamps, `term.cols`/`term.rows` header

Format is auto-detected from the header.
