"use client";

import { useState } from "react";
import { ArrowRight, Check, KeyRound, Lock, LogOut, ShieldCheck, User, UserCheck, UserPlus, X } from "lucide-react";

export const PRESET_OFFICERS = [
  {
    id: "mospi-lead",
    name: "Dr. Abhinav Sharma",
    email: "analyst@mospi.gov.in",
    agency: "Ministry of Statistics & PI (MoSPI)",
    role: "Senior Statistical Officer",
    clearance: "Level 4 · Full CPI Authority",
    badge: "MoSPI Lead",
    initials: "AS",
    avatarColor: "#10b981",
  },
  {
    id: "dgca-lead",
    name: "Priya Nair",
    email: "p.nair@dgca.gov.in",
    agency: "Directorate General of Civil Aviation (DGCA)",
    role: "Air Transport Analytics Lead",
    clearance: "Level 3 · Corridor & Yield Access",
    badge: "DGCA Lead",
    initials: "PN",
    avatarColor: "#38bdf8",
  },
  {
    id: "rbi-research",
    name: "Vikramaditya Sen",
    email: "v.sen@rbi.org.in",
    agency: "Reserve Bank of India (DEPR)",
    role: "Macro Inflation Researcher",
    clearance: "Level 3 · Macroeconomic Surveillance",
    badge: "RBI DEPR",
    initials: "VS",
    avatarColor: "#a78bfa",
  },
];

export const AUTH_STORAGE_KEY = "airfare-cpi-user-session-v1";

export default function AuthModal({ isOpen, onClose, currentUser, onLogin, onLogout, onNotify }) {
  const [tab, setTab] = useState("signin"); // 'signin' | 'signup' | 'profile'
  const [email, setEmail] = useState("analyst@mospi.gov.in");
  const [pin, setPin] = useState("••••••••••••");

  // Sign up state
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupAgency, setSignupAgency] = useState("MoSPI");
  const [signupClearance, setSignupClearance] = useState("Level 2 · Statistical Contributor");
  const [signupPin, setSignupPin] = useState("");

  if (!isOpen) return null;

  const handleQuickLogin = (officer) => {
    onLogin(officer);
    onClose();
    if (onNotify) onNotify(`Authorized: Welcome back, ${officer.name} (${officer.badge}).`);
  };

  const handleCustomSignIn = (e) => {
    e.preventDefault();
    if (!email) {
      if (onNotify) onNotify("Please enter a valid government or research email ID.", "warning");
      return;
    }

    const matched = PRESET_OFFICERS.find((o) => o.email.toLowerCase() === email.toLowerCase());
    const userSession = matched || {
      id: `user-${Date.now()}`,
      name: email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      email,
      agency: email.includes("mospi") ? "MoSPI" : email.includes("gov.in") ? "Government of India" : "Aviation Research Institute",
      role: "Verified Statistical Analyst",
      clearance: "Level 2 · Standard Clearance",
      badge: "Analyst",
      initials: email.slice(0, 2).toUpperCase(),
      avatarColor: "#10b981",
    };

    onLogin(userSession);
    onClose();
    if (onNotify) onNotify(`Authenticated as ${userSession.name} (${userSession.agency}).`);
  };

  const handleSignUp = (e) => {
    e.preventDefault();
    if (!signupName.trim()) {
      if (onNotify) onNotify("Please enter your full name.", "warning");
      return;
    }
    if (!signupEmail.trim() || !signupEmail.includes("@")) {
      if (onNotify) onNotify("Please enter a valid institutional email address.", "warning");
      return;
    }

    const initials = signupName
      .split(" ")
      .map((part) => part[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "AO";

    const newUser = {
      id: `officer-${Date.now()}`,
      name: signupName.trim(),
      email: signupEmail.trim(),
      agency: signupAgency,
      role: signupAgency.includes("MoSPI") ? "Statistical Officer" : "Research Analyst",
      clearance: signupClearance,
      badge: signupAgency.slice(0, 8),
      initials,
      avatarColor: "#10b981",
    };

    onLogin(newUser);
    onClose();
    if (onNotify) onNotify(`Registration Approved: Clearance credentials activated for ${newUser.name}.`);
  };

  const handleSignOutClick = () => {
    onLogout();
    onClose();
    if (onNotify) onNotify("Signed out of secure session.");
  };

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="auth-modal-backdrop">
      <div
        className="modal-panel modal-panel-auth"
        onClick={(e) => e.stopPropagation()}
        data-testid="auth-modal-panel"
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">
              {currentUser ? "Active Session & Clearance" : "MoSPI Sovereign Access Control"}
            </p>
            <h3>
              {currentUser ? "Officer Profile" : tab === "signin" ? "Sign in to MoSPI Portal" : "Request Portal Access"}
            </h3>
          </div>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
            data-testid="auth-modal-close-button"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        {!currentUser ? (
          <div className="auth-tab-bar" data-testid="auth-tab-bar">
            <button
              type="button"
              className={tab === "signin" ? "is-active" : ""}
              onClick={() => setTab("signin")}
              data-testid="auth-tab-signin"
            >
              <KeyRound size={14} /> Sign in with SSO
            </button>
            <button
              type="button"
              className={tab === "signup" ? "is-active" : ""}
              onClick={() => setTab("signup")}
              data-testid="auth-tab-signup"
            >
              <UserPlus size={14} /> Request Clearance (Sign up)
            </button>
          </div>
        ) : null}

        {/* Active Logged-in User Profile View */}
        {currentUser ? (
          <div className="auth-profile-card" data-testid="auth-profile-view">
            <div className="auth-profile-header">
              <div className="auth-avatar" style={{ backgroundColor: currentUser.avatarColor || "#10b981" }}>
                {currentUser.initials}
              </div>
              <div>
                <div className="auth-profile-name">
                  <strong>{currentUser.name}</strong>
                  <span className="status-pill status-pill-success">
                    <ShieldCheck size={12} /> Active
                  </span>
                </div>
                <p className="auth-profile-role">{currentUser.role} · {currentUser.agency}</p>
                <p className="auth-profile-email mono">{currentUser.email}</p>
              </div>
            </div>

            <div className="auth-clearance-meta">
              <div>
                <small>Clearance Status</small>
                <strong>{currentUser.clearance || "Level 3 · Verified Access"}</strong>
              </div>
              <div>
                <small>Session Integrity</small>
                <strong className="mono" style={{ color: "#10b981" }}>TLS 1.3 · Verified</strong>
              </div>
            </div>

            <div className="auth-preset-title" style={{ marginTop: 20 }}>
              <span>Switch Active Demo Perspective:</span>
            </div>
            <div className="auth-presets-grid">
              {PRESET_OFFICERS.map((officer) => (
                <button
                  key={officer.id}
                  type="button"
                  className={`auth-preset-btn ${currentUser.email === officer.email ? "is-current" : ""}`}
                  onClick={() => handleQuickLogin(officer)}
                  data-testid={`switch-role-${officer.id}`}
                >
                  <div className="auth-preset-icon" style={{ backgroundColor: officer.avatarColor }}>
                    {officer.initials}
                  </div>
                  <div className="auth-preset-info">
                    <strong>{officer.name}</strong>
                    <small>{officer.badge} · {officer.role}</small>
                  </div>
                  {currentUser.email === officer.email ? <Check size={14} color="#10b981" /> : null}
                </button>
              ))}
            </div>

            <div className="modal-actions" style={{ marginTop: 24 }}>
              <button
                type="button"
                className="button button-outline"
                onClick={handleSignOutClick}
                data-testid="auth-signout-button"
              >
                <LogOut size={15} /> Sign out
              </button>
              <button
                type="button"
                className="button button-dark"
                onClick={onClose}
                data-testid="auth-done-button"
              >
                Close dialog
              </button>
            </div>
          </div>
        ) : tab === "signin" ? (
          /* Sign In Form */
          <div>
            <p className="modal-copy">
              Official single sign-on (Gov SSO) for MoSPI officers, DGCA analysts, and accredited economic researchers.
            </p>

            {/* 1-Click Fast Presets */}
            <div className="auth-presets-section">
              <p className="eyebrow" style={{ marginBottom: 8 }}>Fast 1-Click Authorized Presets:</p>
              <div className="auth-presets-grid">
                {PRESET_OFFICERS.map((officer) => (
                  <button
                    key={officer.id}
                    type="button"
                    className="auth-preset-btn"
                    onClick={() => handleQuickLogin(officer)}
                    data-testid={`quick-login-${officer.id}`}
                  >
                    <div className="auth-preset-icon" style={{ backgroundColor: officer.avatarColor }}>
                      {officer.initials}
                    </div>
                    <div className="auth-preset-info">
                      <strong>{officer.name}</strong>
                      <small>{officer.agency}</small>
                    </div>
                    <ArrowRight size={14} className="auth-preset-arrow" />
                  </button>
                ))}
              </div>
            </div>

            <div className="auth-divider">
              <span>Or sign in with custom credentials</span>
            </div>

            <form onSubmit={handleCustomSignIn}>
              <label className="modal-field">
                Government Email / Institutional SSO ID
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@mospi.gov.in"
                  data-testid="sign-in-email-input"
                  required
                />
              </label>
              <label className="modal-field">
                Security PIN / Master Token
                <input
                  type="password"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  data-testid="sign-in-password-input"
                  required
                />
              </label>

              <button
                type="submit"
                className="button button-dark modal-submit"
                data-testid="sign-in-submit-button"
              >
                <Lock size={15} /> Sign in with Gov SSO <ArrowRight size={15} />
              </button>
            </form>
          </div>
        ) : (
          /* Sign Up Form */
          <div>
            <p className="modal-copy">
              Request credentials for the MoSPI Real-Time Airfare CPI Ingestion &amp; Econometric Augmentation Platform.
            </p>

            <form onSubmit={handleSignUp}>
              <label className="modal-field">
                Full Name
                <input
                  type="text"
                  value={signupName}
                  onChange={(e) => setSignupName(e.target.value)}
                  placeholder="e.g. Dr. Rajeshwari Patel"
                  data-testid="signup-name-input"
                  required
                />
              </label>

              <label className="modal-field">
                Official / Institutional Email
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="r.patel@mospi.gov.in or university.edu"
                  data-testid="signup-email-input"
                  required
                />
              </label>

              <div className="modal-grid-2">
                <label className="modal-field">
                  Affiliated Ministry / Institution
                  <select
                    value={signupAgency}
                    onChange={(e) => setSignupAgency(e.target.value)}
                    data-testid="signup-agency-select"
                  >
                    <option value="Ministry of Statistics & PI (MoSPI)">MoSPI (Statistics Dept)</option>
                    <option value="Directorate General of Civil Aviation (DGCA)">DGCA (Civil Aviation)</option>
                    <option value="Reserve Bank of India (RBI)">Reserve Bank of India (RBI)</option>
                    <option value="NITI Aayog">NITI Aayog</option>
                    <option value="Ministry of Civil Aviation (MoCA)">Ministry of Civil Aviation</option>
                    <option value="Academic & Policy Research Institute">Academic / Policy Research</option>
                  </select>
                </label>

                <label className="modal-field">
                  Requested Clearance Level
                  <select
                    value={signupClearance}
                    onChange={(e) => setSignupClearance(e.target.value)}
                    data-testid="signup-clearance-select"
                  >
                    <option value="Level 1 · Public Research Read">Level 1 · Research Read Access</option>
                    <option value="Level 2 · Statistical Contributor">Level 2 · Statistical Contributor</option>
                    <option value="Level 3 · Full Corridor Telemetry">Level 3 · Full Corridor Telemetry</option>
                    <option value="Level 4 · National CPI Authority">Level 4 · National CPI Authority</option>
                  </select>
                </label>
              </div>

              <label className="modal-field">
                Create Security PIN (4–8 digits)
                <input
                  type="password"
                  value={signupPin}
                  onChange={(e) => setSignupPin(e.target.value)}
                  placeholder="••••••••"
                  data-testid="signup-pin-input"
                  required
                />
              </label>

              <button
                type="submit"
                className="button button-dark modal-submit"
                data-testid="signup-submit-button"
              >
                <UserCheck size={15} /> Request &amp; Activate Clearance <ArrowRight size={15} />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
