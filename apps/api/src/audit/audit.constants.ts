/**
 * DEV-36 — Audit append-only allowlist and excluded-fields policy.
 *
 * `AUDIT_CHANGE_FIELDS` lists the only fields that may appear in `before`
 * and `after` for each `entityType`. Any key outside the allowlist is
 * rejected with `AuditInvalidFieldException` (HTTP 400 AUDIT_INVALID_FIELD).
 *
 * `EXCLUDED_CHANGE_FIELDS` is an explicit deny-list of secret-like field
 * names. The list is enforced by `isExcludedChangeField`, which also detects
 * names that end with `password`, `token` or `secret` (case-insensitive).
 * Excluded fields are silently removed from `before`/`after` *before* the
 * allowlist check, so a payload that would otherwise be allowed by the
 * allowlist is not persisted with the secret leaked.
 */
export const AUDIT_CHANGE_FIELDS: Readonly<Record<string, readonly string[]>> = {
  organization: ['name', 'slug', 'status'],
  invitation: ['email', 'role', 'status', 'expiresAt'],
  membership: ['role', 'status', 'permissions'],
  'audit-echo': ['message'],
} as const;

export const EXCLUDED_CHANGE_FIELDS: readonly string[] = [
  'password',
  'token',
  'session',
  'content',
  'secret',
  'apiKey',
  'accessToken',
  'refreshToken',
  'cookies',
  'body',
  'payload',
] as const;

const SUFFIX_PATTERN = /(password|token|secret)$/i;

const EXCLUDED_LOOKUP: ReadonlySet<string> = new Set(
  EXCLUDED_CHANGE_FIELDS.map((name) => name.toLowerCase()),
);

/**
 * Returns `true` when a field name is too sensitive to ever persist in an
 * `AuditEvent`. The check is case-insensitive and matches both literal names
 * from `EXCLUDED_CHANGE_FIELDS` and any field whose name ends with
 * `password`, `token` or `secret`.
 */
export function isExcludedChangeField(name: string): boolean {
  const lower = name.toLowerCase();
  if (EXCLUDED_LOOKUP.has(lower)) {
    return true;
  }
  return SUFFIX_PATTERN.test(lower);
}

/**
 * Returns the list of allowed fields for the given `entityType`. Throws when
 * the `entityType` has no allowlist entry, forcing the service to surface a
 * misconfiguration as `AuditInvalidFieldException` instead of silently
 * dropping the changes.
 */
export function getAuditChangeFields(entityType: string): readonly string[] {
  const fields = AUDIT_CHANGE_FIELDS[entityType];
  if (typeof fields === 'undefined') {
    throw new Error(
      `Audit entity "${entityType}" has no allowlist configured`,
    );
  }
  return fields;
}
