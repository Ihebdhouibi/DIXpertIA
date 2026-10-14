/**
 * The single place the frontend talks to the API (#65).
 *
 * Before this, five endpoints were called by hand and every other screen read
 * mock data out of `localStorage`. That meant business data was neither shared
 * between users nor durable: an invoice the admin created was invisible to the
 * accountant, "delete user" only changed the browser, and clearing site data
 * reset the company's books to a fixture.
 *
 * Everything goes through `request` so that authentication, error handling and
 * the 401 path are written once rather than per call site.
 */
import { Client, Employee, Invoice, LeaveRequest, Payslip, User } from './types';

const TOKEN_KEY = 'token';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    // Storage blocked (private mode, blocked site data). The session still
    // works until the page is reloaded.
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing to do: the caller keeps the token in memory for this session.
  }
}

/** Thrown for any non-2xx response, carrying what the API said went wrong. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

/** Called when the API rejects our token, so the app can return to the login screen. */
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

/** Sends an authenticated request and turns a refusal into an ApiError. */
async function send(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  });

  if (res.status === 401) {
    // The token is gone or expired. Clearing it here stops every subsequent
    // call retrying with a credential the server has already refused.
    setToken(null);
    onUnauthorized();
    throw new ApiError(401, 'Your session has expired. Please sign in again.');
  }

  if (!res.ok) {
    throw new ApiError(res.status, await readError(res));
  }
  return res;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  onResponse?: (res: Response) => void,
): Promise<T> {
  const res = await send(path, init);
  onResponse?.(res);

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/**
 * A paginated list and its unpaginated total. The API reports the total in an
 * X-Total-Count header rather than wrapping the body (#61), so a plain
 * request() cannot see it.
 */
export interface Page<T> {
  rows: T[];
  total: number;
}

async function requestPage<T>(path: string): Promise<Page<T>> {
  let total = 0;
  const rows = await request<T[]>(path, {}, (res) => {
    total = Number(res.headers.get('X-Total-Count') ?? 0);
  });
  return { rows, total: Number.isFinite(total) && total > 0 ? total : rows.length };
}

/**
 * Pull a readable message out of an error response.
 *
 * FastAPI returns `detail` as a string for an HTTPException but as a list of
 * field errors for a 422, and the body is not always JSON. Rendering the raw
 * object gives the user "[object Object]", so each shape is handled.
 */
async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { loc?: (string | number)[]; msg?: string }) => {
          const field = d.loc?.filter(p => p !== 'body').join('.');
          return field ? `${field}: ${d.msg}` : d.msg;
        })
        .filter(Boolean)
        .join('; ');
    }
    return `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

// --- Authentication ---------------------------------------------------------

/** One invoice line as the API takes it: the database's own column names. */
export interface InvoiceLineInput {
  designation: string;
  quantite: number;
  prix_unitaire: number;
  taux_tva: number;
}

/** Body of POST /api/invoices (#128). */
export interface InvoiceCreate {
  client_id: number;
  date_echeance: string;
  items: InvoiceLineInput[];
}

/** Body of PATCH /api/invoices/{id} (#125). */
export interface InvoiceUpdate {
  date_echeance: string;
  items: InvoiceLineInput[];
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: User;
}

export const auth = {
  login: (email: string, password: string) =>
    request<LoginResult>('/api/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  /**
   * The signed-in user, resolved from the token.
   *
   * The session is restored with this rather than from a stored copy of the
   * user, so the client never decides its own role.
   */
  me: () => request<User>('/api/me'),
};

// --- Business entities ------------------------------------------------------
//
// Each list takes the limit/offset the API caps (#61). The defaults here are
// the first page; screens that need more pass their own.

export const invoices = {
  list: (params: Record<string, string | number> = {}) =>
    request<Invoice[]>(`/api/invoices?${new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    )}`),
  /** One page for the invoice workspace, with the server's total (#113). */
  page: (params: Record<string, string | number | undefined>) =>
    requestPage<Invoice>(`/api/invoices?${new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => [k, String(v)]),
    )}`),
  /** Move an invoice through the accountant's workflow (#96). */
  setProcessingStatus: (id: string | number, processingStatus: string) =>
    request<Invoice>(`/api/invoices/${id}/processing-status`, {
      method: 'PATCH',
      body: JSON.stringify({ processing_status: processingStatus }),
    }),
  get: (id: number) => request<Invoice>(`/api/invoices/${id}`),
  /**
   * The invoice PDF the server generates (#86), as a Blob. `inline` asks for a
   * copy to display rather than save; the invoice detail embeds it (#127).
   */
  pdf: async (id: string | number, inline = false) =>
    (await send(`/api/invoices/${id}/download${inline ? '?inline=true' : ''}`)).blob(),
  /** Correct a draft: replace its lines and its due date (#125). Admin only. */
  update: (id: string | number, body: InvoiceUpdate) =>
    request<Invoice>(`/api/invoices/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  /**
   * Create a draft invoice (#128). The Idempotency-Key makes a repeated
   * request - a double click, a retry after a timeout - return the invoice
   * already created instead of taking a second legal number.
   */
  create: (body: InvoiceCreate, idempotencyKey: string) =>
    request<Invoice>('/api/invoices', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Idempotency-Key': idempotencyKey },
    }),
};

export const clients = {
  list: () => request<Client[]>('/api/clients?limit=200'),
  create: (body: unknown) =>
    request<Client>('/api/clients', { method: 'POST', body: JSON.stringify(body) }),
};

export const leaveRequests = {
  list: () => request<LeaveRequest[]>('/api/leave-requests'),
  create: (body: unknown) =>
    request<LeaveRequest>('/api/leave-requests', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  approve: (id: string) =>
    request<LeaveRequest>(`/api/leave-requests/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason?: string) =>
    request<LeaveRequest>(`/api/leave-requests/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason ?? '' }),
    }),
};

export const payslips = {
  list: () => request<Payslip[]>('/api/payslips'),
};

export const employees = {
  list: () => request<Employee[]>('/api/employees'),
};

export const users = {
  list: () => request<User[]>('/api/users'),
  create: (body: unknown) =>
    request<User>('/api/users', { method: 'POST', body: JSON.stringify(body) }),
};
