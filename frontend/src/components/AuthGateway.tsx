import React, { useState } from "react";
import { 
  ShieldCheck, 
  Lock, 
  Mail, 
  User, 
  ArrowRight, 
  Sparkles, 
  Briefcase, 
  Building2, 
  Cpu
} from "lucide-react";

export interface UserProfile {
  name: string;
  email: string;
  role: string;
  organization?: string;
}

interface Props {
  onLoginSuccess: (user: UserProfile) => void;
}

export const AuthGateway: React.FC<Props> = ({ onLoginSuccess }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("Senior Equity Research Analyst");
  const [organization, setOrganization] = useState("Global Institutional Research");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError("Please provide both email and password.");
      return;
    }

    if (isSignUp && !name) {
      setError("Please provide your full name to create an analyst account.");
      return;
    }

    const profile: UserProfile = {
      name: isSignUp ? name : (email.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, c => c.toUpperCase()) || "Financial Analyst"),
      email,
      role,
      organization
    };

    localStorage.setItem("financial_workspace_user", JSON.stringify(profile));
    onLoginSuccess(profile);
  };

  const handleInstantDemoLogin = () => {
    const demoProfile: UserProfile = {
      name: "Dr. Eleanor Vance",
      email: "eleanor.vance@institutional-research.desk",
      role: "Lead Portfolio & Credit Analyst",
      organization: "Institutional Equity Research Enclave"
    };
    localStorage.setItem("financial_workspace_user", JSON.stringify(demoProfile));
    onLoginSuccess(demoProfile);
  };

  return (
    <div className="min-h-screen w-screen flex flex-col items-center justify-center bg-[#06080D] text-slate-100 font-sans relative overflow-hidden px-4">
      {/* Deep Space Background Ambient Glows */}
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-emerald-500/[0.04] rounded-full blur-[160px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-indigo-500/[0.05] rounded-full blur-[180px] pointer-events-none" />
      <div className="absolute top-10 right-1/3 w-[400px] h-[400px] bg-rose-500/[0.02] rounded-full blur-[140px] pointer-events-none" />

      {/* Main Container */}
      <div className="w-full max-w-xl z-10 space-y-6">
        {/* Terminal Header & Branding */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium shadow-sm">
            <Cpu className="w-3.5 h-3.5" />
            <span>Sovereign Multi-Agent Financial Research Enclave</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
            Financial Intelligence Desk
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
            Institutional AI Workspace powered by specialized autonomous agents for filing ingestion, ratio extraction, risk audits, and comparative research.
          </p>
        </div>

        {/* Guided Agent Workflow Summary Banner */}
        <div className="grid grid-cols-3 gap-2 p-3 rounded-2xl bg-slate-950/60 border border-white/[0.07] text-[11px] text-slate-300">
          <div className="flex items-center space-x-2 p-1.5 rounded-lg bg-white/[0.02]">
            <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
            <span className="truncate">1. Document Agent</span>
          </div>
          <div className="flex items-center space-x-2 p-1.5 rounded-lg bg-white/[0.02]">
            <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
            <span className="truncate">2. Extraction Agent</span>
          </div>
          <div className="flex items-center space-x-2 p-1.5 rounded-lg bg-white/[0.02]">
            <div className="w-2 h-2 rounded-full bg-rose-400 shrink-0" />
            <span className="truncate">3. Red Flag Agent</span>
          </div>
        </div>

        {/* Authentication Card */}
        <div className="glass-panel p-8 rounded-3xl border-white/[0.1] shadow-2xl backdrop-blur-2xl space-y-6">
          {/* Mode Tabs: Sign In vs Sign Up */}
          <div className="flex items-center p-1 bg-slate-950/80 border border-white/[0.08] rounded-xl text-xs">
            <button
              type="button"
              onClick={() => { setIsSignUp(false); setError(null); }}
              className={`flex-1 py-2 text-center rounded-lg font-bold transition cursor-pointer ${
                !isSignUp 
                  ? "bg-gradient-to-r from-emerald-600 to-teal-700 text-white shadow-md shadow-emerald-950" 
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In to Enclave
            </button>
            <button
              type="button"
              onClick={() => { setIsSignUp(true); setError(null); }}
              className={`flex-1 py-2 text-center rounded-lg font-bold transition cursor-pointer ${
                isSignUp 
                  ? "bg-gradient-to-r from-emerald-600 to-teal-700 text-white shadow-md shadow-emerald-950" 
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Create Analyst Account
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4 text-xs font-sans">
            {isSignUp && (
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span>Full Name</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Eleanor Vance"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950/90 border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition text-xs"
                />
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                <span>Analyst Email Address</span>
              </label>
              <input
                type="email"
                placeholder="analyst@institutional.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950/90 border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                <span>Security Passkey</span>
              </label>
              <input
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950/90 border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition text-xs"
              />
            </div>

            {isSignUp && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-slate-400" />
                    <span>Role / Designation</span>
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full bg-slate-950/90 border border-white/[0.08] rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/60 text-xs"
                  >
                    <option value="Senior Equity Research Analyst">Senior Equity Analyst</option>
                    <option value="Credit Risk & Audit Officer">Credit Risk Officer</option>
                    <option value="Portfolio Manager">Portfolio Manager</option>
                    <option value="Quantitative Research Director">Quantitative Director</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5">
                    <Building2 className="w-3.5 h-3.5 text-slate-400" />
                    <span>Institution / Desk</span>
                  </label>
                  <input
                    type="text"
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    className="w-full bg-slate-950/90 border border-white/[0.08] rounded-xl px-3.5 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/60 text-xs"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-extrabold text-xs transition duration-200 flex items-center justify-center space-x-2 shadow-lg shadow-emerald-500/20 cursor-pointer"
            >
              <span>{isSignUp ? "Create Account & Enter Workspace" : "Authenticate & Access Research Desk"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Access Button */}
          <div className="pt-3 border-t border-white/[0.06] text-center space-y-2">
            <span className="text-[10px] text-slate-400 font-medium">Quick Evaluator / Presenter Bypass</span>
            <button
              type="button"
              onClick={handleInstantDemoLogin}
              className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-emerald-300 hover:text-emerald-200 border border-emerald-500/30 text-xs font-bold transition flex items-center justify-center space-x-2 cursor-pointer shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Instant Demo Access (Lead Portfolio Analyst)</span>
            </button>
          </div>
        </div>

        {/* Footer Guarantee */}
        <div className="flex items-center justify-center space-x-4 text-[11px] text-slate-500">
          <span className="flex items-center space-x-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>FAISS & SQLite Sovereign Enclave</span>
          </span>
          <span>•</span>
          <span>100% Audited Provenance</span>
          <span>•</span>
          <span>Zero External Database Dependencies</span>
        </div>
      </div>
    </div>
  );
};
