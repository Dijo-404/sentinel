/** Stroke icons keyed by nav label; unknown labels get a neutral dot. */
const PATHS: Record<string, string> = {
  profile: "M20 21v-2a7 7 0 00-14 0v2M12 11a4 4 0 100-8 4 4 0 000 8z",
  notifications: "M6 8a6 6 0 0112 0v7l2 3H4l2-3zM10 21h4",
  exceptions: "M12 8v5M12 17h.01M12 3L2 21h20z",
  disputes: "M12 3l8 4v6c0 4-5 7-8 8-3-1-8-4-8-8V7zM12 8v5M12 16h.01",
  analytics: "M4 20h16M7 16v-5M12 16V4M17 16V8",
  settings: "M4 7h16M4 17h16M8 4v6M16 14v6",
  tenants: "M4 21V4h10v17M14 10h6v11M8 8h2M8 12h2M8 16h2M2 21h20",
  teams:
    "M4 21v-3a5 5 0 0110 0v3M9 11a4 4 0 100-8 4 4 0 000 8zM17 4a4 4 0 010 7M17 14a5 5 0 015 4v3",
  merchants: "M3 10l2-7h14l2 7M3 10a3 3 0 006 0 3 3 0 006 0 3 3 0 006 0M5 13v8h14v-8M10 21v-6h4v6",
  policies: "M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h5",
  security: "M12 3l8 4v6c0 4-5 7-8 8-3-1-8-4-8-8V7zM9 12l2 2 4-4",
  configuration: "M4 7h16M4 17h16M8 4v6M16 14v6",
  integrations: "M8 3v5M16 3v5M5 8h14v4a7 7 0 01-14 0zM12 19v3",
  evaluations: "M9 4h6v3H9zM6 6H4v15h16V6h-2M8 13l2 2 5-5",
  observability: "M2 12h5l3-8 4 16 3-8h5",
  reports: "M5 3h10l4 4v14H5zM14 3v5h5M8 17v-3M12 17v-6M16 17v-4",
  dashboard: "M4 13h6V4H4zM14 20h6V11h-6zM4 20h6v-3H4zM14 7h6V4h-6z",
  transactions: "M4 8h13l-3-3M20 16H7l3 3",
  settlements: "M4 7h16v10H4zM4 11h16M8 15h3",
  refunds: "M9 14L4 9l5-5M4 9h10a6 6 0 010 12h-3",
  report:
    "M12 8v5M12 16.5v.5M10.3 3.9L2.6 17a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z",
  cases: "M4 7h16v12H4zM9 7V5h6v2",
  queue: "M4 6h16M4 12h16M4 18h10",
  escalations: "M12 19V5M5 12l7-7 7 7",
  approvals: "M9 12l2 2 4-4M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z",
  history: "M3 12a9 9 0 109-9 9 9 0 00-6.4 2.6L3 8M3 3v5h5M12 7v5l3 2",
  audit: "M9 4h6v3H9zM6 6h12v15H6zM9 12h6M9 16h4",
  messages: "M4 6h16v10H4zM8 20l4-4h8",
  assistant:
    "M12 3a4 4 0 014 4v2h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v2l-4-2H8a2 2 0 01-2-2v-6a2 2 0 012-2h2V7a4 4 0 014-4z",
  knowledge: "M4 5h7v14H4zM13 5h7v14h-7z",
  activity: "M4 19V9M10 19V5M16 19v-7M22 19V11",
  team: "M16 20v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM21 20v-1a4 4 0 00-3-3.9M16 4.1a3.5 3.5 0 010 6.8",
  holds: "M7 11V8a5 5 0 0110 0v3M5 11h14v10H5z",
  users:
    "M16 20v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM21 20v-1a4 4 0 00-3-3.9M16 4.1a3.5 3.5 0 010 6.8",
  invite:
    "M15 20v-1a4 4 0 00-4-4H6a4 4 0 00-4 4v1M8.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM19 8v6M22 11h-6",
  roles: "M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5",
  center:
    "M12 12m-3 0a3 3 0 106 0 3 3 0 10-6 0M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1",
};

export function NavIcon({ label }: { label: string }) {
  const key = label.toLowerCase().split(" ").pop() ?? "";
  const d = PATHS[key];
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" className="nav-icon">
      {d ? (
        <path
          d={d}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <circle cx="12" cy="12" r="3" fill="currentColor" />
      )}
    </svg>
  );
}
