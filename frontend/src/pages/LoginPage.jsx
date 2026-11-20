import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, Eye, EyeOff, Loader2, ShieldCheck, Sparkles, UserCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    if (error) setError("");
  };

  const handleQuickLogin = (uname, pwd) => {
    setForm({ username: uname, password: pwd });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.username.trim() || !form.password.trim()) {
      setError("Please enter both username and password.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await login(form.username.trim(), form.password);
      if (res && res.success) {
        navigate("/dashboard");
      } else {
        setError(res?.error || "Invalid username or password. Please try again.");
      }
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Invalid credentials. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 via-blue-700 to-cyan-500 px-4 py-12">
      {/* Decorative blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-blue-500 opacity-20 rounded-full blur-3xl" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-cyan-400 opacity-20 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Card */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 sm:p-10">
          {/* Logo */}
          <div className="flex flex-col items-center mb-6 select-none">
            <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-red-400 to-pink-600 shadow-lg mb-4">
              <Heart className="w-9 h-9 text-white fill-white" />
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              MediXAI Decision Support
            </h1>
            <p className="mt-1 text-xs font-medium text-blue-200 tracking-widest uppercase">
              Explainable AI · Smart Scheduling · DPDP Compliant
            </p>
          </div>

          {/* Quick Demo Fill Buttons */}
          <div className="mb-6 p-3 bg-white/10 rounded-2xl border border-white/15">
            <span className="text-[11px] font-bold text-blue-100 uppercase tracking-wider block mb-2 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-300" /> One-Click Demo Credentials:
            </span>
            <div className="grid grid-cols-3 gap-1.5 text-xs">
              <button
                type="button"
                onClick={() => handleQuickLogin("admin", "admin123")}
                className="py-1.5 px-2 bg-white/15 hover:bg-white/30 text-white rounded-lg font-semibold transition-colors text-center"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("drpriya", "doctor123")}
                className="py-1.5 px-2 bg-white/15 hover:bg-white/30 text-white rounded-lg font-semibold transition-colors text-center"
              >
                Doctor
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("nurse1", "nurse123")}
                className="py-1.5 px-2 bg-white/15 hover:bg-white/30 text-white rounded-lg font-semibold transition-colors text-center"
              >
                Patient
              </button>
            </div>
          </div>

          {/* Error alert */}
          {error && (
            <div className="mb-5 px-4 py-3 rounded-xl bg-red-500/20 border border-red-400/40 text-red-100 text-xs font-medium flex items-center gap-2 animate-shake">
              <span className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-semibold text-blue-100 mb-1.5"
              >
                Username or Email
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={form.username}
                onChange={handleChange}
                placeholder="e.g. admin or drpriya"
                className="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-blue-200/50 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 transition"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold text-blue-100 mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={form.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 pr-11 rounded-xl bg-white/10 border border-white/20 text-white placeholder-blue-200/50 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 transition"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-blue-200 hover:text-white transition"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 active:scale-[0.98] text-slate-900 font-bold text-sm shadow-lg shadow-cyan-500/25 transition disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <span>Sign In to Console</span>
              )}
            </button>
          </form>

          {/* Footer note */}
          <div className="mt-6 pt-5 border-t border-white/10 flex items-center justify-between text-[11px] text-blue-200/70">
            <span className="flex items-center gap-1 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-cyan-300" />
              DPDP Act 2023 Compliant
            </span>
            <span className="font-mono">SQLite3 WAL Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
