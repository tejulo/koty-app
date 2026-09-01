import { createHash } from 'node:crypto';

import { canonicalStringify } from '../common/idempotency/canonical-fingerprint';

/**
 * DEV-32 — Canonical SHA-256 fingerprint of an outbox event.
 *
 * The fingerprint is computed from the same shape that the `@@unique`
 * constraint uses to arbitrate duplicates — namely
 * `(organizationId, aggregateType, aggregateId, version, semanticKey,
 * eventType, payload)`. Two events with identical metadata AND identical
 * payload collapse to a single row in the `OutboxEvent` table; two
 * events whose fingerprint differs must be reported as a semantic
 * conflict.
 *
 * The function intentionally excludes `correlationId` and
 * `causationId` from the fingerprint: both fields are traceability
 * metadata, not part of the event's identity. The fingerprint must be
 * stable across reintents that only change correlation/causation.
 */
export interface OutboxCanonicalFingerprintInput {
  organizationId: string;
  aggregateType: string;
  aggregateId: string;
  version: number;
  semanticKey: string;
  eventType: string;
  payload: Record<string, unknown>;
}

export function computeOutboxCanonicalFingerprint(
  input: OutboxCanonicalFingerprintInput,
): string {
  const serialized = canonicalStringify(input);
  return createHash('sha256').update(serialized).digest('hex');
}
