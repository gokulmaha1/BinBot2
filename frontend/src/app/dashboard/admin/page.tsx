"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";

export default function AdminPage() {
  const { user, isAuthenticated } = useAuthStore();
  const router = useRouter();
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated || user?.role !== "admin") {
      router.push("/dashboard");
      return;
    }
    loadData();
  }, [isAuthenticated, user, router]);

  const loadData = async () => {
    try {
      const [statsRes, usersRes] = await Promise.all([
        adminApi.stats(),
        adminApi.users(1, 50),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data.users);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUser = async (id: string, currentStatus: boolean) => {
    try {
      if (currentStatus) {
        await adminApi.disableUser(id);
      } else {
        await adminApi.enableUser(id);
      }
      loadData();
    } catch (err) {
      alert("Failed to update user");
    }
  };

  if (loading) return <div className="text-center py-12">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Total Users", value: stats?.total_users || 0 },
          { label: "Total Bots", value: stats?.total_bots || 0 },
          { label: "Total Trades", value: stats?.total_trades || 0 },
          { label: "Active Bots", value: stats?.active_bots || 0 },
        ].map((stat) => (
          <div key={stat.label} className="bg-card border border-border rounded-lg p-6">
            <p className="text-sm text-muted-foreground">{stat.label}</p>
            <p className="text-2xl font-bold">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Users</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2">Name</th>
                <th className="text-left py-2">Email</th>
                <th className="text-left py-2">Plan</th>
                <th className="text-left py-2">Status</th>
                <th className="text-left py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-border last:border-0">
                  <td className="py-2">{u.name}</td>
                  <td className="py-2">{u.email}</td>
                  <td className="py-2">{u.plan}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs ${u.is_active ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
                      {u.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="py-2">
                    <button
                      onClick={() => handleToggleUser(u.id, u.is_active)}
                      className="text-sm text-primary hover:underline"
                    >
                      {u.is_active ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
