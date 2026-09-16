# SOLID review — `src.ts`

Diagnosis only. File untouched. 13 findings across all five rules; 4 are high severity (L2, L3, D1, I1 — they're the same root cause and will cause a production incident on the legacy Adyen path).

Severity: 🔴 will break at runtime / blocks the second consumer · 🟡 will cost you on the next change · ⚪ smell

---

## L — Liskov Substitution (worst area)

**L1 🔴 — `LegacyAdyenProvider` throws on 4 of 6 methods** (`src.ts:23-26`)
`refund`, `capturePreauth`, `voidPreauth`, `storeCard` all `throw new Error("not supported")` behind a signature that promises `Promise<Receipt>` / `Promise<string>`. This is the Penguin-that-can't-fly case exactly: the subtype is not substitutable, and the compiler cannot tell the caller. Any refund or vault flow that's fine on Stripe is a runtime crash on legacy Adyen — and line 1 says this file serves *two* consumers, so someone will pick the wrong one.
Fix: stop declaring `implements PaymentProvider` for the fat interface. Legacy Adyen implements only the capabilities it genuinely has (`Charge`). Then "does this provider support refunds?" becomes a compile-time check, not a try/catch.

**L2 🔴 — `verifyCard` returns hardcoded `true`** (`src.ts:27`)
Worse than L1 because it's silent. The base contract's postcondition is "true ⟺ the card was verified"; this returns true when *nothing was checked*. Callers written against the abstraction get a security/correctness lie, not an exception. A subtype must not weaken postconditions.
Fix: remove the capability from Legacy Adyen's type. If a call site genuinely must run on Adyen, model it explicitly as `CardVerifier | { verify(): "unsupported" }` at the boundary and make the caller handle both. Never fake success.

**L3 🔴 — `Checkout:61` discards the verification result and runs after the charge**
`await this.provider.verifyCard(...)` with no `if`, on line 61 — *after* `charge` on line 58. So the flow both ignores the postcondition and violates the ordering the method name implies (verify, then charge). Combined with L2, the mobile batch job would sail through on an unverified card.
Fix: verify before charging, branch on the boolean, and put the policy in one place (see S3).

**L4 🟡 — `StripeProvider`'s implementations are not substitutable either, as written** (`src.ts:13-18`)
Every method is `(amount, currency, card) { /* real impl */ }` with implicit `any` parameters. TypeScript structurally accepts these against `PaymentProvider`, so the compiler is not checking parameter counts/types at all — a future provider with a swapped `(currency, amount)` order passes the type check. Liskov is only as strong as the contract the compiler enforces.
Fix: annotate the implementations (or better, keep them and turn on `noImplicitAny`, which the current file will not compile under).

---

## I — Interface Segregation

**I1 🔴 — `PaymentProvider` is a 6-method god interface** (`src.ts:3-10`)
It bundles charging, refunds, preauth capture/void, card vaulting, and verification. `Checkout.checkout()` uses `charge` (+ `verifyCard`). Nobody needs all six. This fatness is what *creates* L1 and L2: because the interface is one monolith, an implementer that supports two of six must pretend to support six. Fix ISP first and the LSP failures largely stop being expressible.
Fix: split by capability, then compose for the providers that really are full-service:

```ts
interface Charger    { charge(a: Money, card: CardToken): Promise<Receipt> }
interface Refunder   { refund(receiptId: ReceiptId, a: Money): Promise<void> }
interface Preauthorizer { capturePreauth(id: PreauthId): Promise<Receipt>; voidPreauth(id: PreauthId): Promise<void> }
interface CardVault  { storeCard(card: CardToken): Promise<TokenId> }
interface CardVerifier { verifyCard(card: CardToken): Promise<boolean> }

// Stripe really is all of these — composition, not inheritance of a monolith.
type FullProvider = Charger & Refunder & Preauthorizer & CardVault & CardVerifier;
```

Each consumer's constructor takes only the interfaces it calls. `Checkout` needs `Charger`; the refund service needs `Refunder`. Legacy Adyen can then be a valid `Charger` with no lies.

**I2 ⚪ — the `Receipt`/`CartItem`/`Cart` contracts are undefined in this file**
Consumers depend on types whose shape nobody has asserted. Money as bare `number` across `charge`/`refund`/`totalWithTax` invites cent-vs-dollar and currency-mismatch bugs that the type system won't catch.
Fix: `Receipt`/`CardToken`/`PreauthId` branded types and a `Money { amount: bigint; currency: Currency }` value type. Cheap, and it's what makes I1's signatures actually say something.

---

## D — Dependency Inversion

**D1 🔴 — `Checkout` hardwires the concrete provider** (`src.ts:52`)
`private provider = new StripeProvider()`. The one class that must be swappable per consumer (line 1: web *and* mobile batch) can't be swapped at all without editing `Checkout`. Also: unit tests hit live Stripe, and there's no seam for a fake.
Fix: constructor injection against the abstraction.

```ts
class Checkout {
  constructor(
    private readonly pay: Charger,
    private readonly tax: TaxCalculator,
    private readonly audit: TaxAuditLog,
  ) {}
}
```
`new StripeProvider()` moves to a single composition root per entry point (web.ts, batch.ts).

**D2 🔴 — `TaxEngine` hardwires `fetch` to a URL** (`src.ts:43-46`)
A domain calculation depends on a concrete network transport and a hardcoded internal hostname. Untestable without a network stub; no way to retarget (queue, sidecar, file) without editing domain code; the URL cannot differ per environment.
Fix: define a `TaxAuditLog` port, inject it; keep the HTTP implementation as one adapter in the infrastructure layer. The audit failure should also be a deliberate policy decision, not an implicit `throw` that rolls back nothing after the charge already succeeded (see S4).

**D3 🟡 — `Checkout` constructs its own `TaxEngine` from `process.env`** (`src.ts:53`)
The use-case class reads environment configuration directly, with a non-null `!` assertion that will silently hand `"undefined"` to the region check and detonate at line 38 on the first request. Config parsing belongs at the composition root, validated once at startup.
Fix: read + validate `REGION` at boot; pass a `TaxCalculator` (or a `TaxPolicy`) in.

**D4 🟡 — the abstraction is provider-shaped, not consumer-shaped**
`PaymentProvider` is a port, which looks like DIP, but its methods are Stripe's vocabulary and Stripe's full surface. Depending on it is depending on Stripe's design through a thin veneer. Genuine inversion: `Checkout` declares what *it* needs (`Charger`), and Stripe/Adyen adapt to that. This is the same fix as I1 — that's why they're listed together.

---

## O — Open/Closed

**O1 🟡 — region rates are an if/else chain with a terminal `throw`** (`src.ts:35-38`)
Every new country, every VAT change, every US state carve-out means editing `TaxEngine.totalWithTax` — the same file the mobile batch job depends on, so each tax tweak is a regression risk to a working consumer. Note `US → 0` is already a special case bolted onto the chain.
Fix: closed data + open extension. A `TaxPolicy` per region (or one `Record<Region, TaxRule>` loaded from config), injected into the calculator:

```ts
interface TaxPolicy { rateFor(net: Money, items: readonly CartItem[]): Rate }
```
Adding Thailand-VAT-7-to-8 = one new data row. Adding per-item exemption handling = one new policy class. No edit to existing code.

**O2 🟡 — no seam for a second provider selection** (`src.ts:52`)
Adding "mobile batch runs on Adyen" requires modifying `Checkout`, the highest-traffic code path. Same fix as D1: extension by new composition root, `Checkout` never reopens.

**O3 ⚪ — `totalWithTax` takes `items` and ignores it** (`src.ts:33`)
The signature promises item-level taxation (exemptions, reduced rates) that the body doesn't implement. That's a tell that the real design is a strategy list over items, and today's flat net-rate calc is a placeholder. Either delete the parameter (YAGNI) or implement it behind O1's policy — but don't ship a signature that lies about what the function reads.

---

## S — Single Responsibility

**S1 🟡 — `TaxEngine` has two reasons to change** (`src.ts:30-49`)
Tax *rules* (lines 33-40) and audit-log *transport* (42-48). One changes with finance, the other with the logging platform; they share no state. Split into `TaxCalculator` and `TaxAuditLog` (which D2 requires anyway).

**S2 🟡 — `Checkout` has four reasons to change** (`src.ts:51-65`)
It (a) orchestrates the use case, (b) picks and constructs its payment provider, (c) reads env config to construct its tax engine, and (d) holds the "verify only when the cart is non-empty" business rule. Only (a) is its job. The header comment means any change to (b) or (c) for one consumer breaks the other.
Fix: `Checkout` = pure orchestration against injected ports; creation moves to the composition root; verification policy moves to a named rule (L3).

**S3 ⚪ — `if (cart.items.length > 0)` is an unexplained inline policy** (`src.ts:60`)
An empty cart still reaches here (charge of 0?), so the guard is doing something load-bearing that nobody can name. Either it's a validation rule (belongs in `Cart`/a guard clause at the top: reject empty carts before touching money) or it's a fee-fraud rule (belongs in a named policy object). Currently it's neither — it's a magic condition inside a flow, and it only "works" because L2 makes `verifyCard` a no-op.

**S4 🟡 — `logTaxEvent` is awaited after the money has moved** (`src.ts:58-59`)
If the audit POST fails, `logTaxEvent` throws, `checkout()` rejects, and the caller sees a failed checkout — while the charge at line 58 already succeeded and the receipt is unreachable. Two responsibilities tangled: "complete the order" vs "record the audit trail." Decide explicitly: audit is mandatory → charge only after it's reserved; audit is best-effort → don't let its failure propagate into the checkout result. Then the `Checkout` method has one job: produce a `Receipt` or a well-defined failure.

---

## Fix order

1. **I1** — split `PaymentProvider` into capability interfaces. Everything else depends on this; it deletes L1/L2's expressibility and turns D4 into a real port.
2. **D1/D2/D3** — constructor-inject `Charger`, `TaxCalculator`, `TaxAuditLog`; move `new StripeProvider()` + env parsing to two composition roots (web, batch). This is what makes the file testable.
3. **L2/L3/S3** — decide the verification contract: verify before charge, branch on the result, one named policy for when it applies. Highest business risk in the file; don't leave it for a "later refactor."
4. **S1/O1/O3** — split `TaxEngine`; replace the region if/else with an injected `TaxPolicy` (data or subclass).
5. **S4** — make the audit-failure semantics explicit.
6. **L4/I2** — type hygiene: annotate params, add branded `Money`/`Receipt` types, enable `noImplicitAny` (this file does not currently compile under it).

Steps 1-2 are mechanical and low risk, ~half a day with tests. Step 3 needs a product answer (should checkout ever proceed on an unverifiable card?) — get that before writing code.

## Quick Check (from the skill)

- Class changes for >1 reason? **Yes** — S1, S2.
- Adding a feature requires editing existing files? **Yes** — O1, O2.
- Can all subclasses replace parents safely? **No** — L1 (throws), L2 (lies).
- Interfaces split by use? **No** — I1.
- Dependencies injected as abstractions? **No** — D1, D2, D3.

All five rules violated. `src.ts:21-28` + `src.ts:52` are the two blocks I would not let through review as-is.
