"use client";

import { useState } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function SettingsPage() {
  const { user, loadUser } = useAuthStore();
  const [name, setName] = useState(user?.name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [twoFactorSetup, setTwoFactorSetup] = useState<any>(null);
  const [twoFactorCode, setTwoFactorCode] = useState("");

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await authApi.getMe();
      setMessage("Profile updated");
      loadUser();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Update failed");
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    try {
      setMessage("Password updated successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Password change failed");
    }
  };

  const handleSetup2FA = async () => {
    try {
      const { data } = await authApi.setup2FA();
      setTwoFactorSetup(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "2FA setup failed");
    }
  };

  const handleEnable2FA = async () => {
    try {
      await authApi.enable2FA(twoFactorCode);
      setTwoFactorSetup(null);
      setMessage("2FA enabled");
      loadUser();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid code");
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {message && <div className="bg-success/10 text-success p-3 rounded-lg mb-4 text-sm">{message}</div>}
      {error && <div className="bg-destructive/10 text-destructive p-3 rounded-lg mb-4 text-sm">{error}</div>}

      <div className="space-y-6">
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Profile</h2>
          <form onSubmit={handleProfileUpdate} className="space-y-4">
            <div>
              <label className="block text-sm mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Email</label>
              <input
                type="email"
                value={user?.email || ""}
                disabled
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2 text-muted-foreground"
              />
            </div>
            <button type="submit" className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
              Save Changes
            </button>
          </form>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Change Password</h2>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="block text-sm mb-1">Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-secondary border border-border rounded-lg px-4 py-2"
              />
            </div>
            <button type="submit" className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
              Update Password
            </button>
          </form>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Two-Factor Authentication</h2>
          {user?.two_factor_enabled ? (
            <div className="flex items-center justify-between">
              <p className="text-success text-sm">2FA is enabled</p>
              <button className="text-destructive text-sm hover:underline">Disable</button>
            </div>
          ) : twoFactorSetup ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Scan this QR code with your authenticator app:</p>
              {twoFactorSetup.qr_code_url && (
                <img src={twoFactorSetup.qr_code_url} alt="2FA QR" className="w-48 h-48" />
              )}
              <p className="text-sm">Secret: <code className="bg-secondary px-2 py-1 rounded">{twoFactorSetup.secret}</code></p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  placeholder="Enter 6-digit code"
                  className="bg-secondary border border-border rounded-lg px-4 py-2"
                />
                <button onClick={handleEnable2FA} className="bg-primary text-primary-foreground px-4 py-2 rounded-lg">
                  Verify
                </button>
              </div>
            </div>
          ) : (
            <button onClick={handleSetup2FA} className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
              Enable 2FA
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
