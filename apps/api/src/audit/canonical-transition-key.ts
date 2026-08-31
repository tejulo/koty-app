import { createHash } from 'node:crypto';

import { canonicalStringify } from '../common/idempotency/canonical-fingerprint';

/**
 * DEV-36 — Canonical SHA-256 transition key for `AuditEvent` idempotency.
 *
 * The transition key is the fingerprint of the (scope, action, entityType,
 * entityId, correlationId) tuple. Two events with the same key represent the
 * same logical transition and must collapse into a single row in the
 * `AuditEvent` table (enforced by `@@unique([scope, transitionKey])`).
 *
 * The key is derived through `canonicalStringify` so that the resulting
 * digest is stable across minor re-serializations.
 */
export interface AuditTransitionInput {
  scope: 'PLATFORM' | 'ORGANIZATION';
  action: string;
  entityType: string;
  entityId: string;
  correlationId: string;
}

export function computeCanonicalTransitionKey(input: AuditTransitionInput): string {
  const serialized = canonicalStringify(input);
  return createHash('sha256').update(serialized).digest('hex');
}
