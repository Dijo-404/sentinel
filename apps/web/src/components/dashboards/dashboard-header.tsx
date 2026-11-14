import type { ReactNode } from "react";

type Props = {
  title: string;
  description: string;
  displayName: string;
  workspace: string;
  children?: ReactNode;
};

/** Page heading for portal dashboards: who is signed in and which workspace. */
export function DashboardHeader({
  title,
  description,
  displayName,
  workspace,
  children,
}: Props) {
  return (
    <header className="dash-header">
      <div className="dash-header__text">
        <p className="dash-header__greeting">Welcome back, {displayName}</p>
        <h1>{title}</h1>
        <p className="dash-header__desc">{description}</p>
      </div>
      <span className="dash-header__workspace">{workspace}</span>
      {children ? <div className="dash-header__extra">{children}</div> : null}
    </header>
  );
}
