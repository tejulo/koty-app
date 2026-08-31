import { describe, expect, it } from 'vitest';

import {
  canonicalStringify,
  computeCanonicalFingerprint,
} from './canonical-fingerprint';

describe('computeCanonicalFingerprint', () => {
  it('produces the same fingerprint for objects with the same keys in different order', () => {
    const a = { name: 'Acme', email: 'a@b.co' };
    const b = { email: 'a@b.co', name: 'Acme' };

    expect(computeCanonicalFingerprint(a)).toBe(
      computeCanonicalFingerprint(b),
    );
  });

  it('produces different fingerprints for objects with one value changed', () => {
    expect(computeCanonicalFingerprint({ name: 'Acme' })).not.toBe(
      computeCanonicalFingerprint({ name: 'Beta' }),
    );
  });

  it('produces the same fingerprint for nested objects regardless of key order', () => {
    const a = { org: { id: 'o1', name: 'Acme' }, actor: { id: 'u1' } };
    const b = { actor: { id: 'u1' }, org: { id: 'o1', name: 'Acme' } };

    expect(computeCanonicalFingerprint(a)).toBe(
      computeCanonicalFingerprint(b),
    );
  });

  it('produces a 64 character lowercase hex digest', () => {
    const fingerprint = computeCanonicalFingerprint({ name: 'Acme' });
    expect(fingerprint).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe('canonicalStringify', () => {
  it('sorts object keys deterministically', () => {
    expect(canonicalStringify({ b: 2, a: 1 })).toBe('{"a":1,"b":2}');
  });

  it('keeps array order', () => {
    expect(canonicalStringify([3, 1, 2])).toBe('[3,1,2]');
  });

  it('serializes Date as ISO string', () => {
    const iso = '2024-01-01T00:00:00.000Z';
    expect(canonicalStringify(new Date(iso))).toBe(JSON.stringify(iso));
  });

  it('omits undefined values inside objects', () => {
    expect(canonicalStringify({ a: 1, b: undefined })).toBe('{"a":1}');
  });

  it('throws for unsupported types', () => {
    expect(() => canonicalStringify(() => undefined)).toThrow(TypeError);
  });
});