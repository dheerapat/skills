#!/usr/bin/env python3
"""Move run_case.sh output into the layout aggregate_benchmark.py + generate_review.py expect:
   eval-X/<config>/run-1/{outputs/,grading.json,timing.json}
"""
import json
import shutil
import sys
from pathlib import Path

W = Path("/home/dheeto/skills/skill-workspaces/solid/iteration-1")
SKIP = {"prompt.txt", "timing.json", "__pycache__", ".git"}


def normalize(eval_dir: Path, config: str) -> None:
    src = eval_dir / config
    if not src.is_dir() or (src / "run-1").exists():
        return
    run = src / "run-1"
    out = run / "outputs"
    out.mkdir(parents=True)
    # work/ = files the agent created; response.md + transcript.txt = what it said
    for f in sorted((src / "work").iterdir()):
        if f.name not in SKIP:
            shutil.copy2(f, out / f.name) if f.is_file() else None
    for name in ("response.md", "transcript.txt", "prompt.txt"):
        if (src / name).exists():
            shutil.copy2(src / name, out / name)
    shutil.copy2(src / "timing.json", run / "timing.json")
    t = json.loads((src / "timing.json").read_text())
    t["total_duration_seconds"] = t["duration_seconds"]
    (run / "timing.json").write_text(json.dumps(t, indent=2))
    print(f"{eval_dir.name}/{config}: {len(list(out.iterdir()))} output files")


for name in sys.argv[1:]:
    normalize(W / name, "with_skill")
    normalize(W / name, "old_skill")
