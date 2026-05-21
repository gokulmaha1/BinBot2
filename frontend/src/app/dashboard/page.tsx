"use client";

import { useEffect, useState } from "react";
import { analyticsApi, botsApi } from "@/lib/api";
import PriceTicker from "@/components/price-ticker";
import { TrendingUp, TrendingDown, Activity, Target, DollarSign, Percent } from "lucide-react";

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [bots, setBots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [analyticsRes, botsRes] = await Promise.all([
        analyticsApi.get(30),
        botsApi.list(),
      ]);
      setAnalytics(analyticsRes.data);
      setBots(botsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  const stats = [
    { label: "Total PnL", value: analytics?.total_pnl || 0, icon: DollarSign, prefix: "$" },
    { label: "Win Rate", value: analytics?.win_rate || 0, icon: Percent, suffix: "%" },
    { label: "Total Trades", value: analytics?.total_trades || 0, icon: Activity },
    { label: "Active Bots", value: bots.filter((b) => b.status === "running").length, icon: Target },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="mb-6">
        <PriceTicker />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          const isPositive = stat.value >= 0;
          return (
            <div key={stat.label} className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground text-sm">{stat.label}</span>
                <Icon className="w-4 h-4 text-muted-foreground" />
              </div>
              <div className={`text-2xl font-bold ${stat.label === "Total PnL" ? (isPositive ? "text-success" : "text-destructive") : ""}`}>
                {stat.prefix}{typeof stat.value === "number" && stat.label === "Win Rate"
                  ? (stat.value * 100).toFixed(1)
                  : stat.value}{stat.suffix}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Active Bots</h2>
          {bots.length === 0 ? (
            <p className="text-muted-foreground text-sm">No bots yet. Create your first bot to get started.</p>
          ) : (
            <div className="space-y-3">
              {bots.slice(0, 5).map((bot) => (
                <div key={bot.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="font-medium">{bot.name}</p>
                    <p className="text-sm text-muted-foreground">{bot.symbol} - {bot.strategy}</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${
                    bot.status === "running" ? "bg-success/10 text-success" : "bg-muted text-muted-foreground"
                  }`}>
                    {bot.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Trades</h2>
          {analytics?.trade_history?.length === 0 ? (
            <p className="text-muted-foreground text-sm">No trades yet.</p>
          ) : (
            <div className="space-y-3">
              {analytics?.trade_history?.slice(0, 5).map((trade: any) => (
                <div key={trade.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="font-medium">{trade.symbol}</p>
                    <p className="text-sm text-muted-foreground">{trade.side} @ {trade.entry_price}</p>
                  </div>
                  <span className={`font-medium ${trade.pnl >= 0 ? "text-success" : "text-destructive"}`}>
                    {trade.pnl >= 0 ? "+" : ""}{trade.pnl?.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
