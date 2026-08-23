import { Request, Response, NextFunction } from 'express';
import { CorrelationIdMiddleware, CORRELATION_ID_HEADER } from './correlation-id.middleware';

describe('CorrelationIdMiddleware', () => {
  let middleware: CorrelationIdMiddleware;
  let mockRequest: Partial<Request>;
  let mockResponse: Partial<Response>;
  let nextFunction: NextFunction;

  beforeEach(() => {
    middleware = new CorrelationIdMiddleware();
    nextFunction = jest.fn();
    mockResponse = {
      setHeader: jest.fn(),
    };
  });

  describe('when x-correlation-id header is not present', () => {
    it('should generate a new UUID v4 correlation id', () => {
      mockRequest = { headers: {} };

      middleware.use(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.setHeader).toHaveBeenCalledWith(
        CORRELATION_ID_HEADER,
        expect.stringMatching(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
        ),
      );
    });

    it('should attach correlation id to request headers', () => {
      mockRequest = { headers: {} };

      middleware.use(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockRequest.headers).toHaveProperty(CORRELATION_ID_HEADER);
    });

    it('should call next function', () => {
      mockRequest = { headers: {} };

      middleware.use(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(nextFunction).toHaveBeenCalled();
    });
  });

  describe('when x-correlation-id header is present', () => {
    it('should use the client-provided correlation id', () => {
      const clientCorrelationId = 'client-provided-id';
      mockRequest = { headers: { [CORRELATION_ID_HEADER]: clientCorrelationId } };

      middleware.use(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.setHeader).toHaveBeenCalledWith(
        CORRELATION_ID_HEADER,
        clientCorrelationId,
      );
      expect(mockRequest.headers[CORRELATION_ID_HEADER]).toBe(clientCorrelationId);
    });
  });
});
