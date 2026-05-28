import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { authClient } from "./authClient";
import type { AuthUser, ForgotPasswordInput, LoginInput, ResetPasswordInput } from "./authTypes";

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  login(input: LoginInput): Promise<void>;
  logout(): Promise<void>;
  forgotPassword(input: ForgotPasswordInput): Promise<void>;
  resetPassword(input: ResetPasswordInput): Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;

    authClient
      .getCurrentUser()
      .then((currentUser) => {
        if (!active) return;
        setUser(currentUser);
        setStatus(currentUser ? "authenticated" : "anonymous");
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        setStatus("anonymous");
      });

    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      async login(input) {
        const loggedInUser = await authClient.login(input);
        if (!loggedInUser?.id || !loggedInUser.email) {
          throw new Error("Login did not return a valid user session.");
        }
        setUser(loggedInUser);
        setStatus("authenticated");
      },
      async logout() {
        await authClient.logout();
        setUser(null);
        setStatus("anonymous");
      },
      forgotPassword: authClient.forgotPassword,
      resetPassword: authClient.resetPassword,
    }),
    [status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
