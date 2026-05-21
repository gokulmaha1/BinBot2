import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${api.defaults.baseURL}/api/auth/refresh`, null, {
            params: { refresh_token: refreshToken },
          });
          localStorage.setItem("access_token", data.access_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(error.config);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      } else {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  register: (data: { name: string; email: string; password: string }) => api.post("/api/auth/register", data),
  login: (data: { email: string; password: string; totp_code?: string }) => api.post("/api/auth/login", data),
  verifyEmail: (token: string) => api.post("/api/auth/verify-email", { token }),
  requestPasswordReset: (email: string) => api.post("/api/auth/password-reset/request", { email }),
  resetPassword: (token: string, new_password: string) => api.post("/api/auth/password-reset/confirm", { token, new_password }),
  getMe: () => api.get("/api/auth/me"),
  setup2FA: () => api.post("/api/auth/2fa/setup"),
  enable2FA: (totp_code: string) => api.post("/api/auth/2fa/enable", { totp_code }),
  disable2FA: (totp_code: string) => api.post("/api/auth/2fa/disable", { totp_code }),
};

export const botsApi = {
  list: () => api.get("/api/bots/"),
  get: (id: string) => api.get(`/api/bots/${id}`),
  create: (data: any) => api.post("/api/bots/", data),
  update: (id: string, data: any) => api.put(`/api/bots/${id}`, data),
  delete: (id: string) => api.delete(`/api/bots/${id}`),
  start: (id: string) => api.post(`/api/bots/${id}/start`),
  stop: (id: string) => api.post(`/api/bots/${id}/stop`),
  trades: (id: string, limit = 50) => api.get(`/api/bots/${id}/trades?limit=${limit}`),
};

export const exchangesApi = {
  list: () => api.get("/api/exchanges/"),
  create: (data: any) => api.post("/api/exchanges/", data),
  delete: (id: string) => api.delete(`/api/exchanges/${id}`),
  test: (id: string) => api.post(`/api/exchanges/${id}/test`),
};

export const strategiesApi = {
  list: () => api.get("/api/strategies/"),
  get: (name: string) => api.get(`/api/strategies/${name}`),
  public: () => api.get("/api/strategies/public"),
};

export const backtestsApi = {
  run: (data: any) => api.post("/api/backtests/", data),
  list: () => api.get("/api/backtests/"),
  get: (id: string) => api.get(`/api/backtests/${id}`),
};

export const analyticsApi = {
  get: (days = 30) => api.get(`/api/analytics/?days=${days}`),
  getBot: (botId: string, days = 30) => api.get(`/api/analytics/bot/${botId}?days=${days}`),
};

export const billingApi = {
  checkout: (plan: string) => api.post("/api/billing/checkout", null, { params: { plan } }),
  cancel: () => api.post("/api/billing/cancel"),
  plans: () => api.get("/api/billing/plans"),
  subscription: () => api.get("/api/users/me/subscription"),
};

export const adminApi = {
  users: (page = 1, limit = 50) => api.get(`/api/admin/users?page=${page}&limit=${limit}`),
  stats: () => api.get("/api/admin/stats"),
  auditLogs: (page = 1, limit = 50) => api.get(`/api/admin/audit-logs?page=${page}&limit=${limit}`),
  disableUser: (id: string) => api.post(`/api/admin/users/${id}/disable`),
  enableUser: (id: string) => api.post(`/api/admin/users/${id}/enable`),
};

export default api;
