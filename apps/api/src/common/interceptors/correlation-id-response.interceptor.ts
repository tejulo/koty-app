import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { Request } from 'express';
import { CORRELATION_ID_HEADER } from '../middleware/correlation-id.middleware';

interface CorrelationResponse {
  correlationId: string;
  [key: string]: unknown;
}

@Injectable()
export class CorrelationIdResponseInterceptor
  implements NestInterceptor<unknown, CorrelationResponse>
{
  intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Observable<CorrelationResponse> {
    const request = context.switchToHttp().getRequest<Request>();

    const correlationId =
      (request.headers[CORRELATION_ID_HEADER] as string) || 'unknown';

    return next.handle().pipe(
      map((data): CorrelationResponse => {
        const responseData: CorrelationResponse = { correlationId };
        
        if (typeof data === 'object' && data !== null) {
          Object.assign(responseData, data);
        } else {
          responseData.data = data;
        }
        
        return responseData;
      }),
    );
  }
}
