export interface FieldError {
  field: string;
  message: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  fieldErrors: FieldError[];
  correlationId: string;
}
