import { useState } from "react";
import { useAuth } from "../auth/AuthContext";

export function AuthBar() {
  const { ready, user, firebaseConfigured, signInWithEmail, signOutUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  if (!ready) {
    return <span className="auth-bar__status">Auth…</span>;
  }

  if (!firebaseConfigured) {
    return (
      <span className="auth-bar__warn" title="Set VITE_FIREBASE_* env vars">
        Firebase not configured
      </span>
    );
  }

  if (user) {
    return (
      <div className="auth-bar auth-bar--signed-in">
        <span className="auth-bar__user" title={user.uid}>
          {user.email ?? user.uid.slice(0, 8)}
        </span>
        <button
          type="button"
          className="toolbar__btn"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            void signOutUser().finally(() => setBusy(false));
          }}
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <form
      className="auth-bar"
      onSubmit={(e) => {
        e.preventDefault();
        setLocalError(null);
        setBusy(true);
        void signInWithEmail(email, password)
          .catch((err: unknown) => {
            setLocalError(err instanceof Error ? err.message : "Sign-in failed");
          })
          .finally(() => setBusy(false));
      }}
    >
      {localError ? <span className="auth-bar__error">{localError}</span> : null}
      <input
        className="auth-bar__input"
        type="email"
        name="email"
        autoComplete="username"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <input
        className="auth-bar__input"
        type="password"
        name="password"
        autoComplete="current-password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit" className="toolbar__btn toolbar__btn--primary" disabled={busy}>
        Sign in
      </button>
    </form>
  );
}
