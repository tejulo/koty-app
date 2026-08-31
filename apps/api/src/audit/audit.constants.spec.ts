import { describe, expect, it } from 'vitest';

import {
  AUDIT_CHANGE_FIELDS,
  EXCLUDED_CHANGE_FIELDS,
  getAuditChangeFields,
  isExcludedChangeField,
} from './audit.constants';

describe('isExcludedChangeField', () => {
  it.each([
    'password',
    'Password',
    'PASSWORD',
    'token',
    'Token',
    'session',
    'content',
    'secret',
    'apiKey',
    'accessToken',
    'refreshToken',
    'cookies',
    'body',
    'payload',
  ])('returns true for literal excluded field "%s"', (name) => {
    expect(isExcludedChangeField(name)).toBe(true);
  });

  it('returns true for suffix matches (password, token, secret)', () => {
    expect(isExcludedChangeField('userPassword')).toBe(true);
    expect(isExcludedChangeField('refresh_token')).toBe(true);
    expect(isExcludedChangeField('clientSecret')).toBe(true);
  });

  it('returns false for non-excluded field names', () => {
    expect(isExcludedChangeField('name')).toBe(false);
    expect(isExcludedChangeField('status')).toBe(false);
    expect(isExcludedChangeField('email')).toBe(false);
    expect(isExcludedChangeField('permissions')).toBe(false);
  });

  it('exports a stable deny-list', () => {
    expect(EXCLUDED_CHANGE_FIELDS).toContain('password');
    expect(EXCLUDED_CHANGE_FIELDS).toContain('token');
    expect(EXCLUDED_CHANGE_FIELDS).toContain('session');
    expect(EXCLUDED_CHANGE_FIELDS).toContain('content');
  });
});

describe('AUDIT_CHANGE_FIELDS allowlist', () => {
  it('allows safe fields for the organization entity type', () => {
    const fields = AUDIT_CHANGE_FIELDS['organization'];
    expect(fields).toContain('name');
    expect(fields).toContain('status');
    expect(fields).not.toContain('password');
  });

  it('returns the allowlist for known entity types', () => {
    expect(getAuditChangeFields('organization')).toEqual(
      expect.arrayContaining(['name', 'slug', 'status']),
    );
    expect(getAuditChangeFields('audit-echo')).toEqual(
      expect.arrayContaining(['message']),
    );
  });

  it('throws when the entity type has no allowlist', () => {
    expect(() => getAuditChangeFields('unknown-entity')).toThrow(
      /no allowlist configured/,
    );
  });
});