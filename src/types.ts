export type UserRole = 'admin' | 'employee' | 'accountant';

export interface User {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: UserRole;
  department?: string;
  avatarUrl?: string;
  isActive: boolean;
  isVerified: boolean;
  createdAt: string;
}

export interface Payslip {
  id: string;
  period: string;
  grossPay: number;
  netPay: number;
  issuedOn: string;
}

export type LeaveStatus = 'Pending' | 'Approved' | 'Rejected';

export interface LeaveRequest {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  type: 'Annual Leave' | 'Sick Leave' | 'Personal Day' | 'Unpaid Leave';
  dates: string;
  duration: number;
  status: LeaveStatus;
  reason?: string;
  rejectionReason?: string;
}

export interface TeamMember {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  status: 'Active' | 'Inactive';
  initials?: string;
  avatarUrl?: string;
}

export interface InvoiceItem {
  description: string;
  qty: number;
  price: number;
  total: number;
}

export interface Invoice {
  id: string;
  client: string;
  clientInitials: string;
  amount: number;
  dateIssued: string;
  dueDate: string;
  status: 'Draft' | 'Sent' | 'Paid' | 'Overdue';
  items: InvoiceItem[];
}

export interface Project {
  id: string;
  name: string;
  client: string;
  description?: string;
  status: 'Active' | 'In Progress' | 'Completed' | 'On Hold';
  deadline: string;
  teamMembers: string[];
  createdAt: string;
}