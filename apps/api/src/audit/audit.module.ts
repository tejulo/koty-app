import { Module } from '@nestjs/common';

import { AuditController } from './audit.controller';
import { AuditService } from './audit.service';

@Module({
  controllers: [AuditController],
  providers: [AuditService],
  exports: [AuditService],
})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class AuditModule {}
