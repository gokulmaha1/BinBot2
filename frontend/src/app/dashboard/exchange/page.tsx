"use client";

import { useEffect, useState } from "react";
import { exchangesApi } from "@/lib/api";
import { Plus, Trash2, CheckCircle, XCircle } from "lucide-react";

export default function ExchangePage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({ api_key: "", api_secret: "", testnet: true });
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const { data } = await exchangesApi.list();
      setAccounts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await exchangesApi.create(formData);
      setShowCreate(false);
      setFormData({ api_key: "", api_secret: "", testnet: true });
      loadAccounts();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to add exchange account");
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const { data } = await exchangesApi.test(id);
      alert(`Connected! Balance: ${data.total_balance} USDT`);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Connection failed");
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this exchange account?")) return;
    try {
      await exchangesApi.delete(id);
      loadAccounts();
    } catch (err) {
      alert("Failed to delete");
    }
  };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Exchange Connection</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-lg flex items-center gap-2 hover:opacity-90"
        >
          <Plus className="w-4 h-4" /> Add API Key
        </button>
      </div>

      <div className="bg-warning/10 border border-warning/20 rounded-lg p-4 mb-6">
        <p className="text-sm text-warning">
          Never share your API keys. Only enable &quot;Enable Futures&quot; permission. Disable withdrawal permissions.
        </p>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Add Binance API</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm mb-1">API Key</label>
                <input
                  type="text"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm mb-1">API Secret</label>
                <input
                  type="password"
                  value={formData.api_secret}
                  onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                  className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                  required
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="testnet"
                  checked={formData.testnet}
                  onChange={(e) => setFormData({ ...formData, testnet: e.target.checked })}
                />
                <label htmlFor="testnet" className="text-sm">Use Testnet (recommended for testing)</label>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="flex-1 bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90">
                  Add
                </button>
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 border border-border py-2 rounded-lg hover:bg-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="bg-card border border-border rounded-lg p-12 text-center">
          <p className="text-muted-foreground mb-4">No exchange accounts connected.</p>
          <button onClick={() => setShowCreate(true)} className="bg-primary text-primary-foreground px-6 py-2 rounded-lg">
            Add API Key
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => (
            <div key={account.id} className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Binance {account.testnet ? "Testnet" : "Mainnet"}</h3>
                  <p className="text-sm text-muted-foreground">
                    Key: {account.exchange} - {account.is_active ? "Active" : "Inactive"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {account.is_active ? (
                    <CheckCircle className="w-5 h-5 text-success" />
                  ) : (
                    <XCircle className="w-5 h-5 text-destructive" />
                  )}
                  <button
                    onClick={() => handleTest(account.id)}
                    disabled={testing === account.id}
                    className="text-sm text-primary hover:underline"
                  >
                    {testing === account.id ? "Testing..." : "Test"}
                  </button>
                  <button onClick={() => handleDelete(account.id)} className="text-muted-foreground hover:text-destructive">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
