export type UserRole = 'employee' | 'admin';

export interface User {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  avatarUrl?: string;
  role: UserRole;
  department?: string;
}

export interface Payslip {
  id: string;
  period: string;
  grossPay: number;
  netPay: number;
  issuedOn: string;
  pdfUrl?: string;
}

export interface LeaveRequest {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  type: 'Annual Leave' | 'Sick Leave' | 'Personal Day' | 'Unpaid Leave';
  dates: string;
  duration: number;
  status: 'Approved' | 'Pending' | 'Rejected';
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
  avatarUrl?: string;
  initials?: string;
}

export interface Invoice {
  id: string;
  client: string;
  clientInitials: string;
  amount: number;
  dateIssued: string;
  dueDate: string;
  status: 'Draft' | 'Sent' | 'Paid' | 'Overdue';
  items: {
    description: string;
    qty: number;
    price: number;
    total: number;
  }[];
}
