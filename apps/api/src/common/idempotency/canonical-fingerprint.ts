import { createHash } from 'node:crypto';

/**
 * Compute a canonical SHA-256 fingerprint of a request payload.
 *
 * The fingerprint is derived from a stable JSON serialization where every
 * object key is sorted recursively. This makes the fingerprint independent of
 * the original key ordering and ensures that two semantically equal payloads
 * produce the same fingerprint.
 *
 * The output is a lowercase hex-encoded SHA-256 digest (64 characters).
 *
 * See DEV-31 / `api-v1-idempotency` for the contract.
 */
export function computeCanonicalFingerprint(input: unknown): string {
  const serialized = canonicalStringify(input);
  return createHash('sha256').update(serialized).digest('hex');
}

/**
 * Deterministically serialize an arbitrary value to a JSON string.
 *
 * - Object keys are sorted recursively (arrays keep their order).
 * - `undefined` values inside objects are omitted.
 * - `Date` instances are serialized as ISO strings.
 * - Functions, symbols and `bigint` values throw (they are not part of the
 *   idempotency contract).
 */
export function canonicalStringify(value: unknown): string {
  return JSON.stringify(canonicalize(value));
}

function canonicalize(value: unknown): unknown {
  if (value === null) {
    return null;
  }

  if (Array.isArray(value)) {
    return value.map((item) => canonicalize(item));
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const sortedKeys = Object.keys(obj).sort();
    const result: Record<string, unknown> = {};
    for (const key of sortedKeys) {
      const entry = obj[key];
      if (entry === undefined) {
        continue;
      }
      result[key] = canonicalize(entry);
    }
    return result;
  }

  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return value;
  }

  throw new TypeError(
    `canonicalStringify does not support values of type ${typeof value}`,
  );
}