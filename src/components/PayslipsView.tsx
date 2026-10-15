import React, { useEffect, useMemo, useState } from 'react';
import { FileText, Download, Wallet, Banknote } from 'lucide-react';
import { Payslip, UserRole } from '../types';
import { useToast, ToastTone } from './ui/feedback';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { Pagination } from './ui/TableControls';
import { Field, Select } from './ui/Field';
import { useDataStatus } from '../dataStatus';
import { formatTND } from '../format';

interface PayslipsViewProps {
  payslips: Payslip[];
  userRole: UserRole;
}

export default function PayslipsView({ payslips, userRole }: PayslipsViewProps) {
  const [selectedYear, setSelectedYear] = useState('');
  const status = useDataStatus();
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 4;

  const toast = useToast();
  const showToast = (message: string, tone: ToastTone = 'success') => toast(message, tone);

  const handleDownload = (slip: Payslip) => {
    // Use print fallback to generate a simple PDF
    const win = window.open('', '_blank');
    if (!win) {
      showToast('Please allow pop-ups to download the payslip.', 'error');
      return;
    }

    const content = `
      <html>
        <head><title>Payslip ${slip.period}</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px;">
          <h1>DI Xpertia payslip</h1>
          <p><strong>Period:</strong> ${slip.period}</p>
          <p><strong>Gross pay:</strong> ${formatTND(slip.grossPay)}</p>
          <p><strong>Net pay:</strong> ${formatTND(slip.netPay)}</p>
          <p><strong>Issued on:</strong> ${slip.issuedOn ?? '-'}</p>
          <p><em>Generated from DI Xpertia</em></p>
        </body>
      </html>
    `;

    win.document.write(content);
    win.document.close();
    win.print();
    showToast(`Payslip ${slip.period} opened for printing.`);
  };

  // Years come from the payslips themselves, most recent first, and the most
  // recent is selected by default. The filter used to default to a hard-coded
  // "2024" (options 2024-2022), hiding every current payslip, and it called
  // issuedOn.includes() although issuedOn is optional.
  const yearOf = (p: Payslip) => (p.period.match(/\d{4}/) ?? p.issuedOn?.match(/\d{4}/))?.[0] ?? '';
  const years = useMemo(
    () => Array.from(new Set(payslips.map(yearOf).filter(Boolean))).sort().reverse(),
    [payslips]
  );
  useEffect(() => {
    if (!years.includes(selectedYear)) setSelectedYear(years[0] ?? '');
  }, [years, selectedYear]);

  // Filter and paginated list
  const filteredPayslips = selectedYear ? payslips.filter(p => yearOf(p) === selectedYear) : payslips;
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPayslips.slice(indexOfFirstItem, indexOfLastItem);

  // Year-to-date figures from the payslips actually loaded for the year (#123).
  // They replaced "$84,500.00", "$62,180.00" and a "Next Pay Date" of Oct 31,
  // 2024 that were written in the code, the same for everyone. The server
  // scopes the list: an employee's own payslips, or the whole payroll for an
  // admin or accountant, so the totals and their labels follow that scope.
  const wholePayroll = userRole === 'admin' || userRole === 'accountant';
  const ytdGross = filteredPayslips.reduce((sum, p) => sum + p.grossPay, 0);
  const ytdNet = filteredPayslips.reduce((sum, p) => sum + p.netPay, 0);
  const countLabel = filteredPayslips.length === 0
    ? 'No payslips yet'
    : `${filteredPayslips.length} payslip${filteredPayslips.length === 1 ? '' : 's'}${selectedYear ? ` in ${selectedYear}` : ''}`;

  // Only employees, accountants and admins can see payslips
  if (userRole !== 'employee' && userRole !== 'accountant' && userRole !== 'admin') {
    return <div className="p-8 text-center text-on-surface-variant">Access Denied</div>;
  }

  return (
    <div className="flex-1 flex flex-col gap-6">

      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">
            {userRole === 'admin' || userRole === 'accountant' ? 'All Payslips' : 'My Payslips'}
          </h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            {userRole === 'admin' || userRole === 'accountant'
              ? 'View and download all employee payslips.'
              : 'View and download your monthly salary statements.'}
          </p>
        </div>

        {/* Period filter */}
        {years.length > 0 && (
          <Field label="Year" className="w-full md:w-36">
            {({ id }) => (
              <Select
                id={id}
                value={selectedYear}
                onChange={(e) => {
                  setSelectedYear(e.target.value);
                  setCurrentPage(1);
                }}
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
      </div>

      {/* Year to date, from the real payslips (#123) */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="relative flex flex-col gap-2 overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest p-6">
          <div className="absolute right-0 top-0 p-4 text-on-surface opacity-[0.05]" aria-hidden="true">
            <Wallet className="h-20 w-20" />
          </div>
          <span className="text-body-sm font-medium text-on-surface-variant">
            {wholePayroll ? 'Payroll, gross' : 'Your gross pay'}{selectedYear ? `, ${selectedYear}` : ''}
          </span>
          <span className="font-mono text-h2 font-semibold tabular-nums text-on-surface">{formatTND(ytdGross)}</span>
          <div className="text-xs font-medium text-on-surface-variant">{countLabel}</div>
        </div>

        <div className="relative flex flex-col gap-2 overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest p-6">
          <div className="absolute right-0 top-0 p-4 text-on-surface opacity-[0.05]" aria-hidden="true">
            <Banknote className="h-20 w-20" />
          </div>
          <span className="text-body-sm font-medium text-on-surface-variant">
            {wholePayroll ? 'Payroll, net' : 'Your net pay'}{selectedYear ? `, ${selectedYear}` : ''}
          </span>
          <span className="font-mono text-h2 font-semibold tabular-nums text-on-surface">{formatTND(ytdNet)}</span>
          <div className="text-xs font-medium text-on-surface-variant">{countLabel}</div>
        </div>
      </div>

      {/* Payslips */}
      <Table
        caption="Payslips"
        footer={
          filteredPayslips.length > 0 && (
            <Pagination
              page={currentPage}
              pageSize={itemsPerPage}
              total={filteredPayslips.length}
              onPageChange={setCurrentPage}
              noun="payslips"
            />
          )
        }
      >
        <THead>
          <Th>Period</Th>
          <Th numeric>Gross pay</Th>
          <Th numeric>Net pay</Th>
          <Th numeric>Issued</Th>
          <Th numeric>
            <span className="sr-only">Download</span>
          </Th>
        </THead>
        <TBody>
          {currentItems.length > 0 ? (
            currentItems.map((slip) => (
              <Tr key={slip.id}>
                <Td>
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-container-high text-on-surface-variant">
                      <FileText className="w-4 h-4" aria-hidden="true" />
                    </span>
                    <span className="font-semibold">{slip.period}</span>
                  </div>
                </Td>
                <Td numeric muted>{formatTND(slip.grossPay)}</Td>
                <Td numeric className="font-semibold">{formatTND(slip.netPay)}</Td>
                <Td numeric muted>{slip.issuedOn ?? '-'}</Td>
                <Td numeric>
                  <button
                    type="button"
                    onClick={() => handleDownload(slip)}
                    aria-label={`Download payslip ${slip.period}`}
                    className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                  >
                    <Download className="w-4 h-4" aria-hidden="true" />
                  </button>
                </Td>
              </Tr>
            ))
          ) : status.loading ? (
            <TableState kind="loading" colSpan={5} title="Loading payslips..." />
          ) : status.error && payslips.length === 0 ? (
            <TableState kind="error" colSpan={5} message={status.error} />
          ) : (
            <TableState
              kind="empty"
              colSpan={5}
              title={payslips.length === 0 ? 'No payslips yet' : `No payslips in ${selectedYear}`}
            />
          )}
        </TBody>
      </Table>
    </div>
  );
}
