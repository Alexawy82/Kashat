// Simple API client wrapper for fetch
const baseUrl = process.env.NEXT_PUBLIC_API_BASE || '';

type RequestOptions = {
  body?: unknown;
  params?: { path?: Record<string, string>; query?: Record<string, string | number | boolean | undefined> };
};

async function request<T>(method: string, path: string, options?: RequestOptions): Promise<{ data?: T; error?: Error }> {
  try {
    // Normalize path: if baseUrl ends with /api and path starts with /api, avoid doubling
    let normalizedPath = path;
    if (baseUrl && baseUrl.endsWith('/api') && path.startsWith('/api')) {
      normalizedPath = path.slice(4); // Remove leading /api since baseUrl already has it
    }
    let url = `${baseUrl}${normalizedPath}`;

    // Replace path params
    if (options?.params?.path) {
      for (const [key, value] of Object.entries(options.params.path)) {
        url = url.replace(`{${key}}`, encodeURIComponent(value));
      }
    }

    // Add query params
    if (options?.params?.query) {
      const queryObj: Record<string, string> = {};
      for (const [key, value] of Object.entries(options.params.query)) {
        if (value !== undefined) {
          queryObj[key] = String(value);
        }
      }
      const queryString = new URLSearchParams(queryObj).toString();
      if (queryString) {
        url = `${url}?${queryString}`;
      }
    }

    const fetchOptions: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (options?.body) {
      fetchOptions.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, fetchOptions);

    if (!response.ok) {
      return { error: new Error(`HTTP ${response.status}: ${response.statusText}`) };
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return { data: undefined };
    }

    const data = JSON.parse(text) as T;
    return { data };
  } catch (err) {
    return { error: err instanceof Error ? err : new Error(String(err)) };
  }
}

export const client = {
  get: <T>(path: string, options?: RequestOptions) => request<T>('GET', path, options),
  post: <T>(path: string, options?: RequestOptions) => request<T>('POST', path, options),
  put: <T>(path: string, options?: RequestOptions) => request<T>('PUT', path, options),
  patch: <T>(path: string, options?: RequestOptions) => request<T>('PATCH', path, options),
  delete: <T>(path: string, options?: RequestOptions) => request<T>('DELETE', path, options),
};
