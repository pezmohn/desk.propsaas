import type {
  AuthClient,
  AuthRole,
  AuthUser,
  ForgotPasswordInput,
  LoginInput,
  ResetPasswordInput,
} from "./authTypes";

const localSessionKey = "desk-propsaas.local-auth-user";

const authMode = import.meta.env.VITE_AUTH_MODE || "local";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
const apiEndpoints = {
  me: import.meta.env.VITE_AUTH_ME_PATH,
  login: import.meta.env.VITE_AUTH_LOGIN_PATH,
  logout: import.meta.env.VITE_AUTH_LOGOUT_PATH,
  forgotPassword: import.meta.env.VITE_AUTH_FORGOT_PASSWORD_PATH,
  resetPassword: import.meta.env.VITE_AUTH_RESET_PASSWORD_PATH,
};

export const authClient: AuthClient = authMode === "api" ? createApiAuthClient() : createLocalAuthClient();

function createApiAuthClient(): AuthClient {
  return {
    getCurrentUser: () => request<AuthUser | null>(requireApiEndpoint("me"), { method: "GET" }),
    login: (input) => request<AuthUser>(requireApiEndpoint("login"), { method: "POST", body: input }),
    logout: () => request<void>(requireApiEndpoint("logout"), { method: "POST" }),
    forgotPassword: (input) =>
      request<void>(requireApiEndpoint("forgotPassword"), { method: "POST", body: input }),
    resetPassword: (input) =>
      request<void>(requireApiEndpoint("resetPassword"), { method: "POST", body: input }),
  };
}

function createLocalAuthClient(): AuthClient {
  return {
    async getCurrentUser() {
      const raw = window.localStorage.getItem(localSessionKey);
      return raw ? (JSON.parse(raw) as AuthUser) : null;
    },

    async login(input: LoginInput) {
      if (!input.email.trim() || !input.password) {
        throw new Error("Email and password are required.");
      }

      const user: AuthUser = {
        id: "local-dev-user",
        email: input.email.trim(),
        displayName: input.email.split("@")[0],
        role: localRole(),
      };
      window.localStorage.setItem(localSessionKey, JSON.stringify(user));
      return user;
    },

    async logout() {
      window.localStorage.removeItem(localSessionKey);
    },

    async forgotPassword(input: ForgotPasswordInput) {
      if (!input.email.trim()) {
        throw new Error("Email is required.");
      }
    },

    async resetPassword(input: ResetPasswordInput) {
      if (!input.token.trim() || !input.password) {
        throw new Error("Reset token and new password are required.");
      }
    },
  };
}

async function request<T>(path: string, options: { method: string; body?: unknown }): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method,
    credentials: "include",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401) {
    return null as T;
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Auth request failed with ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function localRole(): AuthRole {
  return import.meta.env.VITE_LOCAL_AUTH_ROLE === "admin" ? "admin" : "user";
}

function requireApiEndpoint(endpoint: keyof typeof apiEndpoints): string {
  const path = apiEndpoints[endpoint];
  if (!path) {
    throw new Error(`VITE_AUTH_MODE=api requires VITE_AUTH_${toEnvName(endpoint)}_PATH.`);
  }

  return path;
}

function toEnvName(endpoint: keyof typeof apiEndpoints): string {
  return endpoint.replace(/[A-Z]/g, (letter) => `_${letter}`).toUpperCase();
}
