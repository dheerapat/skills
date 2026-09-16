# SOLID diagnosis — `src.ts` (design review; file untouched)

**Verdict: 6 findings, but only 1 seam worth paying for.** The file already ships two real payment
implementations, so the provider boundary is a genuine seam — and it's currently the wrong shape:
`I`, `L` and `D` are all the *same* broken boundary. Everything else is a rung-1/rung-2 fix (pass a
value or a function, split a file) or a seam I'd deliberately decline.

| # | Letter | Where | Severity | Fix rung |
|---|--------|-------|----------|----------|
| 1 | I | `PaymentProvider` L3–10 | high | 4 (narrow the *existing* interface) |
| 2 | L | `LegacyAdyenProvider` L21–28 | **high — fails silently** | falls out of #1 |
| 3 | D | `Checkout` L52–53 | high | 3→4 (constructor injection) |
| 4 | D | `logTaxEvent` L42–48 | medium | **1 (inject a function)** |
| 5 | S | `TaxEngine` L30–48 | medium | 2 (extract, no new types) |
| 6 | O | region chain L35–38 | **weak — data, not hierarchy** | 1 |

---

## 1. I — `PaymentProvider` is sized to the vendor's capability list, not to any client (L3–10)

Six methods; no client in this file uses more than two.

- The only client present (`Checkout`) touches `charge` (L58) and `verifyCard` (L61) — **2 of 6**.
- `LegacyAdyenProvider` `throw`s on **4 of 6** (L23–26). That's the loud ISP signal: every new
  implementer pays for the methods it can't do.
- The header comment says the file is "used by web and the mobile batch job". Those needs are almost
  certainly disjoint (web charges; a batch job refunds / captures preauths) — exactly the shape a fat
  interface punishes. Both clients must satisfy all six methods in tests, and neither can state in its
  own signature what it actually requires.

**Fix — split by client need, single-source the signatures with `Pick` (net deletion, no duplicated
types):**

```ts
type Charger      = Pick<PaymentProvider, "charge">;
type CardVerifier = Pick<PaymentProvider, "verifyCard">;
type Refunder     = Pick<PaymentProvider, "refund">;
type Preauth      = Pick<PaymentProvider, "capturePreauth" | "voidPreauth">;
type CardVault    = Pick<PaymentProvider, "storeCard">;
```

`PaymentProvider` stays as the *aggregate* the refund/admin client asks for
(`interface FullProvider extends Charger, Refunder, Preauth, CardVault {}`) — so it becomes an opt-in
for the capability instead of a tax on every implementer. `Checkout` takes `Charger & CardVerifier`.

## 2. L — `LegacyAdyenProvider` breaks substitutability twice (L21–28)

The loud break (throws on `refund`, `capturePreauth`, `voidPreauth`, `storeCard`) is the same defect
as #1, so the type split is also its fix: a provider that can't refund won't type-check into a
`Refunder` parameter, and no caller's `try/catch` is lying about what it catches.

The **quiet** break is the one I'd raise first in review:

```ts
async verifyCard() { return true; }   // always true — nothing is checked
```

This weakens the postcondition the base advertises (`Promise<boolean>` = "this is a real verdict").
Any caller that branches on it is silently disabled the day Adyen is wired in: fraud policy that
*looks* enforced is not. And because `charge` still runs afterwards (L58), it fails **open**. A
subtype may be as strict as the base, never looser in what it guarantees. Either do the verification
or don't claim it on the type.

**Fix:** capability becomes a separate type (#1); the legacy class implements only what it honors.
Do **not** fix it by adding `supportsRefund(): boolean` / `isStub()` flags to the base — that turns a
compile-time boundary into a runtime `switch` in every caller and is worse than deleting the methods.

## 3. D — `Checkout` constructs its own vendor client and reads env (L52–53)

```ts
private provider = new StripeProvider();
private tax = new TaxEngine(process.env.REGION!);
```

- Concrete I/O client built inside business logic → `checkout()` is untestable without Stripe, and the
  test double must satisfy all six methods from #1.
- The second implementation already exists in this file (Adyen) and is **unreachable** — the seam is
  evidenced, not imagined. This is the one place the Step-1 gate is unambiguously met.
- `process.env.REGION!` in a field initializer makes deployment config a dependency of the domain
  class, and the non-null assertion means a missing region surfaces as `unknown region undefined`
  (L38) on the first live checkout instead of at boot.

**Fix — constructor injection typed by client need** (in TS the "abstraction" is two `Pick` types, not
a new class layer):

```ts
class Checkout {
  constructor(private pay: Charger & CardVerifier, private tax: Tax) {}
}
```

Provider selection and the `REGION` read move to `main`/wiring — one site, validated at startup. A
test becomes `Checkout({ charge: async () => receipt, verifyCard: async () => true }, …)`; object
literal, no mocking library, no `ITaxEngineStrategy`.

## 4. D — raw `fetch` hardcoded inside `TaxEngine.logTaxEvent` (L42–48)

A math class contains a network call to a hardcoded internal URL. Testing the tax numbers requires
stubbing global `fetch`; and changing the endpoint, adding retry/batching, or applying PII rules to
the audit payload all edit the tax class.

**Fix — rung 1, the cheapest thing that holds.** It's a callable, not a hierarchy:

```ts
type TaxAudit = (e: { net: number; tax: number }) => Promise<void>;
class Tax { constructor(private rate: number, private audit: TaxAudit) {} }
```

The `fetch` version becomes a ~6-line function in the wiring module. TS idiom: type-only seams cost
nothing, class seams cost a file — so don't declare more than a function type. Promote to
`interface TaxAuditLog` only when a second implementation (SQS producer, file sink) or a second
consumer actually shows up.

## 5. S — `TaxEngine` is two jobs wearing one name (L30–48)

Count the kinds of reason this class gets edited: (a) tax law changes → L33–40; (b) audit
transport/endpoint/retry changes → L42–48. Two axes, and disjoint callers of the two methods. Same
disease in `Checkout`: it gets edited for orchestration order *and* for which vendor/deployment it
runs on.

**Fix — rung 2, no new types:** extract a pure `Tax` (sync math, trivially testable) and move the
audit call to a top-level `postTaxAudit` beside the other I/O. Two boring functions in two files beat
one class whose honest name would be "tax math *and* audit shipping" — the "and" is the tell the split
is correct.

## 6. O — the region `if/else` chain (L35–38): real, but the weakest finding

`O` requires evidence the set keeps growing — a branch per new variant in history — not a hunch. This
workspace has no git history and only three branches, so **do not** build `ITaxStrategy` + per-region
classes + a factory. That is the textbook over-application: four types replacing one number.

**Minimum that holds — make the variants data, and close the set in the type:**

```ts
type Region = "TH" | "DE" | "US";
const VAT: Record<Region, number> = { TH: 0.07, DE: 0.19, US: 0 };
```

A new region is one table entry + one union member, and the compiler flags anything unhandled — so the
runtime `throw new Error("unknown region")` mostly disappears. That's "add alongside the chain" for
~1 line.

**When to open it further:** the day rates stop being a single number (exemptions, per-item rates,
thresholds). L33 already accepts `items: CartItem[]` and **never uses it**, so someone anticipates
that. Even then the seam is already a constructor parameter, so the upgrade is a parameter change, not
a redesign.

---

## Also spotted in these lines — reporting only, not touching

1. **L61** `await this.provider.verifyCard(...)` — result discarded, and it runs *after* the charge.
   With #2, the verification path is decorative today. This is the bug-shaped one; file a ticket.
2. **L59** `logTaxEvent` throws *after* money moved (L58) → an audit outage reports a successful
   payment as a failed checkout. Effect ordering belongs to the orchestrator, not the tax class.
3. **L13–18** `StripeProvider`'s params are implicitly `any` — won't compile under `noImplicitAny`,
   and because TS method params are bivariant `implements` won't catch a drifted signature.
4. **L33** unused `items` param — speculative signature; delete until a rule needs it.

## Seams I'd deliberately decline (and why — reviewer needs this to check the decision)

- **No provider registry/factory** (rung 5). Two providers; the only dispatch site is `main`, which
  whoever adds the third is allowed to edit. A `ProviderFactory` + `register()` buys an indirection
  and nothing else. Revisit when tenant/plugin providers land.
- **No `ITaxStrategy`, no `TaxEngine` interface, no `CheckoutFacade`, no event bus** — one
  implementation each, no second caller I can name.
- **No `supportsX()` capability flags** — #1's type split replaces them.
- **Keep `PaymentProvider` as an aggregate**, don't widen it, don't delete it — "the thing that can do
  everything" needs a name for the refund client.

## Order of work (once you say go)

1. **Characterization tests first** (~1 h): pin `totalWithTax` for TH/DE/US, pin `checkout()` against
   a fake provider. None exist in this workspace, and #2/#3 change what the type system guarantees.
2. **Extract** (pure move, no signature churn): `Tax` math out of `TaxEngine`; `postTaxAudit` to the
   wiring module.
3. **Split the interface** with `Pick` (#1) and re-type `LegacyAdyenProvider` to only what it honors
   (#2). The compiler listing of broken call sites *is* the review output for refunds/verification.
4. **Inject** into `Checkout` (#3); move `new StripeProvider()` + `REGION` validation to `main`.
5. **Convert the region chain to the `VAT` table** (#6); re-run step 1's tests.

Steps 2–4 are ~30–60 lines each, step 5 ~8 lines. Half a day with tests; ~1 hour if tests are a
follow-up — I'd argue against skipping them for step 3.

**Next action:** the review question that decides severity is #2 — do callers of `verifyCard` outside
this file branch on its return value? Let me `grep` the repo for `.verifyCard(` and I can say whether
the legacy stub is a live fraud hole or a dormant one.
