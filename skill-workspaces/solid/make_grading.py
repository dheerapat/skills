#!/usr/bin/env python3
"""Assemble grading.json for each iteration-1 run. Programmatic checks come from
grade.py; the judgment calls were made by reading every output (evidence quoted)."""
import json
import re
from pathlib import Path

import grade as G

W = Path("/home/dheeto/skills/skill-workspaces/solid/iteration-1")

J = {
 ("eval-1-refactor-python", "with_skill"): {
   "behavior-preserved": (False, "Print line, return value and ValueError('unsupported format') preserved, but the public entry point changed: `InvoiceSyncManager().run(fmt, dry_run)` -> module funcs `run_invoice_sync(fmt, dry_run, dsn)` / `sync_invoices(repo, notify, ...)`. Disclosed in the response ('InvoiceSyncManager is gone ... grep is clean'), so callers break knowingly rather than silently - but they break."),
   "sql-and-smtp-decoupled": (True, "invoice_repository.py holds all SQL, invoice_mail.py all SMTP, neither imports the other; sync_invoices() reaches both through parameters."),
   "no-string-dispatch-chain": (True, "regex `(elif|if)\\s+fmt\\s*==` finds no match; FORMATTERS dict + render() instead."),
   "diagnosis-names-principles": (True, "'## Diagnosis' maps S (four reasons to change), O (string-keyed chain), D (psycopg2/smtplib built inline) and states 'L / I - no matches. No subtypes, no interfaces. Nothing done for them.'"),
   "every-abstraction-justified": (True, "Zero Protocol/ABC added. Seam is `Notifier = Callable[[str], None]` (rung 1); the two classes are concrete adapters, not interfaces."),
   "secrets-not-replicated": (False, "'hunter2' and 'apassword' still appear as literals (promoted to module constants in invoice_sync.py / invoice_mail.py). Same as the baseline run - see eval_feedback."),
   "no-new-third-party-deps": (True, "imports outside stdlib: psycopg2 (lazy, already present) only."),
   "declined-work-reported": (True, "'Deliberately not done - No Protocol/ABC/factory. Notifier and the repository each have one implementation plus a duck-typed test double; an interface would be a pass-through.'"),
 },
 ("eval-1-refactor-python", "old_skill"): {
   "behavior-preserved": (True, "Kept `InvoiceSyncManager(...).run(fmt, dry_run)` and ran a differential harness: old vs new side by side over 3 formats x dry_run on/off x 3 bad formats -> 'RESULT: ALL IDENTICAL (9/9 cases)' including order of side effects."),
   "sql-and-smtp-decoupled": (True, "PostgresInvoiceRepository = SQL only; SmtpInvoiceMailSender = delivery only; InvoiceSyncManager orchestrates through injected Protocols."),
   "no-string-dispatch-chain": (True, "if/elif chain replaced by ReporterRegistry.for_format()."),
   "diagnosis-names-principles": (True, "'Rule by rule' section walks S/O/L/I/D by name; closes 'All five rules violated.'"),
   "every-abstraction-justified": (False, "3 Protocols (InvoiceRepository, InvoiceReporter, InvoiceMailSender) each with exactly one implementation, plus `ReporterRegistry.register()` for three built-in formats and an injected `printer: Callable = print`. Justification offered is the principle name ('[I/D]'), never a second implementation or a named test double."),
   "secrets-not-replicated": (False, "Kept as literal constructor defaults, deliberately: 'No config/secret externalisation ... you said behaviour must not change' + flagged for a ticket. Graded fail per the wording; the wording is the problem."),
   "no-new-third-party-deps": (True, "stdlib + psycopg2 only."),
   "declined-work-reported": (True, "'Deliberately *not* done (scope discipline)' - though every item there is scope (secrets, CLI, logging); no abstraction was declined."),
 },
 ("eval-2-new-module-python", "with_skill"): {
   "reuses-existing-notifier": (True, "`import notify`, calls `notify.send(RECIPIENT, subject, body)`; 'notify.py untouched'; smtplib never appears."),
   "dsn-from-environment": (True, "`psycopg2.connect(os.environ[\"PG_DSN\"])` inside main()."),
   "no-speculative-abstraction": (True, "Zero Protocol/ABC/interface added: four module-level functions, `digest_for(conn, today)` taking the clock and the connection as arguments. Test doubles are plain classes in the test file."),
   "declined-seam-stated": (True, "'Not done: no Mailer/Database Protocol, no factory, no registry. notify.send is already the repo's single mail implementation with one caller - an interface for it would be indirection that answers nothing. Add it when a second sender ... actually lands.' Plus 'Seam: rung 1 - parameters ... Zero new types.'"),
   "cron-entry-point": (True, "`if __name__ == '__main__': main()`, documented crontab line, logging/traceback to stderr for cron MAILTO, no interactive input."),
   "parameterized-or-safe-sql": (True, "COUNT_SQL is a constant with `%s` bounds; cur.execute(COUNT_SQL, (day, day + timedelta(days=1)))."),
   "yesterday-computed-safely": (True, "`yesterday = today - timedelta(days=1)` with `today` injected by main(); half-open range comment explains index use and Postgres tz widening."),
   "file-actually-written": (True, "daily_digest.py (2193 B) plus test_daily_digest.py in the work dir."),
 },
 ("eval-2-new-module-python", "old_skill"): {
   "reuses-existing-notifier": (True, "`import notify  # existing, working module -- reused as-is`; the module itself satisfies its Mailer protocol."),
   "dsn-from-environment": (True, "connect_from_env() reads os.environ.get('PG_DSN') and raises if unset."),
   "no-speculative-abstraction": (False, "3 Protocols (Clock, SignupCounter, MessageSender) with one implementation each, plus SystemClock, PostgresSignupCounter, DailyDigest, build(). Reproduced across two independent samples (5 'Protocol' hits in each) - not a fluke."),
   "declined-seam-stated": (False, "Declines only a wrapper class and argparse flags; the abstractions are justified rather than declined: 'D - DailyDigest depends on Clock/SignupCounter/MessageSender Protocols ... That's what makes it testable with fakes.'"),
   "cron-entry-point": (True, "`if __name__ == '__main__': sys.exit(main())`, --date backfill flag, logging to stderr, non-zero exit on failure."),
   "parameterized-or-safe-sql": (True, "_COUNT_SQL constant with positional %s params; comment warns against `WHERE date(created_at) = %s`."),
   "yesterday-computed-safely": (True, "`day = self._clock.today() - YESTERDAY` behind an injectable Clock; half-open bounds."),
   "file-actually-written": (True, "daily_digest.py (4390 B) in the work dir."),
 },
 ("eval-3-diagnose-ts", "with_skill"): {
   "file-unmodified": (True, "outputs/src.ts byte-identical to the fixture."),
   "found-interface-segregation": (True, "'#1 I - PaymentProvider is sized to the vendor's capability list, not to any client (L3-10)'; evidence: Checkout touches 2 of 6, LegacyAdyen throws on 4 of 6, two consumers with disjoint needs."),
   "found-liskov-break": (True, "'#2 L - LegacyAdyenProvider breaks substitutability twice'; names the always-true verifyCard as the quiet, silent postcondition break and notes charge() runs after it so the policy fails open."),
   "found-dependency-inversion": (True, "'#3 D - Checkout constructs its own vendor client and reads env (L52-53)'; '#4 D - raw fetch hardcoded inside TaxEngine.logTaxEvent (L42-48)'."),
   "found-single-responsibility": (True, "'#5 S - TaxEngine is two jobs wearing one name' - tax law vs audit transport, disjoint callers, 'the and test'."),
   "open-closed-honest": (True, "'#6 O - the region if/else chain: real, but the weakest finding ... O requires evidence the set keeps growing - a branch per new variant in history - not a hunch ... do not build ITaxStrategy + per-region classes + a factory. That is the textbook over-application: four types replacing one number.' Prescribes a union type + Record, i.e. keeps it closed."),
   "recommends-against-something": (True, "Section '## Seams I'd deliberately decline (and why - reviewer needs this to check the decision)'; also 'Do not fix it by adding supportsRefund(): boolean flags' and 'no mocking library, no ITaxEngineStrategy'."),
   "grounded-in-symbols": (True, "All eight fixture symbols quoted (PaymentProvider, LegacyAdyenProvider, verifyCard, TaxEngine, StripeProvider, Checkout, logTaxEvent, totalWithTax) with line numbers."),
 },
 ("eval-3-diagnose-ts", "old_skill"): {
   "file-unmodified": (True, "outputs/src.ts byte-identical to the fixture."),
   "found-interface-segregation": (True, "'I1 - PaymentProvider is a 6-method god interface'; correctly diagnoses that the fatness is what creates L1/L2."),
   "found-liskov-break": (True, "'L2 - verifyCard returns hardcoded true ... Worse than L1 because it's silent'; L3 additionally finds the discarded result checked after the charge."),
   "found-dependency-inversion": (True, "'D1 - Checkout hardwires the concrete provider'; D2/D3 cover env reading and the raw fetch."),
   "found-single-responsibility": (True, "'S1 - TaxEngine has two reasons to change' (rules vs transport); S2 counts four for Checkout."),
   "open-closed-honest": (False, "O1 asserts the chain violates O and prescribes `interface TaxPolicy { rateFor(...) }` injected into the calculator, 'Adding per-item exemption handling = one new policy class', with no evidence the region set is open. O3 then reads the ignored `items` param as proof that 'the real design is a strategy list over items'. 7 `interface X` declarations proposed vs 3."),
   "recommends-against-something": (False, "The single YAGNI mention (O3) is about a parameter, and the fix order immediately adds the TaxPolicy interface anyway. Verdict is 'All five rules violated' with a 6-step plan including branded Money/Receipt types nobody asked about."),
   "grounded-in-symbols": (True, "Same eight fixture symbols quoted with src.ts:line references."),
 },
}

# assertions that exist in metadata but only for some evals
J[("eval-3-diagnose-ts", "with_skill")]["diagnosis-gives-fix-rungs"] = (
    True, "Summary table maps each finding to a fix rung (1 / 2 / 3->4) rather than to a new type.")
J[("eval-3-diagnose-ts", "old_skill")]["diagnosis-gives-fix-rungs"] = (
    True, "'Fix order' numbers the 13 findings with a ~half-day estimate, though every fix is a new type.")


def main():
    for name in sorted(p.name for p in W.glob("eval-*")):
        meta = json.loads((W / name / "eval_metadata.json").read_text())
        for cfg in ("with_skill", "old_skill"):
            d = W / name / cfg / "run-1"
            out = d / "outputs"
            tbl = J[(name, cfg)]
            rows = []
            for text in meta["assertions"]:
                key = text.split(":")[0].strip()
                if key not in tbl:
                    rows.append({"text": text, "passed": False,
                                 "evidence": "UNGRADED - no check written for this assertion"})
                    continue
                p, ev = tbl[key]
                rows.append({"text": text, "passed": p, "evidence": ev})
            passed = sum(1 for r in rows if r["passed"])
            total = len(rows)
            (d / "grading.json").write_text(json.dumps({
                "expectations": rows,
                "summary": {"passed": passed, "failed": total - passed, "total": total,
                            "pass_rate": round(passed / total, 3)},
                "execution_metrics": {
                    "output_chars": sum(len(p.read_text(errors="replace"))
                                        for p in out.rglob("*") if p.is_file()),
                    "files_created": sorted(p.name for p in out.iterdir() if p.is_file()),
                    "errors_encountered": 0},
                "timing": {"total_duration_seconds":
                           json.loads((d / "timing.json").read_text())["duration_seconds"]},
                "eval_feedback": {"suggestions": [
                    {"assertion": "secrets-not-replicated",
                     "reason": "Fails for both configs and conflicts with the prompt's own 'behaviour must stay identical' constraint - it measures a scope decision, not skill quality. Drop it or reword as 'flagged for a separate change'."},
                    {"assertion": "declined-work-reported",
                     "reason": "Passes for the old skill too because it accepts any 'deliberately not done' text. Should require a declined *abstraction* specifically."}],
                    "overall": "eval-1's assertions are mostly non-discriminating; eval-2 and eval-3 carry the signal."}
            }, indent=2))
            print(f"{name}/{cfg}: {passed}/{total}")


main()
