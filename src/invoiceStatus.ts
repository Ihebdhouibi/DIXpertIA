import type { Invoice } from './types';

/**
 * Invoice states in the UI's vocabulary and the API's (#113). The API filters
 * take the enum values (`statut=payee`, `processing_status=pending`); the list
 * returns English labels. One table each way, so the two never drift.
 */
export type CommercialStatus = Invoice['status'];
export type ProcessingStatus = Invoice['processingStatus'];

export const COMMERCIAL_STATUSES: readonly CommercialStatus[] = ['Draft', 'Sent', 'Paid', 'Overdue', 'Cancelled'];
export const PROCESSING_STATUSES: readonly ProcessingStatus[] = ['Pending', 'Processed', 'Completed', 'Archived'];

/** The accountant's verification before sending (#118). */
export type ReviewStatus = Invoice['reviewStatus'];
export const REVIEW_STATUSES: readonly ReviewStatus[] = ['Not submitted', 'Submitted', 'Approved', 'Rejected'];
export const REVIEW_TO_API: Record<ReviewStatus, string> = {
  'Not submitted': 'not_submitted',
  Submitted: 'submitted',
  Approved: 'approved',
  Rejected: 'rejected',
};
/** How each review state reads in the UI: "Submitted" is the accountant's "to verify". */
export const REVIEW_LABEL: Record<ReviewStatus, string> = {
  'Not submitted': 'Draft',
  Submitted: 'To verify',
  Approved: 'Approved',
  Rejected: 'Rejected',
};

/**
 * Whether the books can take an invoice yet. Bookkeeping starts when it is
 * sent (#118); the server refuses a draft, so the UI does not offer it.
 */
export const bookable = (invoice: Invoice) => invoice.status !== 'Draft';

export const COMMERCIAL_TO_API: Record<CommercialStatus, string> = {
  Draft: 'brouillon',
  Sent: 'envoyee',
  Paid: 'payee',
  Overdue: 'en_retard',
  Cancelled: 'annulee',
};

export const PROCESSING_TO_API: Record<ProcessingStatus, string> = {
  Pending: 'pending',
  Processed: 'processed',
  Completed: 'completed',
  Archived: 'archived',
};

/**
 * The accountant's next step for one invoice: pending -> processed ->
 * completed. Null after that - archiving is not a per-invoice action, it
 * happens when the month is closed (#99), which archives every completed
 * invoice of the month at once and refuses while work is unfinished.
 */
export function nextProcessingStatus(status: ProcessingStatus): ProcessingStatus | null {
  if (status === 'Pending') return 'Processed';
  if (status === 'Processed') return 'Completed';
  return null;
}

/** The label of the action that moves an invoice to `status`. */
export const PROCESSING_ACTION: Partial<Record<ProcessingStatus, string>> = {
  Processed: 'Mark processed',
  Completed: 'Mark completed',
};

/** The same action, shortened for the row button where width is scarce. */
export const PROCESSING_ACTION_SHORT: Partial<Record<ProcessingStatus, string>> = {
  Processed: 'Process',
  Completed: 'Complete',
};
