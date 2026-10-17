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
import { getLocale, t, type Locale } from './i18n';
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
      // The language showing (#135): the API answers its errors, dates and
      // notifications in it. Not the browser's own languages, which can differ
      // from the one chosen with the toggle.
      'Accept-Language': getLocale(),
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  });

  // Only a request that carried a token can have an expired session. A 401
  // without one is a refusal of its own, e.g. a wrong password at sign-in,
  // which used to read "Your session has expired" (#116).
  if (res.status === 401 && token) {
    // The token is gone or expired. Clearing it here stops every subsequent
    // call retrying with a credential the server has already refused.
    setToken(null);
    onUnauthorized();
    throw new ApiError(401, t('common.sessionExpired'));
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
    return t('common.requestFailed', { status: res.status });
  } catch {
    return t('common.requestFailed', { status: res.status });
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
  login: async (email: string, password: string) => {
    try {
      return await request<LoginResult>('/api/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
    } catch (error) {
      // Said the same way whichever of the two was wrong, as the server does.
      if (error instanceof ApiError && error.status === 401) {
        throw new ApiError(401, t('auth.invalidCredentials'));
      }
      throw error;
    }
  },

  /**
   * The signed-in user, resolved from the token.
   *
   * The session is restored with this rather than from a stored copy of the
   * user, so the client never decides its own role.
   */
  me: () => request<User>('/api/me'),
  /** Save the account's language, so its e-mails and other devices follow (#135). */
  setLocale: (locale: Locale) =>
    request<User>('/api/me/locale', { method: 'PUT', body: JSON.stringify({ locale }) }),
};

// --- Business entities ------------------------------------------------------
//
// Each list takes the limit/offset the API caps (#61). The defaults here are
// the first page; screens that need more pass their own.

/** One step in an invoice's life, from the audit trail (#115). */
export interface InvoiceHistoryEvent {
  id: string;
  occurredAt: string;
  action: string;
  /** The step in words, written by the server. */
  label: string;
  actorName: string;
  actorRole?: string | null;
}

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
  /** Every recorded step of one invoice, newest first (#115). Admin and accountant. */
  history: (id: string | number) => request<InvoiceHistoryEvent[]>(`/api/invoices/${id}/history`),
  /** Verification before sending (#118): the admin submits and sends, the accountant decides. */
  submit: (id: string | number) => request<Invoice>(`/api/invoices/${id}/submit`, { method: 'POST' }),
  approve: (id: string | number) => request<Invoice>(`/api/invoices/${id}/approve`, { method: 'POST' }),
  reject: (id: string | number, comment: string) =>
    request<Invoice>(`/api/invoices/${id}/reject`, { method: 'POST', body: JSON.stringify({ comment }) }),
  send: (id: string | number) => request<Invoice>(`/api/invoices/${id}/send`, { method: 'POST' }),
  /** Paid in full on `paidOn` (YYYY-MM-DD), by the admin or the accountant (#126). */
  pay: (id: string | number, paidOn: string) =>
    request<Invoice>(`/api/invoices/${id}/pay`, { method: 'POST', body: JSON.stringify({ paid_on: paidOn }) }),
  /** Cancelled by the admin, with a reason (#126). */
  cancel: (id: string | number, reason: string) =>
    request<Invoice>(`/api/invoices/${id}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) }),
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

/** One status on the dashboard: how many invoices, and for how much (TTC). */
export interface StatusFigure {
  status: string;
  count: number;
  amount: number;
}

/**
 * The dashboard's figures, computed by the server over every row (#120).
 * A null block is not zero: the caller has no access to it - `invoices` for an
 * employee, `team` for anyone but the admin.
 */
/** Invoices one way (#40), and their total TTC. */
export interface DirectionTotal {
  count: number;
  amount: number;
}

export interface DashboardSummary {
  month: string | null;
  invoices: {
    count: number;
    /** Never added together: one is income, the other expenses. */
    clients: DirectionTotal;
    suppliers: DirectionTotal;
    byStatus: StatusFigure[];
    byProcessing: StatusFigure[];
  } | null;
  leave: { pending: number };
  team: { active: number; total: number } | null;
}

export const dashboard = {
  summary: () => request<DashboardSummary>('/api/dashboard/summary'),
};

export const employees = {
  list: () => request<Employee[]>('/api/employees'),
};

/**
 * What POST /api/users answers (#62). No password: the owner chooses one
 * through the activation link, and `activationEmailSent` says whether it left.
 */
export interface UserCreated {
  id: string;
  email: string;
  activationEmailSent: boolean;
}

export type UserUpdate = Partial<Pick<User, 'firstName' | 'lastName' | 'role' | 'isActive'>>;

const userPath = (id: string) => `/api/users/${encodeURIComponent(id)}`;

export const users = {
  list: () => request<User[]>('/api/users'),
  create: (body: { email: string; firstName: string; lastName: string; role: User['role'] }) =>
    request<UserCreated>('/api/users', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: string, body: UserUpdate) =>
    request<User>(userPath(id), { method: 'PATCH', body: JSON.stringify(body) }),
  /** Blocks the account and every session it holds. There is no delete. */
  deactivate: (id: string) => request<User>(`${userPath(id)}/deactivate`, { method: 'POST' }),
  resendActivation: (id: string) =>
    request<{ id: string; activationEmailSent: boolean }>(`${userPath(id)}/activation`, { method: 'POST' }),
};

/** A notification as the server keeps it (#116); the shape the bell already used. */
export interface ServerNotification {
  id: string;
  kind: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  /** Milliseconds since the epoch. */
  timestamp: number;
  link?: string | null;
  refType?: string | null;
  refId?: string | null;
}

/** The caller's notifications and how many are unread, read from the response headers. */
export interface NotificationPage {
  rows: ServerNotification[];
  total: number;
  unread: number;
}

/** What the website's contact form sends (#98). `website` is the honeypot: always empty from a person. */
export interface ContactSubmission {
  name: string;
  email: string;
  topic: string;
  message: string;
  website: string;
}

/** An enquiry from the contact form, as the admin reads it (#98). */
export interface ContactRequest {
  id: string;
  createdAt: string;
  name: string;
  email: string;
  topic: string;
  message: string;
  handledAt?: string | null;
  handledBy?: string | null;
}

/** The public contact form: no sign-in needed. */
export const contact = {
  send: (body: ContactSubmission) =>
    request<{ message: string }>('/api/contact', { method: 'POST', body: JSON.stringify(body) }),
};

/** The admin's inbox of enquiries (#98). */
export const contactRequests = {
  page: ({ handled, limit, offset }: { handled?: boolean; limit: number; offset: number }) =>
    requestPage<ContactRequest>(
      `/api/contact-requests?${new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
        ...(handled === undefined ? {} : { handled: String(handled) }),
      })}`,
    ),
  handle: (id: string) => request<ContactRequest>(`/api/contact-requests/${id}/handle`, { method: 'POST' }),
};

export const notifications = {
  /** The caller's own notifications, unread first (#116). */
  list: async (limit = 50): Promise<NotificationPage> => {
    let total = 0;
    let unread = 0;
    const rows = await request<ServerNotification[]>(`/api/notifications?limit=${limit}`, {}, (res) => {
      total = Number(res.headers.get('X-Total-Count') ?? 0);
      unread = Number(res.headers.get('X-Unread-Count') ?? 0);
    });
    return { rows, total, unread };
  },
  read: (id: string) => request<ServerNotification>(`/api/notifications/${id}/read`, { method: 'POST' }),
  readAll: () => request<{ updated: number }>('/api/notifications/read-all', { method: 'POST' }),
  dismiss: (id: string) => request<void>(`/api/notifications/${id}/dismiss`, { method: 'POST' }),
  dismissAll: () => request<{ dismissed: number }>('/api/notifications/dismiss-all', { method: 'POST' }),
};
