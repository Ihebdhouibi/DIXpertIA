import { Payslip, LeaveRequest, TeamMember, Invoice, Project } from './types';

export const initialPayslips: Payslip[] = [
  { "id": 'PS-001', "period": 'September 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Sep 30, 2024' },
  { "id": 'PS-002', "period": 'August 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Aug 31, 2024' },
  { "id": 'PS-003', "period": 'July 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Jul 31, 2024' },
  { "id": 'PS-004', "period": 'June 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Jun 30, 2024' },
  { "id": 'PS-005', "period": 'May 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'May 31, 2024' },
  { "id": 'PS-006', "period": 'April 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Apr 30, 2024' },
  { "id": 'PS-007', "period": 'March 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Mar 31, 2024' },
  { "id": 'PS-008', "period": 'February 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Feb 29, 2024' },
  { "id": 'PS-009', "period": 'January 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Jan 31, 2024' }
];

export const initialLeaveRequests: LeaveRequest[] = [
  {
    "id": 'LR-001',
    "employeeId": 'EMP-01',
    "employeeName": 'Alice Smith',
    "department": 'Engineering',
    "type": 'Annual Leave',
    "dates": 'Oct 12 - Oct 16, 2026',
    "duration": 5,
    "status": 'Approved',
    "reason": 'Family trip to the mountains'
  },
  {
    "id": 'LR-002',
    "employeeId": 'EMP-02',
    "employeeName": 'John Doe',
    "department": 'Marketing',
    "type": 'Sick Leave',
    "dates": 'Sep 01, 2026',
    "duration": 1,
    "status": 'Approved',
    "reason": 'Medical appointment'
  },
  {
    "id": 'LR-003',
    "employeeId": 'EMP-02',
    "employeeName": 'John Doe',
    "department": 'Marketing',
    "type": 'Personal Day',
    "dates": 'Nov 20, 2026',
    "duration": 1,
    "status": 'Pending',
    "reason": 'Urgent family matter'
  }
];

export const initialTeamMembers: TeamMember[] = [
  {
    "id": 'TM-001',
    "firstName": 'Sarah',
    "lastName": 'Jenkins',
    "email": 'sarah.j@dixpertia.com',
    "role": 'Senior Developer',
    "status": 'Active',
    "avatarUrl": 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=150&auto=format&fit=crop'
  },
  {
    "id": 'TM-002',
    "firstName": 'Marcus',
    "lastName": 'Rodriguez',
    "email": 'm.rodriguez@dixpertia.com',
    "role": 'Project Manager',
    "status": 'Active',
    "initials": 'MR'
  },
  {
    "id": 'TM-003',
    "firstName": 'David',
    "lastName": 'Chen',
    "email": 'd.chen@dixpertia.com',
    "role": 'System Administrator',
    "status": 'Inactive',
    "avatarUrl": 'https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=150&auto=format&fit=crop'
  },
  {
    "id": 'TM-004',
    "firstName": 'Amina',
    "lastName": 'Khalid',
    "email": 'a.khalid@dixpertia.com',
    "role": 'Security Analyst',
    "status": 'Active',
    "initials": 'AK'
  },
  {
    "id": 'TM-005',
    "firstName": 'John',
    "lastName": 'Doe',
    "email": 'john.doe@dixpertia.com',
    "role": 'Junior Developer',
    "status": 'Active',
    "avatarUrl": 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=150&auto=format&fit=crop'
  },
  {
    "id": 'TM-006',
    "firstName": 'Alice',
    "lastName": 'Smith',
    "email": 'alice.smith@dixpertia.com',
    "role": 'DevOps Engineer',
    "status": 'Active',
    "initials": 'AS'
  }
];

export const initialInvoices: Invoice[] = [
  {
    "id": 'INV-2024-001',
    "client": 'Acme Corp',
    "clientInitials": 'AC',
    "amount": 12450.00,
    "dateIssued": 'Oct 12, 2024',
    "dueDate": 'Nov 11, 2024',
    "status": 'Sent',
    "items": [
      { "description": 'Cloud Infrastructure Setup', "qty": 1, "price": 5000.00, "total": 5000.00 },
      { "description": 'Security Audit Phase 1', "qty": 1, "price": 3450.00, "total": 3450.00 },
      { "description": 'Enterprise Support (Monthly)', "qty": 2, "price": 2000.00, "total": 4000.00 }
    ]
  },
  {
    "id": 'INV-2024-002',
    "client": 'Global Tech',
    "clientInitials": 'G',
    "amount": 8200.00,
    "dateIssued": 'Oct 15, 2024',
    "dueDate": 'Oct 25, 2024',
    "status": 'Overdue',
    "items": [
      { "description": 'React Frontend Development', "qty": 40, "price": 150.00, "total": 6000.00 },
      { "description": 'Figma UX Design Consultation', "qty": 10, "price": 220.00, "total": 2200.00 }
    ]
  },
  {
    "id": 'INV-2024-003',
    "client": 'Stark Industries',
    "clientInitials": 'S',
    "amount": 45000.00,
    "dateIssued": 'Oct 01, 2024',
    "dueDate": 'Oct 31, 2024',
    "status": 'Paid',
    "items": [
      { "description": 'AI Logic Model Training & Validation', "qty": 1, "price": 30000.00, "total": 30000.00 },
      { "description": 'Kubernetes Cluster Provisioning', "qty": 3, "price": 5000.00, "total": 15000.00 }
    ]
  },
  {
    "id": 'INV-2024-004',
    "client": 'Wayne Ent.',
    "clientInitials": 'W',
    "amount": 3500.00,
    "dateIssued": '-',
    "dueDate": '-',
    "status": 'Draft',
    "items": [
      { "description": 'Security Patch Compliance Audit', "qty": 1, "price": 3500.00, "total": 3500.00 }
    ]
  }
];

export const initialProjects: Project[] = [
  {
    id: 'PRJ-001',
    name: 'Cloud Migration for Acme Corp',
    client: 'Acme Corp',
    description: 'Migrate on‑premise infrastructure to AWS with zero downtime.',
    status: 'In Progress',
    deadline: '2024-11-30',
    teamMembers: ['EMP-102', 'TM-001', 'TM-002'],
    createdAt: '2024-09-01',
  },
  {
    id: 'PRJ-002',
    name: 'Cybersecurity Audit – Global Tech',
    client: 'Global Tech',
    description: 'Full security audit and compliance review for ISO 27001.',
    status: 'Active',
    deadline: '2024-12-15',
    teamMembers: ['TM-004', 'ADMIN-01'],
    createdAt: '2024-10-01',
  },
];