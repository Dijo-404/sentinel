/**
 * Local identity.v1 double for fixture-mode portal auth.
 * Seeded synthetic users only. Never production credentials.
 */

export type PortalRole =
  | "customer"
  | "merchant"
  | "operator"
  | "supervisor"
  | "risk"
  | "admin";

export type WorkspaceAssignment = {
  assignment_id: string;
  role: PortalRole;
  tenant_id: string;
  label: string;
  scope?: Record<string, string>;
};

export type IdentityUser = {
  user_id: string;
  email: string;
  display_name: string;
  /** Fixture-only plaintext credential. */
  password: string;
  account_status: "ACTIVE" | "PENDING" | "SUSPENDED";
  account_class: "customer" | "staff";
  assignments: WorkspaceAssignment[];
};

export type SessionRecord = {
  session_id: string;
  user_id: string;
  active_assignment_id: string;
  issued_at: string;
  expires_at: string;
  revoked: boolean;
};

export type Invitation = {
  invitation_id: string;
  work_email: string;
  display_name: string;
  tenant_id: string;
  role: Exclude<PortalRole, "customer">;
  scope: Record<string, string>;
  status: "PENDING" | "ACCEPTED" | "REVOKED" | "EXPIRED";
  created_by: string;
  expires_at: string;
};

export type LoginResult =
  | { ok: true; session: SessionRecord; user: IdentityUser; workspaces: WorkspaceAssignment[] }
  | { ok: false; code: "INVALID_CREDENTIALS" | "SUSPENDED" | "PENDING" };

export type RegisterResult =
  | { ok: true; session: SessionRecord; user: IdentityUser }
  | { ok: false; code: "INVALID_INPUT" | "ALREADY_EXISTS" | "PRIVILEGED_FIELDS_REJECTED" };

export type InviteResult =
  | { ok: true; invitation: Invitation }
  | {
      ok: false;
      code:
        | "FORBIDDEN"
        | "INVALID_ROLE"
        | "DUPLICATE"
        | "INVALID_INPUT";
      message: string;
    };

export type StubIdentity = {
  login(email: string, password: string): LoginResult;
  registerCustomer(input: {
    email: string;
    display_name: string;
    password: string;
    language?: string;
    /** Rejected if present — server derives customer role. */
    roles?: unknown;
    tenant_id?: unknown;
    subject_refs?: unknown;
  }): RegisterResult;
  resolveSession(sessionId: string): {
    session: SessionRecord;
    user: IdentityUser;
    assignment: WorkspaceAssignment;
  } | null;
  /** Bind session to an assignment the user already holds. */
  selectAssignment(sessionId: string, assignmentId: string): SessionRecord | null;
  logout(sessionId: string): void;
  listStaffUsers(actorUserId: string): IdentityUser[] | { error: "FORBIDDEN" };
  listInvitations(actorUserId: string): Invitation[] | { error: "FORBIDDEN" };
  inviteStaff(
    actorUserId: string,
    input: {
      display_name: string;
      work_email: string;
      tenant_id: string;
      role_id: string;
      scope?: Record<string, string>;
      reason?: string;
      idempotency_key?: string;
    },
  ): InviteResult;
  acceptInvitation(input: {
    token: string;
    email: string;
    password: string;
    display_name?: string;
  }):
    | {
        ok: true;
        session: SessionRecord;
        user: IdentityUser;
        assignment: WorkspaceAssignment;
      }
    | { ok: false; code: string; message: string };
  assignableRoles(): Array<{ role_id: Exclude<PortalRole, "customer">; label: string }>;
  reset(): void;
};

const STAFF_ROLES: Exclude<PortalRole, "customer">[] = [
  "merchant",
  "operator",
  "supervisor",
  "risk",
  "admin",
];

const ROLE_LABELS: Record<PortalRole, string> = {
  customer: "Customer",
  merchant: "Merchant",
  operator: "Support Operator",
  supervisor: "Supervisor",
  risk: "Risk Officer",
  admin: "Platform Admin",
};

function seedUsers(): IdentityUser[] {
  return [
    {
      user_id: "user-customer-1",
      email: "customer@example.test",
      display_name: "Demo Customer",
      password: "demo-customer",
      account_status: "ACTIVE",
      account_class: "customer",
      assignments: [
        {
          assignment_id: "asg-customer-1",
          role: "customer",
          tenant_id: "tenant-demo",
          label: "Customer workspace",
        },
      ],
    },
    {
      user_id: "user-merchant-1",
      email: "merchant@example.test",
      display_name: "Demo Merchant",
      password: "demo-merchant",
      account_status: "ACTIVE",
      account_class: "staff",
      assignments: [
        {
          assignment_id: "asg-merchant-1",
          role: "merchant",
          tenant_id: "tenant-demo",
          label: "Merchant Acme",
          scope: { merchant_id: "merchant-acme" },
        },
      ],
    },
    {
      user_id: "user-operator-1",
      email: "operator@example.test",
      display_name: "Demo Operator",
      password: "demo-operator",
      account_status: "ACTIVE",
      account_class: "staff",
      assignments: [
        {
          assignment_id: "asg-operator-1",
          role: "operator",
          tenant_id: "tenant-demo",
          label: "Payments support",
          scope: { team_id: "payments-support" },
        },
      ],
    },
    {
      user_id: "user-supervisor-1",
      email: "supervisor@example.test",
      display_name: "Demo Supervisor",
      password: "demo-supervisor",
      account_status: "ACTIVE",
      account_class: "staff",
      assignments: [
        {
          assignment_id: "asg-supervisor-1",
          role: "supervisor",
          tenant_id: "tenant-demo",
          label: "Approval desk",
        },
      ],
    },
    {
      user_id: "user-risk-1",
      email: "risk@example.test",
      display_name: "Demo Risk Officer",
      password: "demo-risk",
      account_status: "ACTIVE",
      account_class: "staff",
      assignments: [
        {
          assignment_id: "asg-risk-1",
          role: "risk",
          tenant_id: "tenant-demo",
          label: "Fraud queue",
        },
      ],
    },
    {
      user_id: "user-admin-1",
      email: "admin@example.test",
      display_name: "Demo Admin",
      password: "demo-admin",
      account_status: "ACTIVE",
      account_class: "staff",
      assignments: [
        {
          assignment_id: "asg-admin-1",
          role: "admin",
          tenant_id: "tenant-demo",
          label: "Platform administration",
        },
      ],
    },
    {
      user_id: "user-dual-1",
      email: "dual@example.test",
      display_name: "Demo Dual Role",
      password: "demo-dual",
      account_status: "ACTIVE",
      account_class: "staff",
      assignments: [
        {
          assignment_id: "asg-dual-operator",
          role: "operator",
          tenant_id: "tenant-demo",
          label: "Payments support",
        },
        {
          assignment_id: "asg-dual-supervisor",
          role: "supervisor",
          tenant_id: "tenant-demo",
          label: "Approval desk",
        },
      ],
    },
  ];
}

function newId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function isoPlusHours(hours: number): string {
  return new Date(Date.now() + hours * 3600_000).toISOString();
}

export function createIdentityStub(): StubIdentity {
  let users = seedUsers();
  const sessions = new Map<string, SessionRecord>();
  const invitations: Invitation[] = [];
  const inviteIdempotency = new Map<string, string>();
  /** Fixture delivery secrets: raw token → invitation_id */
  const inviteTokens = new Map<string, string>();

  function findAdmin(actorUserId: string): IdentityUser | null {
    const user = users.find((u) => u.user_id === actorUserId);
    if (!user || user.account_status !== "ACTIVE") return null;
    if (!user.assignments.some((a) => a.role === "admin")) return null;
    return user;
  }

  function issueSession(user: IdentityUser, assignment: WorkspaceAssignment): SessionRecord {
    const session: SessionRecord = {
      session_id: newId("sess"),
      user_id: user.user_id,
      active_assignment_id: assignment.assignment_id,
      issued_at: new Date().toISOString(),
      expires_at: isoPlusHours(8),
      revoked: false,
    };
    sessions.set(session.session_id, session);
    return session;
  }

  return {
    login(email, password) {
      const normalized = email.trim().toLowerCase();
      const user = users.find((u) => u.email === normalized);
      if (!user || user.password !== password) {
        return { ok: false, code: "INVALID_CREDENTIALS" };
      }
      if (user.account_status === "SUSPENDED") {
        return { ok: false, code: "SUSPENDED" };
      }
      if (user.account_status === "PENDING") {
        return { ok: false, code: "PENDING" };
      }
      const assignment = user.assignments[0];
      if (!assignment) {
        return { ok: false, code: "INVALID_CREDENTIALS" };
      }
      const session = issueSession(user, assignment);
      return {
        ok: true,
        session,
        user,
        workspaces: user.assignments,
      };
    },

    registerCustomer(input) {
      if (
        input.roles !== undefined ||
        input.tenant_id !== undefined ||
        input.subject_refs !== undefined
      ) {
        return { ok: false, code: "PRIVILEGED_FIELDS_REJECTED" };
      }
      const email = input.email?.trim().toLowerCase() ?? "";
      const display_name = input.display_name?.trim() ?? "";
      const password = input.password ?? "";
      if (!email || !display_name || password.length < 8) {
        return { ok: false, code: "INVALID_INPUT" };
      }
      if (users.some((u) => u.email === email)) {
        return { ok: false, code: "ALREADY_EXISTS" };
      }
      const assignment: WorkspaceAssignment = {
        assignment_id: newId("asg"),
        role: "customer",
        tenant_id: "tenant-demo",
        label: "Customer workspace",
      };
      const user: IdentityUser = {
        user_id: newId("user"),
        email,
        display_name,
        password,
        account_status: "ACTIVE",
        account_class: "customer",
        assignments: [assignment],
      };
      users = [...users, user];
      const session = issueSession(user, assignment);
      return { ok: true, session, user };
    },

    resolveSession(sessionId) {
      const session = sessions.get(sessionId);
      if (!session || session.revoked) return null;
      if (Date.parse(session.expires_at) < Date.now()) return null;
      const user = users.find((u) => u.user_id === session.user_id);
      if (!user || user.account_status !== "ACTIVE") return null;
      const assignment = user.assignments.find(
        (a) => a.assignment_id === session.active_assignment_id,
      );
      if (!assignment) return null;
      return { session, user, assignment };
    },

    selectAssignment(sessionId, assignmentId) {
      const session = sessions.get(sessionId);
      if (!session || session.revoked) return null;
      const user = users.find((u) => u.user_id === session.user_id);
      if (!user || user.account_status !== "ACTIVE") return null;
      const assignment = user.assignments.find(
        (a) => a.assignment_id === assignmentId,
      );
      if (!assignment) return null;
      const next: SessionRecord = {
        ...session,
        active_assignment_id: assignment.assignment_id,
      };
      sessions.set(sessionId, next);
      return next;
    },

    logout(sessionId) {
      const session = sessions.get(sessionId);
      if (session) {
        sessions.set(sessionId, { ...session, revoked: true });
      }
    },

    listStaffUsers(actorUserId) {
      if (!findAdmin(actorUserId)) return { error: "FORBIDDEN" };
      return users.filter((u) => u.account_class === "staff");
    },

    listInvitations(actorUserId) {
      if (!findAdmin(actorUserId)) return { error: "FORBIDDEN" };
      return [...invitations];
    },

    inviteStaff(actorUserId, input) {
      const admin = findAdmin(actorUserId);
      if (!admin) {
        return { ok: false, code: "FORBIDDEN", message: "Admin assignment required" };
      }
      const role_id = input.role_id?.trim();
      if (!role_id || role_id === "customer") {
        return {
          ok: false,
          code: "INVALID_ROLE",
          message: "Customer role cannot be invited via staff invitation",
        };
      }
      if (!STAFF_ROLES.includes(role_id as Exclude<PortalRole, "customer">)) {
        return {
          ok: false,
          code: "INVALID_ROLE",
          message: `Unknown or non-assignable role: ${role_id}`,
        };
      }
      const work_email = input.work_email?.trim().toLowerCase() ?? "";
      const display_name = input.display_name?.trim() ?? "";
      const tenant_id = input.tenant_id?.trim() ?? "";
      if (!work_email || !display_name || !tenant_id) {
        return { ok: false, code: "INVALID_INPUT", message: "Missing required fields" };
      }
      if (input.idempotency_key) {
        const existingId = inviteIdempotency.get(input.idempotency_key);
        if (existingId) {
          const existing = invitations.find((i) => i.invitation_id === existingId);
          if (existing) return { ok: true, invitation: existing };
        }
      }
      if (
        invitations.some(
          (i) =>
            i.work_email === work_email &&
            i.role === role_id &&
            i.status === "PENDING",
        )
      ) {
        return {
          ok: false,
          code: "DUPLICATE",
          message: "Pending invitation already exists for this email and role",
        };
      }
      const invitation: Invitation = {
        invitation_id: newId("inv"),
        work_email,
        display_name,
        tenant_id,
        role: role_id as Exclude<PortalRole, "customer">,
        scope: input.scope ?? {},
        status: "PENDING",
        created_by: admin.user_id,
        expires_at: isoPlusHours(72),
      };
      invitations.push(invitation);
      // Fixture: invitation_id doubles as delivery token for accept tests.
      inviteTokens.set(invitation.invitation_id, invitation.invitation_id);
      if (input.idempotency_key) {
        inviteIdempotency.set(input.idempotency_key, invitation.invitation_id);
      }
      return { ok: true, invitation };
    },

    acceptInvitation(input) {
      const token = input.token?.trim() ?? "";
      const email = input.email?.trim().toLowerCase() ?? "";
      const password = input.password ?? "";
      const invitationId = inviteTokens.get(token);
      if (!invitationId) {
        return { ok: false, code: "FORBIDDEN", message: "Invitation denied" };
      }
      const invitation = invitations.find((i) => i.invitation_id === invitationId);
      if (!invitation || invitation.status !== "PENDING") {
        return { ok: false, code: "FORBIDDEN", message: "Invitation denied" };
      }
      if (Date.parse(invitation.expires_at) < Date.now()) {
        invitation.status = "EXPIRED";
        return { ok: false, code: "FORBIDDEN", message: "Invitation expired" };
      }
      if (email !== invitation.work_email) {
        return { ok: false, code: "FORBIDDEN", message: "Invitation email mismatch" };
      }
      if (password.length < 8) {
        return { ok: false, code: "INVALID_INPUT", message: "Password too short" };
      }
      let user = users.find((u) => u.email === email);
      if (user?.account_class === "customer") {
        return {
          ok: false,
          code: "FORBIDDEN",
          message: "Customer accounts cannot accept staff invitations",
        };
      }
      const assignment: WorkspaceAssignment = {
        assignment_id: newId("asg"),
        role: invitation.role,
        tenant_id: invitation.tenant_id,
        label: `${ROLE_LABELS[invitation.role]} workspace`,
        scope: invitation.scope,
      };
      if (!user) {
        user = {
          user_id: newId("user"),
          email,
          display_name:
            input.display_name?.trim() || invitation.display_name,
          password,
          account_status: "ACTIVE",
          account_class: "staff",
          assignments: [assignment],
        };
        users = [...users, user];
      } else {
        if (user.password !== password) {
          return { ok: false, code: "UNAUTHORIZED", message: "Invalid credentials" };
        }
        user.assignments = [...user.assignments, assignment];
      }
      invitation.status = "ACCEPTED";
      inviteTokens.delete(token);
      const session = issueSession(user, assignment);
      return { ok: true, session, user, assignment };
    },

    assignableRoles() {
      return STAFF_ROLES.map((role_id) => ({
        role_id,
        label: ROLE_LABELS[role_id],
      }));
    },

    reset() {
      users = seedUsers();
      sessions.clear();
      invitations.length = 0;
      inviteIdempotency.clear();
      inviteTokens.clear();
    },
  };
}

/** Process-wide fixture identity store (Next server + Vitest). */
let sharedStub: StubIdentity | null = null;

export function getSharedIdentityStub(): StubIdentity {
  if (!sharedStub) {
    sharedStub = createIdentityStub();
  }
  return sharedStub;
}

export function resetSharedIdentityStub(): void {
  getSharedIdentityStub().reset();
}

export { ROLE_LABELS, STAFF_ROLES };
