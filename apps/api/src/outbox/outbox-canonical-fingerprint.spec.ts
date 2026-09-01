import { describe, expect, it } from 'vitest';

import {
  computeOutboxCanonicalFingerprint,
  type OutboxCanonicalFingerprintInput,
} from './outbox-canonical-fingerprint';

const baseInput: OutboxCanonicalFingerprintInput = {
  organizationId: 'org-1',
  aggregateType: 'organization',
  aggregateId: 'org-123',
  version: 1,
  semanticKey: 'created',
  eventType: 'organization.created',
  payload: { name: 'Acme', status: 'active' },
};

describe('computeOutboxCanonicalFingerprint', () => {
  it('returns a 64 character lowercase hex digest', () => {
    const key = computeOutboxCanonicalFingerprint(baseInput);
    expect(key).toMatch(/^[0-9a-f]{64}$/);
  });

  it('is stable across calls with the same input', () => {
    const first = computeOutboxCanonicalFingerprint(baseInput);
    const second = computeOutboxCanonicalFingerprint({ ...baseInput });
    expect(first).toBe(second);
  });

  it('is stable when payload keys are reordered', () => {
    const a = computeOutboxCanonicalFingerprint(baseInput);
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      payload: { status: 'active', name: 'Acme' },
    });
    expect(a).toBe(b);
  });

  it('changes when organizationId changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      organizationId: 'org-1',
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      organizationId: 'org-2',
    });
    expect(a).not.toBe(b);
  });

  it('changes when aggregateType changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      aggregateType: 'organization',
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      aggregateType: 'invitation',
    });
    expect(a).not.toBe(b);
  });

  it('changes when aggregateId changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      aggregateId: 'a',
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      aggregateId: 'b',
    });
    expect(a).not.toBe(b);
  });

  it('changes when version changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      version: 1,
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      version: 2,
    });
    expect(a).not.toBe(b);
  });

  it('changes when semanticKey changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      semanticKey: 'created',
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      semanticKey: 'updated',
    });
    expect(a).not.toBe(b);
  });

  it('changes when eventType changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      eventType: 'organization.created',
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      eventType: 'organization.updated',
    });
    expect(a).not.toBe(b);
  });

  it('changes when a payload field changes', () => {
    const a = computeOutboxCanonicalFingerprint({
      ...baseInput,
      payload: { name: 'Acme' },
    });
    const b = computeOutboxCanonicalFingerprint({
      ...baseInput,
      payload: { name: 'Beta' },
    });
    expect(a).not.toBe(b);
  });
});
