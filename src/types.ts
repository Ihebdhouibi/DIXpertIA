/**
 * The API contract, as the UI sees it.
 *
 * These mirror the response schemas in `app/schemas/api.py`. They are not the
 * database columns: the backend translates French, snake_case columns into this
 * English, camelCase shape at the edge (#37), so a column rename never reaches
 * the frontend and the UI never has to know that `statut` and
 * `processing_status` are different things.
 *
 * Anything added here must exist in a response schema. Before #65 these types
 * described mock data instead, and drifted far enough that `Payslip` had no
 * link to an employee and `Invoice.amount` had no VAT.
 */
export type UserRole = 'employee' | 'admin' | 'accountant';

/** A login account. Mirrors UserOut; never carries a password hash or a reset token. */
export interface User {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  avatarUrl?: string;
  role: UserRole;
  department?: string;
  isActive: boolean;
  isVerified: boolean;
  createdAt: string;
}

/**
 * A person employed by the company. Separate from their login account since
 * #60, so someone can be offboarded without taking their payroll history with
 * them. Mirrors EmployeeOut, which joins the two back together for display.
 */
export interface Employee {
  id: number;
  userId: string;
  name: string;
  email: string;
  jobTitle?: string;
  role: UserRole;
  hiredOn: string;
  employmentStatus: 'active' | 'on_leave' | 'terminated';
  annualEntitlementDays: number;
}

export interface Payslip {
  id: string;
  employeeId?: number;
  period: string;
  grossPay: number;
  netPay: number;
  issuedOn?: string;
  pdfUrl?: string;
}

export interface LeaveRequest {
  id: string;
  employeeId?: number;
  employeeName: string;
  jobTitle?: string;
  type: 'Annual Leave' | 'Sick Leave' | 'Personal Day' | 'Unpaid Leave';
  /** A formatted range for display; startDate/endDate are the real values. */
  dates: string;
  startDate: string;
  endDate: string;
  duration: number;
  status: 'Approved' | 'Pending' | 'Rejected';
  reason?: string;
  rejectionReason?: string;
}

/** A company we invoice. Mirrors ClientOut. */
export interface Client {
  id: number;
  nom: string;
  email?: string;
  telephone?: string;
  adresse?: string;
}

export interface InvoiceItem {
  description: string;
  qty: number;
  price: number;
  total: number;
}

export interface Invoice {
  id: string;
  /** Always ours: FA-YYYY-NNNN outgoing, FF-YYYY-NNNN incoming (#38, #40). */
  numero: string;
  direction: 'outgoing' | 'incoming';
  /** The client we billed, or the supplier who billed us. */
  counterparty: string;
  counterpartyInitials: string;
  /** The supplier's own number, on an incoming invoice only. */
  supplierReference?: string | null;
  amountHT: number;
  amountTTC: number;
  dateIssued: string;
  dueDate: string;
  /** The commercial state the counterparty sees. */
  status: 'Draft' | 'Sent' | 'Paid' | 'Overdue' | 'Cancelled';
  /**
   * The accountant's workflow state (#41). A separate axis from `status`: an
   * invoice is routinely Paid and Pending at once - the client has paid,
   * nobody has booked it yet.
   */
  processingStatus: 'Pending' | 'Processed' | 'Completed' | 'Archived';
  items: InvoiceItem[];
}
