import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
} from '@nestjs/common';
import { Response } from 'express';
import { ZodError } from 'zod';
import { ErrorCode } from './error-code.enum';
import { FieldError, ErrorResponse } from './error-response.interface';

@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<{ headers: Record<string, string | string[] | undefined> }>();
    const correlationId =
      (request.headers['x-correlation-id'] as string) || 'unknown';

    const BAD_REQUEST = 400;
    const UNAUTHORIZED = 401;
    const NOT_FOUND = 404;
    const INTERNAL_ERROR = 500;

    let httpStatus = INTERNAL_ERROR;
    let code = ErrorCode.INTERNAL_ERROR;
    let message = 'An unexpected error occurred';
    const fieldErrors: FieldError[] = [];

    if (exception instanceof HttpException) {
      httpStatus = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      if (typeof exceptionResponse === 'object') {
        const resp = exceptionResponse as { message?: unknown };
        const msgValue = resp.message;
        
        if (typeof msgValue === 'string') {
          message = msgValue;
        } else if (Array.isArray(msgValue)) {
          msgValue.forEach((msg: unknown) => {
            if (typeof msg === 'string') {
              fieldErrors.push({ field: 'unknown', message: msg });
            } else if (typeof msg === 'object' && msg !== null) {
              const msgObj = msg as Record<string, unknown>;
              fieldErrors.push({
                field: (msgObj.field as string) || 'unknown',
                message: (msgObj.message as string) || JSON.stringify(msg),
              });
            }
          });
          message = 'Validation failed';
          code = ErrorCode.VALIDATION_ERROR;
        }
      } else if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else {
        message = exception.message;
      }

      if (httpStatus === BAD_REQUEST) {
        code = ErrorCode.VALIDATION_ERROR;
      } else if (httpStatus === UNAUTHORIZED) {
        code = ErrorCode.UNAUTHORIZED;
      } else if (httpStatus === NOT_FOUND) {
        code = ErrorCode.NOT_FOUND;
      } else if (httpStatus >= INTERNAL_ERROR) {
        code = ErrorCode.INTERNAL_ERROR;
      }
    } else if (exception instanceof ZodError) {
      httpStatus = BAD_REQUEST;
      code = ErrorCode.VALIDATION_ERROR;
      message = 'Validation failed';

      exception.errors.forEach((err) => {
        fieldErrors.push({
          field: err.path.join('.'),
          message: err.message,
        });
      });
    }

    const errorResponse: ErrorResponse = {
      code,
      message,
      fieldErrors,
      correlationId,
    };

    response.status(httpStatus).json(errorResponse);
  }
}
