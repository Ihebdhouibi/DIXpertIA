import React, { useEffect, useMemo, useState } from 'react';
import { FileText, Download, DollarSign, Wallet, CreditCard } from 'lucide-react';
import { Payslip, UserRole } from '../types';
import { useToast, ToastTone } from './ui/feedback';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { Pagination } from './ui/TableControls';
import { Field, Select } from './ui/Field';
import { useDataStatus } from '../dataStatus';

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
          <h1>DIXpertIA Payslip</h1>
          <p><strong>Period:</strong> ${slip.period}</p>
          <p><strong>Gross Pay:</strong> $${slip.grossPay.toFixed(2)}</p>
          <p><strong>Net Pay:</strong> $${slip.netPay.toFixed(2)}</p>
          <p><strong>Issued On:</strong> ${slip.issuedOn}</p>
          <p><em>Generated from DIXpertIA</em></p>
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

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

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

      {/* Bento Style Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col gap-2 relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="absolute top-0 right-0 p-4 opacity-[0.04] text-primary group-hover:scale-110 transition-transform">
            <Wallet className="w-20 h-20" />
          </div>
          <span className="text-body-sm font-medium text-on-surface-variant">YTD Gross</span>
          <span className="text-h1 font-bold text-on-surface tracking-tight">$84,500.00</span>
          <div className="text-xs text-outline mt-1 font-medium">Cumulé brut pour l'année {selectedYear}</div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col gap-2 relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="absolute top-0 right-0 p-4 opacity-[0.04] text-secondary group-hover:scale-110 transition-transform">
            <DollarSign className="w-20 h-20" />
          </div>
          <span className="text-body-sm font-medium text-on-surface-variant">YTD Net</span>
          <span className="text-h1 font-bold text-on-surface tracking-tight">$62,180.00</span>
          <div className="text-xs text-outline mt-1 font-medium">Cumulé net pour l'année {selectedYear}</div>
        </div>

        <div className="bg-primary text-on-primary rounded-xl p-6 shadow-md flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute inset-0 opacity-15 bg-[radial-gradient(var(--color-on-primary)_1px,transparent_1px)] bg-[size:16px_16px]"></div>
          <div className="absolute top-0 right-0 p-4 opacity-25">
            <CreditCard className="w-16 h-16" />
          </div>
          <span className="text-body-sm font-medium opacity-85 z-10">Next Pay Date</span>
          <span className="text-h1 font-black z-10 tracking-tight">Oct 31, 2024</span>
          <div className="text-xs opacity-75 mt-1 font-medium z-10">Virement automatique programmé</div>
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
                <Td numeric muted>{formatCurrency(slip.grossPay)}</Td>
                <Td numeric className="font-semibold">{formatCurrency(slip.netPay)}</Td>
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
