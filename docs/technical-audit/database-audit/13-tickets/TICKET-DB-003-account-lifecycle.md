<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-004, 005, 009, 024. -->

# TICKET-DB-003 — Server-side account lifecycle: effective deactivation, role changes, session revocation, safe reset and activation tokens

## Context
Account management exists in the UI, but only in `localStorage`. The server has no endpoint to edit, deactivate or delete a user, and never checks `users.isActive`.

## Problem
1. A deactivated account (`isActive = false`) can still log in and call the API.
2. "Delete user" and "edit user" (including the role) in `UsersView` only change `localStorage` (`App.tsx:485-493`). The account is untouched on the server, while the UI reports success.
3. Tokens cannot be revoked. Logout is client-side only, and a password change does not invalidate existing sessions.
4. The password-reset token is a JWT signed with the session key. No `get_current_user` checks its `purpose` claim, so it works as a session token. It is stored in clear in `users.resetToken`, and no password policy applies.
5. New accounts get a temporary password returned in the HTTP response. The e-mail is sent after the commit, and a failure is only logged. Nothing forces the password to be changed, and `isVerified` has no effect.
6. Login answers about 12× faster for unknown e-mails (24 ms vs 292 ms median), which enables account enumeration.

## Current Behavior

| Test | Result |
|---|---|
| Login with an `isActive = false` account | **token issued** |
| `resetToken` of an employee used as `Bearer` on `GET /api/data` | **200** |
| Delete a user in the UI, then log in as that user | login still works (code path, UI-only delete) |
| Login timing, unknown vs known e-mail | 24 ms vs 292 ms |

## Expected Behavior
- Deactivating an account blocks it immediately, including tokens already issued.
- Admins edit role and status through the API, and every change is recorded (TICKET-DB-010).
- Reset and activation tokens are single-use, opaque and stored hashed, and are never accepted as session tokens.
- Login timing does not depend on whether the account exists.

## Technical Analysis
- Login: `main.py:195-222`.
- `get_current_user`: `main.py:107-114` and `app/core/deps.py:13-30`.
- Reset: `main.py:271-326`.
- Creation: `main.py:224-269`.
- **Positive:** the role is re-read from the database on every request (the JWT `role` claim is ignored), so a server-side role change takes effect at once.
- **Physical deletion is impossible anyway:** `payslips` and `leave_requests` reference `users` with `NO ACTION`, and payroll must be retained. Use deactivation.

## Root Cause
The UI was built on `localStorage`. `isActive` was added to the model without any check using it, and session and reset tokens share one key and one shape.

## Impact
A departed employee or a compromised account keeps full API access, while the admin believes access was removed.

## Proposed Solution
1. Check `isActive` at login **and** in a single `get_current_user`.
2. Add `users.tokenVersion INT NOT NULL DEFAULT 0` (or `sessionsInvalidatedAt`), embed it in the JWT, compare it on every request, and bump it on deactivation, role change and password change.
3. Admin-only endpoints: `PATCH /api/users/{id}` (role, active) and `POST /api/users/{id}/deactivate`. No physical delete.
4. Reset tokens: reject any token carrying `purpose` in `get_current_user`. Better: switch to `secrets.token_urlsafe(32)`, store its SHA-256, compare in constant time, single use, 1 h.
5. Replace the temporary password with an activation link built on the same mechanism (72 h). Activation sets `isVerified = true`, and unverified accounts cannot log in.
6. Password policy on reset and activation (minimum length; other rules to be decided).
7. Constant-time login: run `bcrypt.checkpw` against a dummy hash when the user does not exist. Add rate limiting on `/api/login`.
8. Wire `UsersView` to the new endpoints and drop the local handlers.

## Acceptance Criteria
- [ ] Login with an inactive account returns **401**.
- [ ] After deactivation, a previously issued token returns **401** on its next request.
- [ ] A reset token used as `Bearer` returns **401**.
- [ ] `users.resetToken` (or its replacement) contains only a hash.
- [ ] `POST /api/users` no longer returns a password; a new account cannot log in before activation.
- [ ] Login median latency for unknown and known e-mails is within the same order of magnitude.
- [ ] Deleting or editing a user in the UI changes the server state, and the action is recorded.

## Evidence
Runtime tests T-B04 (inactive login), T-B07 (reset token as session) and T-A09 (timing), on `develop` @ `34453a4`, 2026-10-02. Code references above.

## Related Findings
AUDIT-DB-004 (HIGH), AUDIT-DB-005 (MEDIUM), AUDIT-DB-009 (LOW), AUDIT-DB-024 (LOW)

## Dependencies
TICKET-DB-001 (migration for `tokenVersion`), TICKET-DB-007 (`isActive NOT NULL DEFAULT true`), TICKET-DB-010 (audit events). Related to #44 (2FA), which should build on the same token model.

## Estimated Complexity
L
