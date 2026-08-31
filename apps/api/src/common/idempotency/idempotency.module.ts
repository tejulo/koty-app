import { Module } from '@nestjs/common';

import { IdempotencyService } from './idempotency.service';

@Module({
  providers: [IdempotencyService],
  exports: [IdempotencyService],
})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class IdempotencyModule {}