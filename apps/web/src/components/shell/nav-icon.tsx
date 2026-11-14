/** Stroke icons keyed by nav label; unknown labels get a neutral dot. */
const PATHS: Record<string, string> = {
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
  assistant: "M12 3a4 4 0 014 4v2h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v2l-4-2H8a2 2 0 01-2-2v-6a2 2 0 012-2h2V7a4 4 0 014-4z",
  knowledge: "M4 5h7v14H4zM13 5h7v14h-7z",
  activity: "M4 19V9M10 19V5M16 19v-7M22 19V11",
  team: "M16 20v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM21 20v-1a4 4 0 00-3-3.9M16 4.1a3.5 3.5 0 010 6.8",
  holds: "M7 11V8a5 5 0 0110 0v3M5 11h14v10H5z",
  users:
    "M16 20v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM21 20v-1a4 4 0 00-3-3.9M16 4.1a3.5 3.5 0 010 6.8",
  invite:
    "M15 20v-1a4 4 0 00-4-4H6a4 4 0 00-4 4v1M8.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM19 8v6M22 11h-6",
  roles: "M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5",
};

export function NavIcon({ label }: { label: string }) {
  const key = label.toLowerCase().split(" ").pop() ?? "";
  const d = PATHS[key];
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      aria-hidden="true"
      className="nav-icon"
    >
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
