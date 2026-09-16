// Checkout.ts — used by web and the mobile batch job.

interface PaymentProvider {
  charge(amount: number, currency: string, card: string): Promise<Receipt>;
  refund(receiptId: string, amount: number): Promise<void>;
  capturePreauth(preauthId: string): Promise<Receipt>;
  voidPreauth(preauthId: string): Promise<void>;
  storeCard(card: string): Promise<string>;
  verifyCard(card: string): Promise<boolean>;
}

class StripeProvider implements PaymentProvider {
  async charge(amount, currency, card) { /* real impl */ }
  async refund(receiptId, amount) { /* real impl */ }
  async capturePreauth(preauthId) { /* real impl */ }
  async voidPreauth(preauthId) { /* real impl */ }
  async storeCard(card) { /* real impl */ }
  async verifyCard(card) { /* real impl */ }
}

class LegacyAdyenProvider implements PaymentProvider {
  async charge(amount, currency, card) { /* real impl */ }
  async refund() { throw new Error("refunds not supported on legacy adyen"); }
  async capturePreauth() { throw new Error("no preauth on legacy adyen"); }
  async voidPreauth() { throw new Error("no preauth on legacy adyen"); }
  async storeCard() { throw new Error("no vault on legacy adyen"); }
  async verifyCard() { return true; }   // always true — nothing is checked
}

class TaxEngine {
  constructor(private region: string) {}

  totalWithTax(net: number, items: CartItem[]): number {
    let tax = 0;
    if (this.region === "TH") tax = net * 0.07;
    else if (this.region === "DE") tax = net * 0.19;
    else if (this.region === "US") tax = 0;
    else throw new Error("unknown region " + this.region);
    return net + tax;
  }

  async logTaxEvent(net: number, tax: number) {
    const res = await fetch("https://tax-audit.internal/log", {
      method: "POST",
      body: JSON.stringify({ net, tax }),
    });
    if (!res.ok) throw new Error("audit log failed");
  }
}

class Checkout {
  private provider = new StripeProvider();
  private tax = new TaxEngine(process.env.REGION!);

  async checkout(cart: Cart): Promise<Receipt> {
    const net = cart.subtotal();
    const total = this.tax.totalWithTax(net, cart.items);
    const receipt = await this.provider.charge(total, cart.currency, cart.cardToken);
    await this.tax.logTaxEvent(net, total - net);
    if (cart.items.length > 0) {
      await this.provider.verifyCard(cart.cardToken);
    }
    return receipt;
  }
}
