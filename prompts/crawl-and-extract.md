---
description: Crawl a website and create knowledge base. Requires `agent-browser` CLI, `tmux`, and `writing-knowledge-base` skills.
argument-hint: "[target website URL and what topic/info to extract]"
---

**Instruction**

$@

**Workflow**

1. **Discover links.** Fetch the page and extract URLs. Prefer `agent-browser read` (fast, works on most sites):

   ```bash
   agent-browser read <BASE_URL> | grep -oP 'https?://[^\)\s<>"'']+' | sort -u > links.txt
   ```

   For sites that return markdown, also capture relative links:

   ```bash
   agent-browser read <BASE_URL> | grep -oP '\[.*?\]\((/[^)]+)\)' | sed 's/.*](//;s/)$//' | sed 's|^/|https://<DOMAIN>/|' | sort -u >> links.txt
   ```

   If `agent-browser read` gets no content (JS-only sites), fall back to the browser. **Run each command separately** — avoid `&&` chaining with `snapshot`, as the browser session can lose state:

   ```bash
   agent-browser open <BASE_URL>
   agent-browser wait --load networkidle
   agent-browser snapshot -u | grep -oP 'url=\S+' | sed 's/url=//' | sort -u > links.txt
   agent-browser close
   ```

1. **Filter.** Prune `links.txt` — remove external domains, duplicates, and pages irrelevant to the user's topic. Keep only URLs whose content would answer the request.

1. **Scrape + build in parallel.** For each remaining URL, dedicate one tmux session. Each session fetches its URL with `agent-browser read` then feeds the content into `/writing-knowledge-base`:

   ```bash
   # For each URL in links.txt:
   SLUG="kb-$(echo '$URL' | sed 's|[^a-zA-Z0-9]|-|g' | tr -s '-' | sed 's|^-\|-$||g')"

   tmux new-session -d -s "$SLUG"
   tmux send-keys -t "$SLUG" \
     "agent-browser read '$URL' | pi 'Use /writing-knowledge-base to create a knowledge base from this content. Save under ./kb/$SLUG/'" \
     C-m
   ```

   The ping-pong: `agent-browser read` fetches agent-readable text/markdown → `pi` reads it via stdin and runs `/writing-knowledge-base` on it.

   **Exit tracking** — append an exit marker so you can poll for completion:

   ```bash
   tmux send-keys -t "$SLUG" '; printf "\n__DONE__%s\n" "$?" >> /tmp/kb-job-status.txt' C-m
   ```

1. **Wait.** Poll until every session has written its exit marker:

   ```bash
   TOTAL=$(wc -l < links.txt)
   for i in $(seq 1 120); do
     sleep 2
     DONE=$(grep -c '__DONE__' /tmp/kb-job-status.txt 2>/dev/null || echo 0)
     [ "$DONE" -ge "$TOTAL" ] && break
   done
   ```

1. **Collect.** Each session's `/writing-knowledge-base` output lands in `./kb/<slug>/` — one self-contained knowledge base directory per scraped URL. Verify they exist:

   ```bash
   ls ./kb/
   ```

1. **Clean up.** Kill all tmux sessions:

   ```bash
   for slug in $(cat slugs.txt); do tmux kill-session -t "$slug" 2>/dev/null; done
   rm -f /tmp/kb-job-status.txt slugs.txt
   ```

**Notes**

- Each tmux session is fully independent — one URL scrape → one knowledge base. No shared state.

- Use URL-derived slugs for session names and output directories so results trace back to their source.

- If a session fails (no `__DONE__` marker or non-zero exit), re-run that single URL individually.

- `agent-browser read <URL>` negotiates `Accept: text/markdown` and falls back to readable HTML extraction — ideal input for `/writing-knowledge-base`.

- For JS-heavy sites where `agent-browser read` misses content, open the page in a browser first, then use `agent-browser read` (no URL) to capture the rendered DOM. Give each tmux session its own browser with `--session "$SLUG"`.

- For stubborn JS sites where even the rendered-DOM read fails, fall back to extracting HTML then converting:

  ```bash
  agent-browser open '$URL' && sleep 5 && agent-browser get html "body" | pandoc -f html -t markdown --wrap=none | pi 'Use /writing-knowledge-base ...'
  ```

  This requires `pandoc` installed. The `sleep 5` gives JS-rendered content time to settle.

- **Mixed JS/static pattern**: Some sites render navigation/index links via JS but serve article pages as static HTML. Two-phase approach: use `snapshot` on the index page (link discovery), then `agent-browser read <URL>` on each article (content extraction).
