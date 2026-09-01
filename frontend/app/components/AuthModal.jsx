"use client";

import { useState } from "react";
import { ArrowRight, Check, LogOut, ShieldCheck, User, UserCheck, UserPlus, X } from "lucide-react";

/**
 * DEMO PERSONAS — NOT AUTHENTICATION
 *
 * These are illustrative role presets used to preview how the dashboard would look
 * for different user types. They are NOT credentials and grant nothing: this is a
 * client-side view preference stored in localStorage, with no server-side session,
 * no authorization, and no access control behind it.
 *
 * Previously this list contained invented named individuals with @mospi.gov.in,
 * @dgca.gov.in and @rbi.org.in addresses and clearance labels such as
 * "Level 4 · Full CPI Authority". That impersonated real institutions and implied
 * an authorization model that does not exist, so the personas are now generic and
 * explicitly unprivileged. See AUDIT.md C3.
 */
export const PRESET_OFFICERS = [
  {
    id: "demo-statistician",
    name: "Demo Statistician",
    email: "statistician@example.invalid",
    agency: "Demo persona · statistical analysis view",
    role: "Statistical Analysis (demo view)",
    clearance: "Demo only · no privileges granted",
    badge: "Demo",
    initials: "DS",
    avatarColor: "#10b981",
  },
  {
    id: "demo-aviation-analyst",
    name: "Demo Aviation Analyst",
    email: "aviation@example.invalid",
    agency: "Demo persona · route and yield view",
    role: "Route & Yield Analysis (demo view)",
    clearance: "Demo only · no privileges granted",
    badge: "Demo",
    initials: "DA",
    avatarColor: "#38bdf8",
  },
  {
    id: "demo-economist",
    name: "Demo Economist",
    email: "economist@example.invalid",
    agency: "Demo persona · macro inflation view",
    role: "Macro Inflation Research (demo view)",
    clearance: "Demo only · no privileges granted",
    badge: "Demo",
    initials: "DE",
    avatarColor: "#a78bfa",
  },
];

export const AUTH_STORAGE_KEY = "airfare-cpi-user-session-v1";

export default function AuthModal({ isOpen, onClose, currentUser, onLogin, onLogout, onNotify }) {
  const [tab, setTab] = useState("signin"); // 'signin' | 'signup' | 'profile'
  const [email, setEmail] = useState("");
  // No password/PIN field: this flow performs no credential verification, so
  // collecting a secret would falsely imply that one is checked.

  // Sign up state
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupAgency, setSignupAgency] = useState("Demo persona");
  const [signupClearance, setSignupClearance] = useState("Demo only · no privileges granted");

  if (!isOpen) return null;

  const handleQuickLogin = (officer) => {
    onLogin(officer);
    onClose();
    if (onNotify) onNotify(`Viewing as ${officer.name} (demo persona — no privileges granted).`);
  };

  const handleCustomSignIn = (e) => {
    e.preventDefault();
    if (!email) {
      if (onNotify) onNotify("Please enter a valid government or research email ID.", "warning");
      return;
    }

    const matched = PRESET_OFFICERS.find((o) => o.email.toLowerCase() === email.toLowerCase());
    // Never infer an institution from an email domain — typing "@mospi.gov.in"
    // must not produce a session labelled as Government of India.
    const userSession = matched || {
      id: `persona-${Date.now()}`,
      name: email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      email,
      agency: "Demo persona · self-selected",
      role: "Dashboard viewer (demo)",
      clearance: "Demo only · no privileges granted",
      badge: "Demo",
      initials: email.slice(0, 2).toUpperCase(),
      avatarColor: "#10b981",
    };

    onLogin(userSession);
    onClose();
    if (onNotify) onNotify(`Demo persona set to ${userSession.name}. No privileges granted.`);
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
      id: `persona-${Date.now()}`,
      name: signupName.trim(),
      email: signupEmail.trim(),
      agency: signupAgency || "Demo persona · self-selected",
      role: "Dashboard viewer (demo)",
      clearance: signupClearance,
      badge: "Demo",
      initials,
      avatarColor: "#10b981",
    };

    onLogin(newUser);
    onClose();
    if (onNotify) onNotify(`Demo persona created for ${newUser.name}. No privileges granted.`);
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
              {currentUser ? "Active demo persona" : "Demo persona selection"}
            </p>
            <h3>
              {currentUser ? "Persona profile" : tab === "signin" ? "Choose a demo persona" : "Create a custom persona"}
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
              <User size={14} /> Choose persona
            </button>
            <button
              type="button"
              className={tab === "signup" ? "is-active" : ""}
              onClick={() => setTab("signup")}
              data-testid="auth-tab-signup"
            >
              <UserPlus size={14} /> Custom persona
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
                <small>Access level</small>
                <strong>{currentUser.clearance || "Demo only · no privileges granted"}</strong>
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
            <div className="auth-demo-notice" role="note">
              <strong>Demo personas — not a login.</strong> This prototype has no authentication and no
              access control. Selecting a persona only changes labels shown in this browser; it grants no
              permissions and sends nothing to a server. All dashboard data is publicly visible either way.
            </div>

            {/* Persona presets */}
            <div className="auth-presets-section">
              <p className="eyebrow" style={{ marginBottom: 8 }}>Preview the dashboard as:</p>
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
              <span>Or set a custom display name</span>
            </div>

            <form onSubmit={handleCustomSignIn}>
              <label className="modal-field">
                Display email (local only)
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.invalid"
                  data-testid="sign-in-email-input"
                  required
                />
              </label>
              {/* No password field: nothing verifies a credential here, and asking for
                  one would imply a security control that does not exist. */}

              <button
                type="submit"
                className="button button-dark modal-submit"
                data-testid="sign-in-submit-button"
              >
                <User size={15} /> Use this persona <ArrowRight size={15} />
              </button>
            </form>
          </div>
        ) : (
          /* Sign Up Form */
          <div>
            <p className="modal-copy">
              Create a local display persona for the Airfare CPI dashboard. This is stored only in your
              browser and grants no permissions.
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
                Display email (local only)
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="you@example.invalid"
                  data-testid="signup-email-input"
                  required
                />
              </label>

              {/* Institution and clearance selectors removed. A client-side form cannot
                  grant a clearance level, and offering "Level 4 · National CPI Authority"
                  implied an authorization model that does not exist. */}
              <label className="modal-field">
                Description (optional, cosmetic)
                <input
                  type="text"
                  value={signupAgency}
                  onChange={(e) => setSignupAgency(e.target.value)}
                  placeholder="e.g. Demo persona · analyst view"
                  data-testid="signup-agency-input"
                />
              </label>

              <button
                type="submit"
                className="button button-dark modal-submit"
                data-testid="signup-submit-button"
              >
                <UserCheck size={15} /> Create demo persona <ArrowRight size={15} />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
