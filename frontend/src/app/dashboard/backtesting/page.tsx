"use client";

import { useEffect, useState } from "react";
import { backtestsApi } from "@/lib/api";
import { Play } from "lucide-react";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];
const STRATEGIES = ["trend_following", "mean_reversion", "momentum_breakout", "scalping", "volatility_expansion", "multi_timeframe"];
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"];

export default function BacktestingPage() {
  const [backtests, setBacktests] = useState<any[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [formData, setFormData] = useState({
    strategy: "trend_following",
    symbol: "BTCUSDT",
    timeframe: "1h",
    start_date: "",
    end_date: "",
    initial_capital: 10000,
  });

  useEffect(() => {
    loadBacktests();
  }, []);

  const loadBacktests = async () => {
    try {
      const { data } = await backtestsApi.list();
      setBacktests(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setResult(null);
    try {
      const { data } = await backtestsApi.run(formData);
      setResult(data);
      loadBacktests();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Backtest failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Backtesting</h1>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Configure Backtest</h2>
          <form onSubmit={handleRun} className="space-y-4">
            <div>
              <label className="block text-sm mb-1">Strategy</label>
              <select
                value={formData.strategy}
                onChange={(e) => setFormData({ ...formData, strategy: e.target.value })}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              >
                {STRATEGIES.map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm mb-1">Symbol</label>
              <select
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              >
                {SYMBOLS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm mb-1">Timeframe</label>
              <select
                value={formData.timeframe}
                onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              >
                {TIMEFRAMES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm mb-1">Start Date</label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm mb-1">End Date</label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm mb-1">Initial Capital</label>
              <input
                type="number"
                value={formData.initial_capital}
                onChange={(e) => setFormData({ ...formData, initial_capital: parseFloat(e.target.value) })}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              />
            </div>
            <button
              type="submit"
              disabled={running}
              className="w-full bg-primary text-primary-foreground py-2 rounded-lg flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50"
            >
              <Play className="w-4 h-4" /> {running ? "Running..." : "Run Backtest"}
            </button>
          </form>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Results</h2>
          {result ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Return</p>
                  <p className={`text-xl font-bold ${result.total_return_pct >= 0 ? "text-success" : "text-destructive"}`}>
                    {result.total_return_pct?.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Win Rate</p>
                  <p className="text-xl font-bold">{(result.win_rate * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Trades</p>
                  <p className="text-xl font-bold">{result.total_trades}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Max Drawdown</p>
                  <p className="text-xl font-bold">{(result.max_drawdown * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
                  <p className="text-xl font-bold">{result.sharpe_ratio?.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Profit Factor</p>
                  <p className="text-xl font-bold">{result.profit_factor?.toFixed(2)}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">Run a backtest to see results here.</p>
          )}
        </div>
      </div>

      {backtests.length > 0 && (
        <div className="mt-8 bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Previous Backtests</h2>
          <div className="space-y-2">
            {backtests.slice(0, 10).map((bt) => (
              <div key={bt.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <div>
                  <p className="font-medium">{bt.strategy.replace(/_/g, " ")} - {bt.symbol}</p>
                  <p className="text-sm text-muted-foreground">{bt.timeframe} | {bt.start_date?.split("T")[0]} to {bt.end_date?.split("T")[0]}</p>
                </div>
                <p className={`font-medium ${(bt.result?.total_return_pct || 0) >= 0 ? "text-success" : "text-destructive"}`}>
                  {(bt.result?.total_return_pct || 0).toFixed(2)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
