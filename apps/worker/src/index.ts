import type { HealthStatus } from '@koty-app/contracts';

interface WorkerConfig {
  name: string;
  port: number;
  environment: string;
}

type ShutdownSignal = 'SIGINT' | 'SIGTERM';

class Worker {
  private config: WorkerConfig;
  private isRunning: boolean = false;
  private healthCheckInterval: NodeJS.Timeout | undefined;
  private shutdownHandlers: Partial<Record<ShutdownSignal, () => void>> = {};

  constructor(config: Partial<WorkerConfig> = {}) {
    this.config = {
      name: config.name || 'koty-worker',
      port: config.port || 3001,
      environment: config.environment || process.env.NODE_ENV || 'development',
    };
  }

  start(): Promise<void> {
    if (this.isRunning) {
      console.log(`[${this.config.name}] Worker is already running`);
      return Promise.resolve();
    }

    console.log(`[${this.config.name}] Starting worker...`);
    console.log(`[${this.config.name}] Environment: ${this.config.environment}`);
    console.log(`[${this.config.name}] Port: ${String(this.config.port)}`);

    this.isRunning = true;
    this.registerShutdownHandlers();
    this.startHealthCheck();

    console.log(`[${this.config.name}] Worker started successfully`);
    return Promise.resolve();
  }

  stop(): Promise<void> {
    if (!this.isRunning) {
      console.log(`[${this.config.name}] Worker is not running`);
      return Promise.resolve();
    }

    console.log(`[${this.config.name}] Stopping worker...`);
    this.isRunning = false;
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = undefined;
    }
    this.unregisterShutdownHandlers();
    console.log(`[${this.config.name}] Worker stopped`);
    return Promise.resolve();
  }

  getStatus(): { running: boolean; health: HealthStatus } {
    return {
      running: this.isRunning,
      health: this.isRunning ? 'ok' : 'unhealthy',
    };
  }

  private registerShutdownHandlers(): void {
    for (const signal of ['SIGTERM', 'SIGINT'] as const) {
      if (this.shutdownHandlers[signal]) {
        continue;
      }

      const handler = () => {
        void this.shutdown(signal);
      };
      this.shutdownHandlers[signal] = handler;
      process.on(signal, handler);
    }
  }

  private unregisterShutdownHandlers(): void {
    for (const signal of ['SIGTERM', 'SIGINT'] as const) {
      const handler = this.shutdownHandlers[signal];
      if (!handler) {
        continue;
      }

      process.off(signal, handler);
      this.shutdownHandlers[signal] = undefined;
    }
  }

  private async shutdown(signal: ShutdownSignal): Promise<void> {
    console.log(`[${this.config.name}] Received ${signal}, shutting down...`);
    await this.stop();
    process.exit(0);
  }

  private startHealthCheck(): void {
    if (this.healthCheckInterval) {
      return;
    }

    this.healthCheckInterval = setInterval(() => {
      const status = this.getStatus();
      console.log(`[${this.config.name}] Health check: ${status.health}`);
    }, 60000);
  }
}

export { Worker, type WorkerConfig };
export default Worker;
