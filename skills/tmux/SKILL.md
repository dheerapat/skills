---
name: tmux
description: Use this skill whenever you need to run long-running commands, background processes, or interactive shell sessions using tmux. Running commands that take time (builds, tests, servers, installs), running multiple parallel processes, executing commands that need a persistent shell, capturing terminal output after a delay, or any task where you need to start a process and check on it later. Use this skill whenever tmux is mentioned, or when you need to send commands to a shell session and retrieve their output. Always clean up sessions when done.
---

# tmux Skill

A structured workflow for creating tmux sessions, executing commands, capturing output, and cleaning up — designed for agents running tasks that need persistent or background shells.

---

## Core Workflow

### 1. Create a Session

Always create a **named session** so you can reference it reliably later.

```bash
tmux new-session -d -s <session-name>
```

- `-d` starts it detached (in the background)
- `-s <session-name>` assigns a name (use short, descriptive names like `build`, `server`, `task-1`)
- Default window/pane is `<session-name>:0.0`

**Check if a session already exists before creating:**

```bash
tmux has-session -t <session-name> 2>/dev/null && echo "exists" || echo "new"
```

---

### 2. Send Keys (Run Commands)

Use `send-keys` to type a command into a session pane, followed by `Enter`:

```bash
tmux send-keys -t <session-name> "<command>" Enter
```

**Examples:**

```bash
# Run a build
tmux send-keys -t build "npm run build" Enter

# Start a server
tmux send-keys -t server "python -m http.server 8080" Enter

# Chain commands
tmux send-keys -t task-1 "cd /tmp && ls -la" Enter
```

**Tips:**
- Always include `Enter` at the end to execute the command
- For commands with special characters (quotes, brackets), wrap in single quotes or escape carefully
- To send a literal `Enter` without a command (e.g., confirm a prompt): `tmux send-keys -t <session-name> "" Enter`
- To send `Ctrl+C` to stop a process: `tmux send-keys -t <session-name> "" ""`  
  → Use: `tmux send-keys -t <session-name> C-c`

---

### 3. Capture Output

Use `capture-pane` to retrieve visible terminal content from the pane:

```bash
tmux capture-pane -t <session-name> -p
```

- `-p` prints output to stdout (instead of a paste buffer)
- Returns the current visible contents of the pane

**Capture including scrollback history:**

```bash
tmux capture-pane -t <session-name> -p -S -3000
```

- `-S -3000` goes back up to 3000 lines of history (adjust as needed)

**Save output to a file:**

```bash
tmux capture-pane -t <session-name> -p -S -3000 > /tmp/<session-name>-output.txt
```

---

### 4. Wait for Commands to Finish

For commands that take time, poll until they complete:

```bash
# Simple sleep-and-check loop
for i in $(seq 1 30); do
  sleep 2
  output=$(tmux capture-pane -t <session-name> -p -S -500)
  echo "$output" | grep -q "<done-marker>" && break
done
```

Replace `<done-marker>` with a string that appears when the command finishes (e.g., `"Build complete"`, `"$ "` for a shell prompt, `"error"`, `"success"`).

**Better pattern — redirect output to a file and tail it:**

```bash
# Send command with output redirected
tmux send-keys -t <session-name> "<command> > /tmp/out.txt 2>&1; echo DONE >> /tmp/out.txt" Enter

# Poll the file
for i in $(seq 1 60); do
  sleep 1
  grep -q "DONE" /tmp/out.txt 2>/dev/null && break
done

cat /tmp/out.txt
```

---

### 5. Kill (Remove) the Session

Always clean up when the job is done:

```bash
tmux kill-session -t <session-name>
```

**Kill all tmux sessions (use with care):**

```bash
tmux kill-server
```

---

## Full Example: Run a Script and Capture Output

```bash
# 1. Create session
tmux new-session -d -s myjob

# 2. Run command, redirect output
tmux send-keys -t myjob "bash /tmp/myscript.sh > /tmp/myjob-out.txt 2>&1; echo __DONE__ >> /tmp/myjob-out.txt" Enter

# 3. Wait for completion (up to 60s)
for i in $(seq 1 60); do
  sleep 1
  grep -q "__DONE__" /tmp/myjob-out.txt 2>/dev/null && break
done

# 4. Capture and display output
cat /tmp/myjob-out.txt

# 5. Kill session
tmux kill-session -t myjob
```

---

## Parallel Jobs Pattern

To run multiple tasks in parallel, create one session per task:

```bash
tmux new-session -d -s job1
tmux new-session -d -s job2

tmux send-keys -t job1 "task1.sh > /tmp/job1.txt 2>&1; echo DONE >> /tmp/job1.txt" Enter
tmux send-keys -t job2 "task2.sh > /tmp/job2.txt 2>&1; echo DONE >> /tmp/job2.txt" Enter

# Wait for both
for i in $(seq 1 60); do
  sleep 1
  j1=$(grep -c "DONE" /tmp/job1.txt 2>/dev/null || echo 0)
  j2=$(grep -c "DONE" /tmp/job2.txt 2>/dev/null || echo 0)
  [ "$j1" -ge 1 ] && [ "$j2" -ge 1 ] && break
done

cat /tmp/job1.txt
cat /tmp/job2.txt

tmux kill-session -t job1
tmux kill-session -t job2
```

---

## Useful Diagnostic Commands

```bash
# List all active sessions
tmux ls

# Show what's currently visible in a pane
tmux capture-pane -t <session-name> -p

# Check if session exists
tmux has-session -t <session-name> 2>/dev/null && echo "exists"

# List windows in a session
tmux list-windows -t <session-name>
```

---

## Common Pitfalls

| Problem | Fix |
|---|---|
| Command not running | Check you included `Enter` in `send-keys` |
| Output is empty | Add a short `sleep 1` before `capture-pane`; the command may not have started yet |
| Session name conflict | Use `tmux has-session` to check first, or use unique names |
| Special chars in command | Wrap the command string in single quotes, or escape `$`, `"`, `` ` `` |
| Process still running after kill | Use `tmux kill-session` (not just closing the pane) |

---

## Cleanup Reminder

**Always kill sessions after use.** Lingering sessions consume resources and may cause name conflicts on future runs.

```bash
tmux kill-session -t <session-name>
```

If you created multiple sessions, kill each one explicitly, or use `tmux kill-server` to wipe all sessions if you're certain no other sessions are needed.
