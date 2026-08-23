import { Test, TestingModule } from '@nestjs/testing';
import { ExecutionContext, CallHandler } from '@nestjs/common';
import { of } from 'rxjs';
import { ZodValidationInterceptor } from './zod-validation.interceptor';
import { z } from 'zod';

describe('ZodValidationInterceptor', () => {
  let interceptor: ZodValidationInterceptor;

  const createMockSchema = z.object({
    body: z.object({
      name: z.string(),
      email: z.string().email(),
    }),
    query: z.object({}),
    params: z.object({}),
  });

  beforeEach(() => {
    interceptor = new ZodValidationInterceptor(createMockSchema);
  });

  const createMockContext = (body: unknown, query: unknown, params: unknown): ExecutionContext =>
    ({
      switchToHttp: () => ({
        getRequest: () => ({ body, query, params }),
      }),
    }) as ExecutionContext;

  const createMockCallHandler = (data: unknown): CallHandler => ({
    handle: () => of(data),
  });

  describe('valid input', () => {
    it('should pass validation with valid body', (done) => {
      const validBody = { name: 'Test', email: 'test@example.com' };
      const context = createMockContext(validBody, {}, {});
      const handler = createMockCallHandler({ status: 'ok' });

      interceptor.intercept(context, handler).subscribe({
        next: (result) => {
          expect(result).toBeDefined();
          done();
        },
        error: done,
      });
    });
  });

  describe('invalid input', () => {
    it('should reject body with unknown fields', (done) => {
      const bodyWithUnknown = { name: 'Test', email: 'test@example.com', unknownField: 'value' };
      const context = createMockContext(bodyWithUnknown, {}, {});
      const handler = createMockCallHandler({ status: 'ok' });

      interceptor.intercept(context, handler).subscribe({
        next: () => done('Should have thrown an error'),
        error: (error) => {
          expect(error.status).toBe(400);
          expect(error.response.message).toBe('Validation failed');
          done();
        },
      });
    });

    it('should reject body with missing required fields', (done) => {
      const incompleteBody = { name: 'Test' };
      const context = createMockContext(incompleteBody, {}, {});
      const handler = createMockCallHandler({ status: 'ok' });

      interceptor.intercept(context, handler).subscribe({
        next: () => done('Should have thrown an error'),
        error: (error) => {
          expect(error.status).toBe(400);
          expect(error.response.message).toBe('Validation failed');
          done();
        },
      });
    });

    it('should reject body with invalid email format', (done) => {
      const invalidEmailBody = { name: 'Test', email: 'not-an-email' };
      const context = createMockContext(invalidEmailBody, {}, {});
      const handler = createMockCallHandler({ status: 'ok' });

      interceptor.intercept(context, handler).subscribe({
        next: () => done('Should have thrown an error'),
        error: (error) => {
          expect(error.status).toBe(400);
          done();
        },
      });
    });
  });
});
