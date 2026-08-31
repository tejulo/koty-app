import { Global, Module } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

import { PRISMA_CLIENT } from './prisma.constants';
import { PrismaService } from './prisma.service';

@Global()
@Module({
  providers: [
    {
      provide: PRISMA_CLIENT,
      useFactory: (): PrismaClient => new PrismaClient(),
    },
    PrismaService,
  ],
  exports: [PrismaService],
})
// eslint-disable-next-line @typescript-eslint/no-extraneous-class
export class PrismaModule {}