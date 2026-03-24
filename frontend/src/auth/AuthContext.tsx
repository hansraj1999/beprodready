import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from "firebase/auth";

import { getFirebaseAuth, isFirebaseConfigured } from "../lib/firebase";

export type AuthContextValue = {
  ready: boolean;
  user: User | null;
  firebaseConfigured: boolean;
  /** Firebase ID token for `Authorization: Bearer`, or null if signed out / not configured. */
  getIdToken: () => Promise<string | null>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signOutUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const firebaseConfigured = isFirebaseConfigured();

  useEffect(() => {
    if (!firebaseConfigured) {
      setReady(true);
      return;
    }

    const auth = getFirebaseAuth();
    const unsub = onAuthStateChanged(auth, (next) => {
      setUser(next);
      setReady(true);
    });
    return () => unsub();
  }, [firebaseConfigured]);

  const getIdToken = useCallback(async () => {
    if (!user) return null;
    return user.getIdToken();
  }, [user]);

  const signInWithEmail = useCallback(
    async (email: string, password: string) => {
      if (!firebaseConfigured) {
        throw new Error("Firebase is not configured");
      }
      await signInWithEmailAndPassword(getFirebaseAuth(), email.trim(), password);
    },
    [firebaseConfigured],
  );

  const signOutUser = useCallback(async () => {
    if (!firebaseConfigured) return;
    await signOut(getFirebaseAuth());
  }, [firebaseConfigured]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      user,
      firebaseConfigured,
      getIdToken,
      signInWithEmail,
      signOutUser,
    }),
    [ready, user, firebaseConfigured, getIdToken, signInWithEmail, signOutUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
