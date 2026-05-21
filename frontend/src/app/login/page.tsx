"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [requires2FA, setRequires2FA] = useState(false);
  const [error, setError] = useState("");
  const { login, isLoading } = useAuthStore();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login(email, password, requires2FA ? totpCode : undefined);
      router.push("/dashboard");
    } catch (err: any) {
      if (err.response?.headers?.["x-2fa-required"]) {
        setRequires2FA(true);
      } else {
        setError(err.response?.data?.detail || "Login failed");
      }
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-full max-w-md p-8">
        <Link href="/" className="text-2xl font-bold text-primary block text-center mb-8">BinBot AI</Link>
        <h1 className="text-2xl font-bold text-center mb-6">Login</h1>
        {error && <div className="bg-destructive/10 text-destructive p-3 rounded-lg mb-4 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              required
            />
          </div>
          {requires2FA && (
            <div>
              <label className="block text-sm mb-1">2FA Code</label>
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
                placeholder="Enter 6-digit code"
                required
              />
            </div>
          )}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? "Logging in..." : "Login"}
          </button>
        </form>
        <p className="text-center text-muted-foreground mt-4">
          Don&apos;t have an account? <Link href="/register" className="text-primary">Register</Link>
        </p>
      </div>
    </div>
  );
}
