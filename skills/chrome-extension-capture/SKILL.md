---
name: chrome-extension-capture
description: Capture animated GIF demos of browser UIs using headful Chromium and agent-browser. Use when the user asks to create a demo GIF, record a browser workflow, capture an animated screenshot, document web UI features visually, make a walkthrough of a web app, or record any interactive browser session. Also use for Chrome extensions, side panels, popups, or WebSocket-driven UIs. Trigger whenever the user wants to visually demonstrate or document something that happens in a browser.
---

# Capturing Browser UIs as Animated GIFs

Capture animated demos (GIFs) of any browser UI — web apps, Chrome extensions, side panels, popups, multi-step workflows — using headful Chromium and agent-browser.

## Prerequisites

- `chromium` (or `google-chrome`) — headful browser with CDP support
- `agent-browser` — browser automation CLI (`npm i -g agent-browser && agent-browser install`)
- `ffmpeg` — for converting frame sequences to GIFs

## Launching Chromium

```bash
PROFILE="/tmp/chrome-profile"
rm -rf "$PROFILE" && mkdir -p "$PROFILE"

chromium \
  --remote-debugging-port=9222 \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$PROFILE" \
  --window-size=1280,800 \
  "about:blank" &

# Wait for CDP to be ready
until curl -s http://127.0.0.1:9222/json/version > /dev/null; do sleep 1; done
```

**Loading a Chrome extension** (only needed for extension capture):
```bash
chromium ... --load-extension="/path/to/dist" --test-type --allow-running-insecure-content ...
```

### Useful Chromium flags

| Flag | When to use |
|---|---|
| `--remote-debugging-port=9222` | Always — enables CDP |
| `--window-size=W,H` | Set viewport; default 1280×800 for web apps, 420×750 for narrow UIs |
| `--no-first-run` | Skips onboarding dialogs |
| `--load-extension=<path>` | Chrome extensions only |
| `--test-type` | Extensions: suppresses warning banners |
| `--allow-running-insecure-content` | Extensions: allows WebSocket from extension pages |
| `--ignore-certificate-errors` | Self-signed cert environments |

## Connecting and navigating

```bash
agent-browser connect 9222
agent-browser open "https://example.com"
sleep 2  # let the page settle
```

For Chrome extensions, discover the extension ID first:
```bash
EXT_ID=$(curl -s http://127.0.0.1:9222/json/list | python3 -c "
import sys, json
for d in json.load(sys.stdin):
    if 'service_worker' in d.get('type','') and 'chrome-extension://' in d.get('url',''):
        print(d['url'].split('/')[2]); break
")
agent-browser open "chrome-extension://${EXT_ID}/index.html"
```

## Capturing frames

Use sequential screenshots — **not** `agent-browser record` (can trigger blocking issues on some pages).

```bash
mkdir -p frames

# Capture initial state
agent-browser screenshot frames/frame-00.png

# Interact, then capture
agent-browser snapshot -i          # get fresh element refs
agent-browser click @e5            # interact
sleep 1
agent-browser screenshot frames/frame-01.png
```

**Always re-snapshot before using `@eN` refs** — they go stale after page changes. For resilience, use semantic locators:

```bash
agent-browser find text "Submit" click
agent-browser find placeholder "Search..." fill "my query"
```

### Capturing a multi-step workflow

```bash
steps=(
  "https://example.com"
  "https://example.com/step2"
  "https://example.com/step3"
)

for i in "${!steps[@]}"; do
  agent-browser open "${steps[$i]}"
  sleep 1
  agent-browser screenshot "frames/frame-$(printf '%02d' $i).png"
done
```

### Capturing streaming or async progress

```bash
for i in $(seq 3 30); do
  sleep 2
  agent-browser screenshot "frames/frame-$(printf '%02d' $i).png"

  done=$(agent-browser eval --stdin <<'EOF'
document.body.innerText.includes("Complete") ? "yes" : "no"
EOF
  )
  [ "$done" = '"yes"' ] && break
done
```

## Converting frames to GIF

```bash
ffmpeg -y \
  -framerate 3 \
  -pattern_type glob -i "frames/frame-*.png" \
  -vf "fps=6,scale=1280:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse" \
  output.gif
```

| Option | Purpose |
|---|---|
| `-framerate 3` | Input frame rate (how fast to read source images) |
| `fps=6` | Output frame rate — smooth enough, keeps file small |
| `scale=W:-1` | Resize width, maintain aspect ratio |
| `palettegen=max_colors=128` | Optimized palette for smaller file size |
| `paletteuse` | Apply palette — critical for quality |

**File size tips:** ~5-6 frames at 2s intervals → 50-80 KB. For 30+ frames, reduce fps to 4 or sample every Nth frame.

## Checking page state

```bash
agent-browser eval --stdin <<'EOF'
document.title
EOF
# Returns JSON-quoted string, e.g. "\"My Page Title\""
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Page blank or broken | JS error / wrong URL | Check `agent-browser eval --stdin <<<'document.body.innerHTML'` |
| `element not found` | Stale refs | Re-run `agent-browser snapshot -i` before interacting |
| `ERR_BLOCKED_BY_CLIENT` | Security flag missing (extensions) | Add `--test-type --allow-running-insecure-content` |
| GIF too large | Too many frames | Reduce fps, sample every Nth frame, or lower `max_colors` |
| Extension not found | Failed to load | Check `manifest.json`; look at chromium stderr |
