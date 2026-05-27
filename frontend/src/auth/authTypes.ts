export type AuthRole = "user" | "admin";

export type AuthUser = {
  id: string;
  email: string;
  displayName?: string;
  role: AuthRole;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type ForgotPasswordInput = {
  email: string;
};

export type ResetPasswordInput = {
  token: string;
  password: string;
};

export type AuthClient = {
  getCurrentUser(): Promise<AuthUser | null>;
  login(input: LoginInput): Promise<AuthUser>;
  logout(): Promise<void>;
  forgotPassword(input: ForgotPasswordInput): Promise<void>;
  resetPassword(input: ResetPasswordInput): Promise<void>;
};
