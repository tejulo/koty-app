// Contracts shared across the monorepo
// Add your shared types, schemas, and interfaces here

export type HealthStatus = 'ok' | 'degraded' | 'unhealthy';

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}
