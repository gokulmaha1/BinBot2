"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";

const symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];

export default function PriceTicker() {
  const [prices, setPrices] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPrices = async () => {
      const results: Record<string, any> = {};
      await Promise.all(
        symbols.map(async (sym) => {
          try {
            const { data } = await axios.get(
              `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/ws/price/${sym}`
            );
            results[sym] = data;
          } catch {
            results[sym] = null;
          }
        })
      );
      setPrices(results);
      setLoading(false);
    };

    fetchPrices();
    const interval = setInterval(fetchPrices, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="flex gap-4 animate-pulse">{symbols.map((_, i) => <div key={i} className="h-16 w-48 bg-secondary rounded-lg" />)}</div>;

  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {symbols.map((sym) => {
        const p = prices[sym];
        if (!p) return null;
        const isPositive = p.price_change_percent_24h >= 0;
        return (
          <div key={sym} className="bg-card border border-border rounded-lg p-4 min-w-[180px]">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-sm">{sym.replace("USDT", "")}</span>
              {isPositive ? <TrendingUp className="w-3 h-3 text-success" /> : <TrendingDown className="w-3 h-3 text-destructive" />}
            </div>
            <p className="text-lg font-bold">${p.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            <p className={`text-xs ${isPositive ? "text-success" : "text-destructive"}`}>
              {isPositive ? "+" : ""}{p.price_change_percent_24h?.toFixed(2)}%
            </p>
          </div>
        );
      })}
    </div>
  );
}
