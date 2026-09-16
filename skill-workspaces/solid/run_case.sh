#!/usr/bin/env bash
# Run one solid-skill test case against a given skill version.
# usage: run_case.sh <eval-dir-name> <config:with_skill|old_skill> <prompt-file> <fixture-files...>
set -uo pipefail

W=/home/dheeto/skills/skill-workspaces/solid/iteration-1
NEW=/home/dheeto/skills/skills/solid
OLD=/home/dheeto/skills/skill-workspaces/solid-snapshot-old

name=$1; config=$2; prompt_file=$3; shift 3
skill=$([ "$config" = "with_skill" ] && echo "$NEW" || echo "$OLD")
run=$W/$name/$config

rm -rf "$run"; mkdir -p "$run/work"
for f in "$@"; do cp "$W/$name/$(basename "$f")" "$run/work/"; done

{
  echo "You have a skill to use. Read ${skill}/SKILL.md first, and read any file under ${skill}/references/ that it tells you to read. Then do the task following it."
  echo
  echo "Work in the directory ${run}/work — create/edit files there only."
  echo "When finished, write your complete final answer to the user as ${run}/response.md"
  echo
  echo "TASK:"
  cat "$prompt_file"
} > "$run/prompt.txt"

cd "$run/work"
start=$(date +%s)
timeout 1200 pi -p --no-session --thinking high  "$(cat "$run/prompt.txt")" > "$run/transcript.txt" 2>&1
rc=$?
end=$(date +%s)
printf '{"exit":%s,"duration_seconds":%s}\n' "$rc" $((end-start)) > "$run/timing.json"
echo "DONE $name $config rc=$rc $((end-start))s"
