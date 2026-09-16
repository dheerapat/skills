#!/usr/bin/env python3
"""Programmatic checks for the solid-skill evals. Prints JSON per run so the
judgment-based expectations can be merged in by hand."""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

W = Path("/home/dheeto/skills/skill-workspaces/solid/iteration-1")
STDLIB_AND_KNOWN = {
    "smtplib", "csv", "io", "psycopg2", "json", "os", "sys", "argparse", "logging",
    "contextlib", "datetime", "typing", "collections", "unittest", "abc", "functools",
    "dataclasses", "importlib", "types", "re", "tempfile", "decimal", "time", "zoneinfo",
}


def py_files(d: Path):
    return sorted(p for p in d.rglob("*.py") if "__pycache__" not in str(p))


def text_of(d: Path) -> str:
    parts = [p.read_text(errors="replace") for p in py_files(d)]
    for n in ("response.md",):
        if (d / n).exists():
            parts.append((d / n).read_text(errors="replace"))
    return "\n".join(parts)


def code_only(d: Path) -> str:
    return "\n".join(p.read_text(errors="replace") for p in py_files(d))


def imports_of(d: Path):
    local = {p.stem for p in d.rglob("*.py")}
    found = set()
    for p in py_files(d):
        try:
            tree = ast.parse(p.read_text(errors="replace"))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                found.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                found.add(n.module.split(".")[0])
    return {m for m in found if m not in local}


def compile_ok(d: Path):
    ok, errs = True, []
    for p in py_files(d):
        r = subprocess.run([sys.executable, "-m", "py_compile", str(p)],
                           capture_output=True, text=True)
        if r.returncode:
            ok = False
            errs.append(f"{p.name}: {r.stderr.strip()[:120]}")
    return ok, errs


def abstraction_count(d: Path) -> int:
    t = code_only(d)
    n = len(re.findall(r"\(\s*Protocol\s*\)|Protocol\]|:\s*Protocol\b", t))
    n += len(re.findall(r"\bABC\b", t)) + len(re.findall(r"@abstractmethod", t))
    n += len(re.findall(r"\binterface\s+\w+", t))
    return n


def checks_eval1(d: Path) -> dict:
    code = code_only(d)
    return {
        "no-string-dispatch-chain": not re.search(r"(elif|if)\s+fmt\s*==", code),
        "no-new-third-party-deps": sorted(imports_of(d) - STDLIB_AND_KNOWN),
        "files-compile": compile_ok(d),
        "abstractions-added": abstraction_count(d),
        "new-files": [p.name for p in py_files(d)],
    }


def checks_eval2(d: Path) -> dict:
    dg = d / "daily_digest.py"
    code = dg.read_text(errors="replace") if dg.exists() else ""
    return {
        "file-actually-written": dg.exists(),
        "reuses-existing-notifier": bool(re.search(r"^\s*(import notify|from notify import)", code, re.M)) and "smtplib" not in code,
        "dsn-from-environment": 'os.environ["PG_DSN"]' in code or "os.environ.get(\"PG_DSN\")" in code or "environ['PG_DSN']" in code,
        "cron-entry-point": "__main__" in code,
        "abstractions-added": abstraction_count(d),
        "sql-interpolates-external-values": bool(re.search(r'execute\(\s*f["\']', code)),
        "no-interactive-input": "input(" not in code,
        "files-compile": compile_ok(d),
        "new-files": [p.name for p in py_files(d)],
    }


def checks_eval3(d: Path, fixture: Path) -> dict:
    got = d / "src.ts"
    resp = (d / "response.md")
    rtext = resp.read_text(errors="replace") if resp.exists() else ""
    same = got.exists() and got.read_bytes() == fixture.read_bytes()
    symbols = ["LegacyAdyenProvider", "verifyCard", "PaymentProvider", "TaxEngine",
               "StripeProvider", "Checkout", "logTaxEvent", "totalWithTax"]
    return {
        "file-unmodified": bool(same),
        "src.ts-present": got.exists(),
        "symbols-quoted": [s for s in symbols if s in rtext],
        "response-chars": len(rtext),
        "declared-refactors-in-src-ts": bool(re.search(r"^\+", rtext, re.M)) and same,
        "abstractions-mentioned": len(re.findall(r"\binterface\s+\w+", rtext)),
    }


def main():
    for name in sys.argv[1:]:
        d = W / name
        for cfg in ("with_skill", "old_skill"):
            run = d / cfg
            out = next((r for r in (run / "run-1" / "outputs", run / "outputs", run / "work") if r.is_dir()), None)
            if not out.is_dir():
                print(f"skip {name}/{cfg}")
                continue
            if "eval-1" in name:
                res = checks_eval1(out)
            elif "eval-2" in name:
                res = checks_eval2(out)
            else:
                res = checks_eval3(out, d / "src.ts" if (d / "src.ts").exists() else W / "eval-3-diagnose-ts/src.ts")
            print(f"### {name}/{cfg}")
            print(json.dumps(res, indent=2, default=str))


main()
