import { FormEvent, useState } from "react";
import { useAuth } from "../auth/AuthProvider";

type PageProps = {
  navigate(to: string, options?: { replace?: boolean }): void;
};

export function ForgotPasswordPage({ navigate }: PageProps) {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await forgotPassword({ email });
      setIsSubmitted(true);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Reset request failed.");
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="forgot-title">
        <p className="eyebrow">Account access</p>
        <h1 id="forgot-title">Reset your password</h1>

        {isSubmitted ? (
          <div className="notice">
            <strong>Request received.</strong>
            <span>If the account exists, the reset flow can continue through the configured backend.</span>
          </div>
        ) : (
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

            {error ? <p className="form-error">{error}</p> : null}

            <button className="primary-button" type="submit">
              Continue
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
