import { DynamicModule, Module } from '@nestjs/common';

import { IdempotencyModule } from '../common/idempotency/idempotency.module';
import { IdempotencyEchoController } from './idempotency-echo.controller';

@Module({})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class IdempotencyEchoModule {
  static register(): DynamicModule {
    return {
      module: IdempotencyEchoModule,
      imports: [IdempotencyModule],
      controllers: [IdempotencyEchoController],
    };
  }
}