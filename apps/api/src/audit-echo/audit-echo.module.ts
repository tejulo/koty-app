import { DynamicModule, Module } from '@nestjs/common';

import { AuditModule } from '../audit/audit.module';
import { AuditEchoController } from './audit-echo.controller';

@Module({})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class AuditEchoModule {
  static register(): DynamicModule {
    return {
      module: AuditEchoModule,
      imports: [AuditModule],
      controllers: [AuditEchoController],
    };
  }
}
