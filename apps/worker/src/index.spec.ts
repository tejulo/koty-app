import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Worker } from './index.js';

describe('Worker', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(console, 'log').mockImplementation(() => undefined);
    vi.spyOn(process, 'on').mockReturnValue(process);
    vi.spyOn(process, 'off').mockReturnValue(process);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('reports its initial state', () => {
    const worker = new Worker();

    expect(worker.getStatus()).toEqual({
      running: false,
      health: 'unhealthy',
    });
  });

  it('starts and allocates one health-check interval', async () => {
    const worker = new Worker();

    await worker.start();

    expect(worker.getStatus()).toEqual({ running: true, health: 'ok' });
    expect(vi.getTimerCount()).toBe(1);
  });

  it('does not allocate another interval when started twice', async () => {
    const worker = new Worker();

    await worker.start();
    await worker.start();

    expect(vi.getTimerCount()).toBe(1);
  });

  it('registers one handler per signal when started twice', async () => {
    const worker = new Worker();

    await worker.start();
    await worker.start();

    expect(process.on).toHaveBeenCalledTimes(2);
    expect(process.on).toHaveBeenCalledWith('SIGTERM', expect.any(Function));
    expect(process.on).toHaveBeenCalledWith('SIGINT', expect.any(Function));
  });

  it('reports a stopped state', async () => {
    const worker = new Worker();
    await worker.start();

    await worker.stop();

    expect(worker.getStatus()).toEqual({
      running: false,
      health: 'unhealthy',
    });
  });

  it('releases the health-check interval when stopped', async () => {
    const worker = new Worker();
    await worker.start();

    await worker.stop();

    expect(vi.getTimerCount()).toBe(0);
  });

  it('removes the registered signal handlers when stopped', async () => {
    const worker = new Worker();
    await worker.start();
    const registrations = vi.mocked(process.on).mock.calls;

    await worker.stop();

    expect(process.off).toHaveBeenCalledTimes(2);
    expect(process.off).toHaveBeenCalledWith('SIGTERM', registrations[0]?.[1]);
    expect(process.off).toHaveBeenCalledWith('SIGINT', registrations[1]?.[1]);
  });

  it.each(['SIGTERM', 'SIGINT'] as const)(
    'stops and cleans up after receiving %s',
    async (signal) => {
      const exit = vi
        .spyOn(process, 'exit')
        .mockImplementation(() => undefined as never);
      const worker = new Worker();
      await worker.start();
      const registrations = vi.mocked(process.on).mock.calls;
      const registration = registrations.find(([event]) => event === signal);
      const handler = registration?.[1] as (() => void) | undefined;

      expect(handler).toBeTypeOf('function');
      handler?.();

      await vi.waitFor(() => {
        expect(exit).toHaveBeenCalledWith(0);
      });
      expect(worker.getStatus()).toEqual({
        running: false,
        health: 'unhealthy',
      });
      expect(vi.getTimerCount()).toBe(0);
      expect(process.off).toHaveBeenCalledTimes(2);
      expect(process.off).toHaveBeenCalledWith('SIGTERM', registrations[0]?.[1]);
      expect(process.off).toHaveBeenCalledWith('SIGINT', registrations[1]?.[1]);
    },
  );

  it('does not leak timers or signal handlers across a restart', async () => {
    const worker = new Worker();
    await worker.start();
    const firstRegistrations = vi.mocked(process.on).mock.calls.slice();

    await worker.stop();
    await worker.start();

    const allRegistrations = vi.mocked(process.on).mock.calls;
    const secondRegistrations = allRegistrations.slice(2);
    expect(vi.getTimerCount()).toBe(1);
    expect(allRegistrations).toHaveLength(4);
    expect(process.off).toHaveBeenCalledTimes(2);
    expect(secondRegistrations[0]?.[1]).not.toBe(firstRegistrations[0]?.[1]);
    expect(secondRegistrations[1]?.[1]).not.toBe(firstRegistrations[1]?.[1]);

    await worker.stop();

    expect(vi.getTimerCount()).toBe(0);
    expect(process.off).toHaveBeenCalledTimes(4);
    expect(process.off).toHaveBeenCalledWith('SIGTERM', secondRegistrations[0]?.[1]);
    expect(process.off).toHaveBeenCalledWith('SIGINT', secondRegistrations[1]?.[1]);
  });

  it('can be stopped twice without repeating cleanup', async () => {
    const worker = new Worker();
    await worker.start();

    await worker.stop();
    await worker.stop();

    expect(vi.getTimerCount()).toBe(0);
    expect(process.off).toHaveBeenCalledTimes(2);
  });
});
