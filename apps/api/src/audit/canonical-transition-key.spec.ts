import { describe, expect, it } from 'vitest';

import {
  computeCanonicalTransitionKey,
  type AuditTransitionInput,
} from './canonical-transition-key';

const baseInput: AuditTransitionInput = {
  scope: 'ORGANIZATION',
  action: 'organization.create',
  entityType: 'organization',
  entityId: 'org-123',
  correlationId: '11111111-1111-4111-8111-111111111111',
};

describe('computeCanonicalTransitionKey', () => {
  it('returns a 64 character lowercase hex digest', () => {
    const key = computeCanonicalTransitionKey(baseInput);
    expect(key).toMatch(/^[0-9a-f]{64}$/);
  });

  it('is stable across calls with the same input', () => {
    const first = computeCanonicalTransitionKey(baseInput);
    const second = computeCanonicalTransitionKey({ ...baseInput });
    expect(first).toBe(second);
  });

  it('changes when correlationId changes', () => {
    const a = computeCanonicalTransitionKey({
      ...baseInput,
      correlationId: 'c-1',
    });
    const b = computeCanonicalTransitionKey({
      ...baseInput,
      correlationId: 'c-2',
    });
    expect(a).not.toBe(b);
  });

  it('changes when entityId changes', () => {
    const a = computeCanonicalTransitionKey({ ...baseInput, entityId: 'x' });
    const b = computeCanonicalTransitionKey({ ...baseInput, entityId: 'y' });
    expect(a).not.toBe(b);
  });

  it('changes when scope changes', () => {
    const a = computeCanonicalTransitionKey({ ...baseInput, scope: 'PLATFORM' });
    const b = computeCanonicalTransitionKey({
      ...baseInput,
      scope: 'ORGANIZATION',
    });
    expect(a).not.toBe(b);
  });

  it('changes when action changes', () => {
    const a = computeCanonicalTransitionKey({
      ...baseInput,
      action: 'organization.create',
    });
    const b = computeCanonicalTransitionKey({
      ...baseInput,
      action: 'organization.update',
    });
    expect(a).not.toBe(b);
  });

  it('changes when entityType changes', () => {
    const a = computeCanonicalTransitionKey({
      ...baseInput,
      entityType: 'organization',
    });
    const b = computeCanonicalTransitionKey({
      ...baseInput,
      entityType: 'invitation',
    });
    expect(a).not.toBe(b);
  });
});
