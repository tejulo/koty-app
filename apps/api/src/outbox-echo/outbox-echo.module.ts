import { DynamicModule, Module } from '@nestjs/common';

import { OutboxModule } from '../outbox/outbox.module';
import { OutboxEchoController } from './outbox-echo.controller';

@Module({})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class OutboxEchoModule {
  static register(): DynamicModule {
    return {
      module: OutboxEchoModule,
      imports: [OutboxModule],
      controllers: [OutboxEchoController],
    };
  }
}
