import Link from "next/link";
import type { ReactNode } from "react";
import { LogoMark } from "@/components/brand/logo-mark";

/** Shared entry layout for account, recovery, and workspace selection screens. */
export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-story" aria-label="About Sentinel">
        <Link href="/" className="landing-wordmark auth-story__brand">
          <LogoMark inverse size={32} />
          Sentinel
        </Link>
        <div className="auth-story__body">
          <p className="auth-story__category">Payment operations, with clarity</p>
          <h2>
            Every payment issue.
            <br />A clear path forward.
          </h2>
          <p className="auth-story__lead">
            Bring the evidence, the decision, and the outcome into one accountable workspace.
          </p>
          <ol className="auth-story__steps">
            <li>
              <strong>Investigate the evidence</strong>
              <span>Understand what happened to the payment.</span>
            </li>
            <li>
              <strong>Approve the exact action</strong>
              <span>Keep people in control of financial decisions.</span>
            </li>
            <li>
              <strong>Verify the outcome</strong>
              <span>Close the case only when the required checks pass.</span>
            </li>
          </ol>
        </div>
        <p className="auth-story__footer">Pending is not proof of customer credit.</p>
      </section>
      <div className="auth-content">{children}</div>
    </main>
  );
}
