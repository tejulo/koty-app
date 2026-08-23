import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
  BadRequestException,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { ZodSchema } from 'zod';

interface RequestWithBody {
  body: unknown;
  query: unknown;
  params: unknown;
}

interface ParsedRequest {
  body: unknown;
  query: unknown;
  params: unknown;
}

@Injectable()
export class ZodValidationInterceptor implements NestInterceptor {
  constructor(private schema: ZodSchema) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const httpRequest = context.switchToHttp().getRequest<RequestWithBody>();

    const body = httpRequest.body;
    const query = httpRequest.query;
    const params = httpRequest.params;

    const result = this.schema.safeParse({ body, query, params });

    if (!result.success) {
      const errors = result.error.errors.map((err) => ({
        field: err.path.join('.'),
        message: err.message,
      }));

      throw new BadRequestException({
        message: 'Validation failed',
        errors,
      });
    }

    const parsedData = result.data as ParsedRequest;
    httpRequest.body = parsedData.body;
    httpRequest.query = parsedData.query;
    httpRequest.params = parsedData.params;

    return next.handle();
  }
}
