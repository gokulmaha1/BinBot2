"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { register, isLoading } = useAuthStore();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    try {
      await register(name, email, password);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed");
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-full max-w-md p-8 text-center">
          <h1 className="text-2xl font-bold mb-4">Check Your Email</h1>
          <p className="text-muted-foreground mb-6">
            We&apos;ve sent a verification email to {email}. Please verify your email to continue.
          </p>
          <Link href="/login" className="text-primary">Go to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-full max-w-md p-8">
        <Link href="/" className="text-2xl font-bold text-primary block text-center mb-8">BinBot AI</Link>
        <h1 className="text-2xl font-bold text-center mb-6">Create Account</h1>
        {error && <div className="bg-destructive/10 text-destructive p-3 rounded-lg mb-4 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              required
            />
          </div>
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
          <div>
            <label className="block text-sm mb-1">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? "Creating account..." : "Create Account"}
          </button>
        </form>
        <p className="text-center text-muted-foreground mt-4">
          Already have an account? <Link href="/login" className="text-primary">Login</Link>
        </p>
      </div>
    </div>
  );
}
