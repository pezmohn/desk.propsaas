import type {
  AuthClient,
  AuthRole,
  AuthUser,
  ForgotPasswordInput,
  LoginInput,
  ResetPasswordInput,
} from "./authTypes";
import { requestJson } from "../api/apiClient";
import { asRecord, readNullableString, readString } from "../api/normalize";

const localSessionKey = "desk-propsaas.local-auth-user";

const authMode = import.meta.env.VITE_AUTH_MODE || "local";
const apiEndpoints = {
  me: import.meta.env.VITE_AUTH_ME_PATH || import.meta.env.VITE_AUTH_SESSION_PATH || "/api/v1/auth/session",
  login: import.meta.env.VITE_AUTH_LOGIN_PATH || "/api/v1/auth/login",
  logout: import.meta.env.VITE_AUTH_LOGOUT_PATH || "/api/v1/auth/logout",
  forgotPassword: import.meta.env.VITE_AUTH_FORGOT_PASSWORD_PATH,
  resetPassword: import.meta.env.VITE_AUTH_RESET_PASSWORD_PATH,
};

export const authClient: AuthClient = authMode === "api" ? createApiAuthClient() : createLocalAuthClient();

function createApiAuthClient(): AuthClient {
  return {
    async getCurrentUser() {
      const payload = await requestJson(requireApiEndpoint("me"), {
        method: "GET",
        unauthorizedAsNull: true,
      });
      return payload ? normalizeAuthUser(payload) : null;
    },
    async login(input) {
      const payload = await requestJson(requireApiEndpoint("login"), { method: "POST", body: input });
      return normalizeAuthUser(payload);
    },
    async logout() {
      await requestJson(requireApiEndpoint("logout"), { method: "POST" });
    },
    async forgotPassword(input) {
      await requestJson(requireApiEndpoint("forgotPassword"), { method: "POST", body: input });
    },
    async resetPassword(input) {
      await requestJson(requireApiEndpoint("resetPassword"), { method: "POST", body: input });
    },
  };
}

function createLocalAuthClient(): AuthClient {
  return {
    async getCurrentUser() {
      const raw = window.localStorage.getItem(localSessionKey);
      return raw ? normalizeAuthUser(JSON.parse(raw)) : null;
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

function localRole(): AuthRole {
  return import.meta.env.VITE_LOCAL_AUTH_ROLE === "admin" ? "admin" : "user";
}

function normalizeAuthUser(payload: unknown): AuthUser {
  const record = asRecord(payload, "Auth user");
  const role = readString(record, "role", "user");

  return {
    id: readString(record, "id"),
    email: readString(record, "email"),
    displayName: readNullableString(record, "displayName") || undefined,
    role: role === "admin" ? "admin" : "user",
  };
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
