import { Module } from '@nestjs/common';

import { OutboxService } from './outbox.service';

@Module({
  providers: [OutboxService],
  exports: [OutboxService],
})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class OutboxModule {}
