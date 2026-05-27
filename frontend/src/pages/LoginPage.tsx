import { FormEvent, useState } from "react";
import { useAuth } from "../auth/AuthProvider";

type PageProps = {
  navigate(to: string, options?: { replace?: boolean }): void;
  search: string;
};

export function LoginPage({ navigate, search }: PageProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      const params = new URLSearchParams(search);
      navigate(params.get("next") || "/dashboard", { replace: true });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="login-title">
        <div className="auth-heading">
          <span className="brand-mark">dp</span>
          <div>
            <p className="eyebrow">desk-propsaas</p>
            <h1 id="login-title">Sign in</h1>
          </div>
        </div>

        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Password
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? <p className="form-error">{error}</p> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <button className="link-button" type="button" onClick={() => navigate("/forgot-password")}>
          Forgot password?
        </button>
      </section>
    </main>
  );
}
