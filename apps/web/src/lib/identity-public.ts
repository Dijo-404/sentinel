import type { IdentityUser } from "../../tests/stubs/identity";

/** Profile fields safe to ship to client components — never includes password. */
export type PublicProfileUser = {
  user_id: string;
  email: string;
  display_name: string;
  preferred_language?: string;
  email_verified_at?: string | null;
  account_status: IdentityUser["account_status"];
  account_class: IdentityUser["account_class"];
};

export function toPublicProfileUser(user: IdentityUser | PublicProfileUser): PublicProfileUser {
  return {
    user_id: user.user_id,
    email: user.email,
    display_name: user.display_name,
    preferred_language: user.preferred_language,
    email_verified_at: user.email_verified_at,
    account_status: user.account_status,
    account_class: user.account_class,
  };
}
