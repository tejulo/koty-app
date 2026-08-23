import { createZodDto } from 'nestjs-zod';
import { z } from 'zod';

/**
 * Creates a DTO class from a Zod schema.
 * @param schema - The Zod schema to use for validation
 * @returns A DTO class that can be used with NestJS validation pipes
 */
export function createStrictZodDto(schema: z.ZodSchema) {
  return createZodDto(schema);
}
