import { Module, MiddlewareConsumer, NestModule } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { HealthModule } from './health/health.module';
import { PrismaModule } from './prisma/prisma.module';
import { CorrelationIdMiddleware } from './common/middleware/correlation-id.middleware';
import { IdempotencyModule } from './common/idempotency/idempotency.module';
import { IdempotencyEchoModule } from './idempotency-echo/idempotency-echo.module';

const additionalImports = [];
if (process.env['ENABLE_IDEMPOTENCY_ECHO'] === 'true') {
  additionalImports.push(IdempotencyEchoModule.register());
}

@Module({
  imports: [HealthModule, PrismaModule, IdempotencyModule, ...additionalImports],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(CorrelationIdMiddleware).forRoutes('*');
  }
}