import { API_BASE_URL } from '../lib/constants';

export class ApiError extends Error {
  code: string;
  details?: any;
  status: number;

  constructor(message: string, code = 'unknown_error', status = 500, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

let isBackendAvailable: boolean | null = null;

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(1500),
    });
    isBackendAvailable = res.ok;
    return res.ok;
  } catch {
    isBackendAvailable = false;
    return false;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('nimbus_auth_token');
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorBody: any = {};
      try {
        errorBody = await response.json();
      } catch {
        // fallback
      }
      const message = errorBody?.error?.message || errorBody?.detail || `HTTP Error ${response.status}`;
      const code = errorBody?.error?.code || `HTTP_${response.status}`;
      throw new ApiError(message, code, response.status, errorBody?.error?.details);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network or connection refusal
    throw new ApiError(
      err.message || 'Network connection failed. Backend service might be unreachable.',
      'NETWORK_FAILURE',
      0
    );
  }
}
