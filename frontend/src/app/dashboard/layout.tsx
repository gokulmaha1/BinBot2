"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import {
  LayoutDashboard,
  Bot,
  Settings,
  BarChart3,
  CreditCard,
  Shield,
  LogOut,
  Menu,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/bots", label: "Bots", icon: Bot },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/backtesting", label: "Backtesting", icon: BarChart3 },
  { href: "/dashboard/exchange", label: "Exchange", icon: Shield },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, loadUser, logout } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background flex">
      <aside className="w-64 border-r border-border hidden md:block">
        <div className="p-6">
          <Link href="/" className="text-xl font-bold text-primary">BinBot AI</Link>
          {user && <p className="text-xs text-muted-foreground mt-1">{user.plan} plan</p>}
        </div>
        <nav className="px-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-secondary"
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-4 left-4 right-4">
          <button
            onClick={() => { logout(); router.push("/login"); }}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary w-full"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      <main className="flex-1">
        <header className="border-b border-border px-6 py-4 flex items-center justify-between md:hidden">
          <Link href="/" className="text-xl font-bold text-primary">BinBot AI</Link>
          <Menu className="w-6 h-6" />
        </header>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
