---
name: chrome-extension-capture
description: Capture animated GIF demos of Chrome extensions (side panels, popups, WebSocket-driven UIs) using headful Chromium and agent-browser. Use when the user asks to create a demo GIF, record a Chrome extension in action, capture a side panel workflow, make an animated screenshot of an extension UI, document extension features visually, or troubleshoot ERR_BLOCKED_BY_CLIENT when trying to screenshot extension pages.
---

# Capturing Chrome Extensions in Action

Capture animated demos (GIFs) of Chrome extension UIs — side panels,
popups, and real-time streaming workflows — using headful Chromium and
agent-browser.

## Prerequisites

- `chromium` (or `google-chrome`) — headful browser with CDP support
- `agent-browser` — browser automation CLI (`npm i -g agent-browser && agent-browser install`)
- `ffmpeg` — for converting frame sequences to GIFs
- `curl`, `python3` — for CDP introspection and extension ID discovery

## Why not just open the built HTML directly?

Chrome extensions use `chrome.*` APIs (storage, runtime messages,
WebSocket connections through the extension's CSP) that aren't available
outside the extension context. Loading the built HTML directly in a
browser gives you a blank or broken page. You need a real Chromium
instance with the extension **loaded**.

## Launching Chromium with the extension

```bash
# Build the extension first
cd packages/extension && pnpm build

EXT_PATH="$(pwd)/dist"
PROFILE="/tmp/chrome-ext-profile"

rm -rf "$PROFILE"
mkdir -p "$PROFILE"

chromium \
  --remote-debugging-port=9222 \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$PROFILE" \
  --load-extension="$EXT_PATH" \
  --test-type \
  --allow-running-insecure-content \
  --ignore-certificate-errors \
  --window-size=420,750 \
  "about:blank" &
```

### Critical Chromium flags

| Flag | Why |
|---|---|
| `--remote-debugging-port=9222` | Enables CDP so agent-browser can connect |
| `--load-extension=<path>` | Pre-loads the unpacked extension |
| `--test-type` | Suppresses warning banners; relaxes some security checks |
| `--allow-running-insecure-content` | Allows WebSocket connections from extension pages |
| `--ignore-certificate-errors` | Prevents certificate blocks on self-signed connections |
| `--user-data-dir=/tmp/...` | Isolated profile; required for unpacked extensions |
| `--no-first-run` | Skips onboarding dialogs |
| `--window-size=W,H` | Sets viewport (side panel is narrow — 420×750 is a good default) |

### What NOT to use

**`--disable-web-security`** works but produces a persistent warning banner
in every screenshot. Use `--test-type` + `--allow-running-insecure-content`
instead — same result, no banner.

Without `--allow-running-insecure-content`, Chromium may block the
extension page with `ERR_BLOCKED_BY_CLIENT` when the service worker opens
a WebSocket. The block is often **delayed** — the page loads fine
initially, then gets blocked 5-10 seconds later.

## Discovering the extension ID

```bash
# Wait for the CDP port
until curl -s http://127.0.0.1:9222/json/version > /dev/null; do sleep 1; done

# Extract the extension ID
EXT_ID=$(curl -s http://127.0.0.1:9222/json/list | python3 -c "
import sys, json
for d in json.load(sys.stdin):
    if 'service_worker' in d.get('type','') and 'chrome-extension://' in d.get('url',''):
        print(d['url'].split('/')[2])
        break
")
echo "Extension ID: $EXT_ID"
```

Connect agent-browser and open the extension page:

```bash
agent-browser connect 9222
agent-browser open "chrome-extension://${EXT_ID}/index.html"
sleep 3
```

## Capturing workflows as GIFs

**Do not use `agent-browser record` on extension pages** — the recording
attachment can trigger `ERR_BLOCKED_BY_CLIENT`. Use sequential screenshots
instead.

### Basic frame capture pattern

```bash
mkdir -p frames

# Frame 0: initial state
agent-browser screenshot frames/frame-00.png

# Interact — always re-snapshot before using @eN refs
agent-browser snapshot -i
agent-browser fill @e8 "https://example.com/article"
agent-browser screenshot frames/frame-01.png

agent-browser snapshot -i
agent-browser click @e9
sleep 1
agent-browser screenshot frames/frame-02.png
```

### Capturing streaming progress

```bash
for i in $(seq 3 30); do
  sleep 2
  padded=$(printf "%02d" $i)
  agent-browser screenshot "frames/frame-${padded}.png"

  # Check if still processing
  status=$(agent-browser eval --stdin <<'EOF'
  document.body.innerText.includes("Compiling") ? "busy" : "idle"
EOF
  )
  if [ "$status" = '"idle"' ]; then
    agent-browser screenshot frames/frame-final.png
    break
  fi
done
```

### Converting frames to GIF

```bash
ffmpeg -y \
  -framerate 3 \
  -pattern_type glob -i "frames/frame-*.png" \
  -vf "fps=6,scale=420:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse" \
  output.gif
```

| Option | Purpose |
|---|---|
| `-framerate 3` | Input frame rate from source images |
| `fps=6` | Output frame rate — smooth enough, keeps size down |
| `scale=420:-1:flags=lanczos` | Resize to 420px wide, maintain aspect ratio |
| `palettegen=max_colors=128` | Optimized 128-color palette |
| `paletteuse` | Apply palette — critical for small file sizes |

For ~10-second workflows at 2s intervals (5-6 frames), this produces GIFs
around 50-80 KB. For longer sequences (30+ frames), reduce fps to 4-5 or
sample fewer frames.

## Finding elements and interacting

Always follow this pattern — refs (`@e1`, `@e2`, ...) become stale the
moment the page changes:

```bash
agent-browser snapshot -i    # get fresh refs
agent-browser click @eN      # act on a ref
# ... page changes ...
agent-browser snapshot -i    # ALWAYS re-snapshot before next interaction
```

Semantic locators are more resilient when refs are unreliable:

```bash
agent-browser find placeholder "https://example.com/article" fill "https://..."
agent-browser find text "Fetch & Add" click
agent-browser find text "Consult" click
```

## Checking page state from bash

```bash
agent-browser eval --stdin <<'EOF'
var t = document.body.innerText;
t.includes("Compiling") ? "busy" : "idle"
EOF
```

The return value is printed as JSON — strings come back quoted (`"busy"`),
so compare with `'"busy"'` in bash conditions.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Page blank / no interactive elements | Extension crashed or JS errors | Check console: `agent-browser eval --stdin <<<'console.log(document.body.innerHTML)'` |
| `ERR_BLOCKED_BY_CLIENT` | Missing security flags | Add `--test-type --allow-running-insecure-content` |
| Blocked after recording starts | `agent-browser record` triggers CDP check | Use sequential screenshots instead of `record` |
| `element not found` | Stale refs after page change | Always `snapshot -i` before using `@eN` refs |
| Extension not in `/json/list` | Extension failed to load | Check `manifest.json`; inspect chromium stderr |
| WebSocket connection fails | Bridge not running or blocked by CSP | Ensure bridge is on `127.0.0.1:9876`; verify flags |
| GIF too large | Too many frames or high resolution | Reduce fps, sample every Nth frame, lower palette colors |
