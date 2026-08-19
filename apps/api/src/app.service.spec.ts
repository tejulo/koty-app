import { describe, expect, it } from 'vitest';

import { AppService } from './app.service';

describe('AppService', () => {
  const service = new AppService();

  it('returns the API greeting', () => {
    expect(service.getHello()).toBe('Hello from Koty API!');
  });

  it('returns an ok status with an ISO timestamp', () => {
    const result = service.getHealth();

    expect(result.status).toBe('ok');
    expect(new Date(result.timestamp).toISOString()).toBe(result.timestamp);
  });
});
