import { Test, TestingModule } from '@nestjs/testing';
import { HttpException, HttpStatus } from '@nestjs/common';
import { ZodError, ZodIssueCode } from 'zod';
import { ApiExceptionFilter } from './api-exception.filter';
import { ErrorCode } from './error-code.enum';

describe('ApiExceptionFilter', () => {
  let filter: ApiExceptionFilter;
  let mockResponse: { status: jest.Mock; json: jest.Mock };

  beforeEach(() => {
    filter = new ApiExceptionFilter();
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
    };
  });

  const createMockArgumentsHost = (correlationId = 'test-correlation-id') => ({
    switchToHttp: () => ({
      getResponse: () => mockResponse,
      getRequest: () => ({
        headers: { 'x-correlation-id': correlationId },
      }),
    }),
  });

  describe('HttpException handling', () => {
    it('should handle validation error (400) with VALIDATION_ERROR code', () => {
      const exception = new HttpException('Validation failed', HttpStatus.BAD_REQUEST);
      const host = createMockArgumentsHost();

      filter.catch(exception, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.VALIDATION_ERROR,
        message: 'Validation failed',
        fieldErrors: [],
        correlationId: 'test-correlation-id',
      });
    });

    it('should handle not found error (404) with NOT_FOUND code', () => {
      const exception = new HttpException('Not found', HttpStatus.NOT_FOUND);
      const host = createMockArgumentsHost();

      filter.catch(exception, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(404);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.NOT_FOUND,
        message: 'Not found',
        fieldErrors: [],
        correlationId: 'test-correlation-id',
      });
    });

    it('should handle unauthorized error (401) with UNAUTHORIZED code', () => {
      const exception = new HttpException('Unauthorized', HttpStatus.UNAUTHORIZED);
      const host = createMockArgumentsHost();

      filter.catch(exception, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(401);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.UNAUTHORIZED,
        message: 'Unauthorized',
        fieldErrors: [],
        correlationId: 'test-correlation-id',
      });
    });

    it('should handle conflict (409) with IDEMPOTENCY_KEY_REUSED code', () => {
      const exception = new HttpException(
        {
          message: 'Idempotency key reused with a different request payload',
          code: ErrorCode.IDEMPOTENCY_KEY_REUSED,
        },
        HttpStatus.CONFLICT,
      );
      const host = createMockArgumentsHost();

      filter.catch(exception, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(409);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.IDEMPOTENCY_KEY_REUSED,
        message:
          'Idempotency key reused with a different request payload',
        fieldErrors: [],
        correlationId: 'test-correlation-id',
      });
    });

    it('should handle conflict (409) with default IDEMPOTENCY_KEY_REUSED code when no code is provided', () => {
      const exception = new HttpException('Conflict', HttpStatus.CONFLICT);
      const host = createMockArgumentsHost();

      filter.catch(exception, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(409);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.IDEMPOTENCY_KEY_REUSED,
        message: 'Conflict',
        fieldErrors: [],
        correlationId: 'test-correlation-id',
      });
    });

    it('should handle internal error (500) with INTERNAL_ERROR code', () => {
      const exception = new HttpException('Internal error', HttpStatus.INTERNAL_SERVER_ERROR);
      const host = createMockArgumentsHost();

      filter.catch(exception, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(500);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.INTERNAL_ERROR,
        message: 'Internal error',
        fieldErrors: [],
        correlationId: 'test-correlation-id',
      });
    });
  });

  describe('ZodError handling', () => {
    it('should handle ZodError with VALIDATION_ERROR code', () => {
      const zodError = new ZodError([
        {
          code: ZodIssueCode.invalid_type,
          expected: 'string',
          received: 'number',
          path: ['name'],
          message: 'Expected string',
        },
      ]);
      const host = createMockArgumentsHost();

      filter.catch(zodError, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        code: ErrorCode.VALIDATION_ERROR,
        message: 'Validation failed',
        fieldErrors: [{ field: 'name', message: 'Expected string' }],
        correlationId: 'test-correlation-id',
      });
    });

    it('should handle ZodError with multiple field errors', () => {
      const zodError = new ZodError([
        { code: ZodIssueCode.invalid_type, expected: 'string', received: 'number', path: ['name'], message: 'Expected string' },
        { code: ZodIssueCode.invalid_type, expected: 'email', received: 'string', path: ['email'], message: 'Invalid email' },
      ]);
      const host = createMockArgumentsHost();

      filter.catch(zodError, host as any);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      const jsonCall = mockResponse.json.mock.calls[0][0];
      expect(jsonCall.fieldErrors).toHaveLength(2);
      expect(jsonCall.fieldErrors[0].field).toBe('name');
      expect(jsonCall.fieldErrors[1].field).toBe('email');
    });
  });

  describe('correlationId handling', () => {
    it('should use correlationId from request headers', () => {
      const exception = new HttpException('Error', HttpStatus.BAD_REQUEST);
      const host = createMockArgumentsHost('custom-correlation-id');

      filter.catch(exception, host as any);

      expect(mockResponse.json).toHaveBeenCalledWith(
        expect.objectContaining({ correlationId: 'custom-correlation-id' }),
      );
    });

    it('should use "unknown" when correlationId is not present', () => {
      const exception = new HttpException('Error', HttpStatus.BAD_REQUEST);
      const host = createMockArgumentsHost('');

      filter.catch(exception, host as any);

      expect(mockResponse.json).toHaveBeenCalledWith(
        expect.objectContaining({ correlationId: 'unknown' }),
      );
    });
  });
});