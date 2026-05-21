import Link from "next/link";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/month",
    features: ["Paper trading only", "1 bot", "Basic indicators", "Email support"],
    cta: "Get Started",
    href: "/register",
    popular: false,
  },
  {
    name: "Starter",
    price: "$29",
    period: "/month",
    features: ["3 bots", "Backtesting", "Basic strategies", "Live trading", "Priority support"],
    cta: "Start Trial",
    href: "/register",
    popular: false,
  },
  {
    name: "Pro",
    price: "$99",
    period: "/month",
    features: ["Unlimited bots", "Advanced AI strategies", "ML predictions", "Analytics dashboard", "All strategies", "Priority support"],
    cta: "Start Trial",
    href: "/register",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "$299",
    period: "/month",
    features: ["White-label support", "API access", "Team management", "Custom strategies", "Dedicated support", "SLA"],
    cta: "Contact Sales",
    href: "/register",
    popular: false,
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold text-primary">BinBot AI</Link>
          <div className="flex items-center gap-4">
            <Link href="/" className="text-muted-foreground hover:text-foreground">Home</Link>
            <Link href="/login" className="text-muted-foreground hover:text-foreground">Login</Link>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-4 py-16">
        <h1 className="text-4xl font-bold text-center mb-4">Simple, Transparent Pricing</h1>
        <p className="text-xl text-muted-foreground text-center mb-12">Start free, upgrade when you&apos;re ready</p>

        <div className="grid md:grid-cols-4 gap-8 max-w-6xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`bg-card border rounded-lg p-6 ${plan.popular ? "border-primary ring-2 ring-primary" : "border-border"}`}
            >
              {plan.popular && (
                <span className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded-full">Popular</span>
              )}
              <h2 className="text-2xl font-bold mt-4">{plan.name}</h2>
              <div className="mt-4">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-muted-foreground">{plan.period}</span>
              </div>
              <ul className="mt-6 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm">
                    <svg className="w-4 h-4 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
              <Link
                href={plan.href}
                className={`mt-8 block text-center py-2 rounded-lg ${plan.popular ? "bg-primary text-primary-foreground" : "border border-border hover:bg-secondary"}`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
