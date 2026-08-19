import { Worker } from './index.js';

const worker = new Worker({
  name: 'koty-worker',
  port: 3001,
});

worker.start().catch((error: unknown) => {
  console.error('Failed to start worker:', error);
  process.exit(1);
});
