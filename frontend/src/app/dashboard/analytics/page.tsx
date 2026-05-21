"use client";

import { useEffect, useState } from "react";
import { analyticsApi } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [days]);

  const loadAnalytics = async () => {
    try {
      const { data } = await analyticsApi.get(days);
      setAnalytics(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  const metrics = [
    { label: "Total PnL", value: `$${analytics?.total_pnl?.toFixed(2) || "0.00"}`, color: analytics?.total_pnl >= 0 ? "text-success" : "text-destructive" },
    { label: "Win Rate", value: `${((analytics?.win_rate || 0) * 100).toFixed(1)}%` },
    { label: "Total Trades", value: analytics?.total_trades || 0 },
    { label: "Max Drawdown", value: `${((analytics?.max_drawdown || 0) * 100).toFixed(1)}%` },
    { label: "Sharpe Ratio", value: analytics?.sharpe_ratio?.toFixed(2) || "0.00" },
    { label: "Profit Factor", value: analytics?.profit_factor?.toFixed(2) || "0.00" },
    { label: "Avg Win", value: `$${analytics?.avg_win?.toFixed(2) || "0.00"}`, color: "text-success" },
    { label: "Avg Loss", value: `$${analytics?.avg_loss?.toFixed(2) || "0.00"}`, color: "text-destructive" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <select
          value={days}
          onChange={(e) => setDays(parseInt(e.target.value))}
          className="bg-secondary border border-border rounded-lg px-4 py-2"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="bg-card border border-border rounded-lg p-4">
            <p className="text-sm text-muted-foreground">{m.label}</p>
            <p className={`text-xl font-bold ${m.color || ""}`}>{m.value}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Daily PnL</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={analytics?.daily_pnl || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
              <Bar dataKey="pnl" fill="#3b82f6">
                {(analytics?.daily_pnl || []).map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? "#22c55e" : "#ef4444"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Equity Curve</h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={analytics?.daily_pnl?.reduce((acc: any[], d: any, i: number) => {
              const prev = i > 0 ? acc[i-1].equity : 10000;
              acc.push({ date: d.date, equity: prev + d.pnl });
              return acc;
            }, []) || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
              <Line type="monotone" dataKey="equity" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Trade History</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2">Symbol</th>
                <th className="text-left py-2">Side</th>
                <th className="text-right py-2">Entry</th>
                <th className="text-right py-2">Exit</th>
                <th className="text-right py-2">PnL</th>
                <th className="text-left py-2">Reason</th>
              </tr>
            </thead>
            <tbody>
              {analytics?.trade_history?.slice(0, 20).map((trade: any) => (
                <tr key={trade.id} className="border-b border-border last:border-0">
                  <td className="py-2">{trade.symbol}</td>
                  <td className={`py-2 ${trade.side === "BUY" ? "text-success" : "text-destructive"}`}>{trade.side}</td>
                  <td className="text-right py-2">{trade.entry_price}</td>
                  <td className="text-right py-2">{trade.exit_price || "-"}</td>
                  <td className={`text-right py-2 font-medium ${trade.pnl >= 0 ? "text-success" : "text-destructive"}`}>
                    {trade.pnl >= 0 ? "+" : ""}{trade.pnl?.toFixed(2)}
                  </td>
                  <td className="py-2 text-muted-foreground">{trade.exit_reason || "Open"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
