import { FormEvent, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthProvider";

type PageProps = {
  navigate(to: string, options?: { replace?: boolean }): void;
  search: string;
};

export function ResetPasswordPage({ navigate, search }: PageProps) {
  const { resetPassword } = useAuth();
  const resetToken = useMemo(() => new URLSearchParams(search).get("token") || "", [search]);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await resetPassword({ token: resetToken, password });
      setIsComplete(true);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Password reset failed.");
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="reset-title">
        <p className="eyebrow">Account access</p>
        <h1 id="reset-title">Choose a new password</h1>

        {!resetToken ? (
          <p className="form-error">The reset token is missing.</p>
        ) : isComplete ? (
          <div className="notice">
            <strong>Password updated.</strong>
            <span>You can sign in with the new password when backend auth is connected.</span>
          </div>
        ) : (
          <form className="form-stack" onSubmit={handleSubmit}>
            <label>
              New password
              <input
                autoComplete="new-password"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>

            {error ? <p className="form-error">{error}</p> : null}

            <button className="primary-button" type="submit">
              Save password
            </button>
          </form>
        )}

        <button className="link-button" type="button" onClick={() => navigate("/login")}>
          Back to login
        </button>
      </section>
    </main>
  );
}
