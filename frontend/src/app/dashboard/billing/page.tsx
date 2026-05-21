"use client";

import { useEffect, useState } from "react";
import { billingApi } from "@/lib/api";
import { CreditCard } from "lucide-react";

const plans = [
  { name: "Free", price: "$0", features: ["Paper trading only", "1 bot", "Basic indicators"] },
  { name: "Starter", price: "$29/mo", features: ["3 bots", "Backtesting", "Basic strategies", "Live trading"] },
  { name: "Pro", price: "$99/mo", features: ["Unlimited bots", "Advanced AI strategies", "ML predictions", "Analytics dashboard"] },
  { name: "Enterprise", price: "$299/mo", features: ["White-label", "API access", "Team management", "Custom strategies"] },
];

export default function BillingPage() {
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const { data } = await billingApi.subscription();
      setSubscription(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (plan: string) => {
    try {
      const { data } = await billingApi.checkout(plan);
      window.location.href = data.url;
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create checkout session");
    }
  };

  const handleCancel = async () => {
    if (!confirm("Cancel your subscription?")) return;
    try {
      await billingApi.cancel();
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to cancel");
    }
  };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Billing & Subscription</h1>

      <div className="bg-card border border-border rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Current Plan</h2>
        <div className="flex items-center gap-4">
          <CreditCard className="w-8 h-8 text-primary" />
          <div>
            <p className="font-medium text-lg">{subscription?.plan?.toUpperCase() || "FREE"}</p>
            <p className="text-sm text-muted-foreground">Status: {subscription?.status || "active"}</p>
          </div>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
      <div className="grid md:grid-cols-4 gap-4">
        {plans.map((plan) => (
          <div key={plan.name} className="bg-card border border-border rounded-lg p-6">
            <h3 className="font-semibold">{plan.name}</h3>
            <p className="text-2xl font-bold my-2">{plan.price}</p>
            <ul className="space-y-2 mb-4">
              {plan.features.map((f) => (
                <li key={f} className="text-sm text-muted-foreground">{f}</li>
              ))}
            </ul>
            {subscription?.plan?.toLowerCase() === plan.name.toLowerCase() ? (
              <button disabled className="w-full bg-secondary text-muted-foreground py-2 rounded-lg cursor-default">
                Current Plan
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade(plan.name.toLowerCase())}
                className="w-full bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90"
              >
                {subscription ? "Upgrade" : "Select"}
              </button>
            )}
          </div>
        ))}
      </div>

      {subscription?.status === "active" && subscription?.plan !== "free" && (
        <div className="mt-8">
          <button onClick={handleCancel} className="text-destructive text-sm hover:underline">
            Cancel Subscription
          </button>
        </div>
      )}
    </div>
  );
}
