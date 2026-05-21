import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold text-primary">BinBot AI</Link>
          <div className="flex items-center gap-4">
            <Link href="/pricing" className="text-muted-foreground hover:text-foreground">Pricing</Link>
            <Link href="/login" className="text-muted-foreground hover:text-foreground">Login</Link>
            <Link href="/register" className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <section className="container mx-auto px-4 py-24 text-center">
          <h1 className="text-5xl font-bold mb-6">
            AI-Powered <span className="text-primary">Binance Futures</span> Trading
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Automated trading strategies with advanced risk management, ML predictions, and real-time analytics.
            Trade smarter, not harder.
          </p>
          <div className="flex justify-center gap-4">
            <Link href="/register" className="bg-primary text-primary-foreground px-8 py-3 rounded-lg text-lg hover:opacity-90">
              Start Free
            </Link>
            <Link href="/pricing" className="border border-border px-8 py-3 rounded-lg text-lg hover:bg-secondary">
              View Plans
            </Link>
          </div>
        </section>

        <section className="container mx-auto px-4 py-16">
          <h2 className="text-3xl font-bold text-center mb-12">Features</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { title: "AI Strategies", desc: "6 built-in strategies with ML confirmation for optimal entries" },
              { title: "Risk Management", desc: "Mandatory stop losses, dynamic position sizing, and drawdown protection" },
              { title: "Backtesting", desc: "Test strategies on historical data before risking real capital" },
              { title: "Paper Trading", desc: "Practice with virtual money in real market conditions" },
              { title: "Live Trading", desc: "Automated execution with Binance Futures API integration" },
              { title: "Analytics", desc: "Real-time PnL, win rate, Sharpe ratio, and detailed trade history" },
            ].map((feature, i) => (
              <div key={i} className="bg-card border border-border rounded-lg p-6">
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="container mx-auto px-4 py-16">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-8 text-center">
            {[
              { step: "1", title: "Register", desc: "Create your free account" },
              { step: "2", title: "Connect", desc: "Add your Binance API keys" },
              { step: "3", title: "Configure", desc: "Choose strategy and set risk" },
              { step: "4", title: "Trade", desc: "Start paper or live trading" },
            ].map((item, i) => (
              <div key={i}>
                <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 text-lg font-bold">
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                <p className="text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-8">
        <div className="container mx-auto px-4 text-center text-muted-foreground">
          <p>&copy; 2026 BinBot AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
