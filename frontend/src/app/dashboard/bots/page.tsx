"use client";

import { useEffect, useState } from "react";
import { botsApi, strategiesApi } from "@/lib/api";
import { Plus, Play, Square, Trash2 } from "lucide-react";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"];
const STRATEGIES = ["trend_following", "mean_reversion", "momentum_breakout", "scalping", "volatility_expansion", "multi_timeframe"];

export default function BotsPage() {
  const [bots, setBots] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    name: "",
    strategy: "trend_following",
    symbol: "BTCUSDT",
    leverage: 1,
    live_mode: false,
  });

  useEffect(() => {
    loadBots();
  }, []);

  const loadBots = async () => {
    try {
      const { data } = await botsApi.list();
      setBots(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await botsApi.create(formData);
      setShowCreate(false);
      setFormData({ name: "", strategy: "trend_following", symbol: "BTCUSDT", leverage: 1, live_mode: false });
      loadBots();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create bot");
    }
  };

  const handleStart = async (id: string) => {
    try {
      await botsApi.start(id);
      loadBots();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to start bot");
    }
  };

  const handleStop = async (id: string) => {
    try {
      await botsApi.stop(id);
      loadBots();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to stop bot");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this bot?")) return;
    try {
      await botsApi.delete(id);
      loadBots();
    } catch (err) {
      alert("Failed to delete bot");
    }
  };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Trading Bots</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-lg flex items-center gap-2 hover:opacity-90"
        >
          <Plus className="w-4 h-4" /> Create Bot
        </button>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create New Bot</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                  required
                />
              </div>
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
                <label className="block text-sm mb-1">Leverage (1-5x)</label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.leverage}
                  onChange={(e) => setFormData({ ...formData, leverage: parseInt(e.target.value) })}
                  className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="live_mode"
                  checked={formData.live_mode}
                  onChange={(e) => setFormData({ ...formData, live_mode: e.target.checked })}
                />
                <label htmlFor="live_mode" className="text-sm">Enable Live Trading</label>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="flex-1 bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90">
                  Create
                </button>
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 border border-border py-2 rounded-lg hover:bg-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {bots.length === 0 ? (
        <div className="bg-card border border-border rounded-lg p-12 text-center">
          <p className="text-muted-foreground mb-4">No bots yet. Create your first trading bot to get started.</p>
          <button onClick={() => setShowCreate(true)} className="bg-primary text-primary-foreground px-6 py-2 rounded-lg">
            Create Bot
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {bots.map((bot) => (
            <div key={bot.id} className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{bot.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {bot.symbol} - {bot.strategy.replace(/_/g, " ")} - {bot.leverage}x
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs ${
                    bot.status === "running" ? "bg-success/10 text-success" : "bg-muted text-muted-foreground"
                  }`}>
                    {bot.status}
                  </span>
                  {bot.live_mode && (
                    <span className="px-2 py-1 rounded text-xs bg-warning/10 text-warning">LIVE</span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <p className="text-sm text-muted-foreground">PnL</p>
                  <p className={`font-medium ${bot.total_pnl >= 0 ? "text-success" : "text-destructive"}`}>
                    ${bot.total_pnl?.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Win Rate</p>
                  <p className="font-medium">{(bot.win_rate * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Trades</p>
                  <p className="font-medium">{bot.total_trades}</p>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                {bot.status === "stopped" ? (
                  <button onClick={() => handleStart(bot.id)} className="flex items-center gap-1 bg-success/10 text-success px-3 py-1 rounded text-sm hover:bg-success/20">
                    <Play className="w-3 h-3" /> Start
                  </button>
                ) : (
                  <button onClick={() => handleStop(bot.id)} className="flex items-center gap-1 bg-destructive/10 text-destructive px-3 py-1 rounded text-sm hover:bg-destructive/20">
                    <Square className="w-3 h-3" /> Stop
                  </button>
                )}
                <button onClick={() => handleDelete(bot.id)} className="flex items-center gap-1 text-muted-foreground px-3 py-1 rounded text-sm hover:bg-secondary">
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
