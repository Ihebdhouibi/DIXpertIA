import React, { useState } from 'react';
import { FileText, Download, Calendar, DollarSign, Wallet, CreditCard, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { Payslip, UserRole } from '../types';

interface PayslipsViewProps {
  payslips: Payslip[];
  userRole: UserRole;
}

export default function PayslipsView({ payslips, userRole }: PayslipsViewProps) {
  const [selectedYear, setSelectedYear] = useState('2024');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 4;

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleDownload = (slip: Payslip) => {
    // Use print fallback to generate a simple PDF
    const win = window.open('', '_blank');
    if (!win) {
      showToast('Please allow pop-ups to download the payslip.');
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

  // Filter and paginated list
  const filteredPayslips = payslips.filter(p => p.issuedOn.includes(selectedYear));
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPayslips.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredPayslips.length / itemsPerPage);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

  // Only employees, accountants and admins can see payslips
  if (userRole !== 'employee' && userRole !== 'accountant' && userRole !== 'admin') {
    return <div className="p-8 text-center text-on-surface-variant">Access Denied</div>;
  }

  return (
    <div className="flex-1 flex flex-col gap-6">
      
      {/* Toast Alert Notification */}
      {toastMessage && (
        <div className="fixed bottom-4 right-4 z-50 bg-[#137333] text-white py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border border-white/20">
          <Check className="w-5 h-5 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

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
        
        {/* Period Filter */}
        <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-outline-variant shadow-sm w-full md:w-auto">
          <Calendar className="text-outline w-5 h-5" />
          <select
            value={selectedYear}
            onChange={(e) => {
              setSelectedYear(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-transparent border-none text-on-surface font-semibold text-body-sm focus:outline-none cursor-pointer py-1 pr-6 w-full md:w-32"
          >
            <option value="2024">2024</option>
            <option value="2023">2023</option>
            <option value="2022">2022</option>
          </select>
        </div>
      </div>

      {/* Bento Style Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col gap-2 relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="absolute top-0 right-0 p-4 opacity-[0.04] text-primary group-hover:scale-110 transition-transform">
            <Wallet className="w-20 h-20" />
          </div>
          <span className="text-body-sm font-medium text-on-surface-variant">YTD Gross</span>
          <span className="text-h1 font-bold text-on-surface tracking-tight">$84,500.00</span>
          <div className="text-xs text-outline mt-1 font-medium">Cumulé brut pour l'année {selectedYear}</div>
        </div>

        <div className="bg-white rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col gap-2 relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="absolute top-0 right-0 p-4 opacity-[0.04] text-secondary group-hover:scale-110 transition-transform">
            <DollarSign className="w-20 h-20" />
          </div>
          <span className="text-body-sm font-medium text-on-surface-variant">YTD Net</span>
          <span className="text-h1 font-bold text-on-surface tracking-tight">$62,180.00</span>
          <div className="text-xs text-outline mt-1 font-medium">Cumulé net pour l'année {selectedYear}</div>
        </div>

        <div className="bg-primary-container text-white rounded-xl p-6 shadow-md flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#ffffff_1px,transparent_1px)] bg-[size:16px_16px]"></div>
          <div className="absolute top-0 right-0 p-4 opacity-25">
            <CreditCard className="w-16 h-16" />
          </div>
          <span className="text-body-sm font-medium opacity-85 z-10">Next Pay Date</span>
          <span className="text-h1 font-black z-10 tracking-tight">Oct 31, 2024</span>
          <div className="text-xs opacity-75 mt-1 font-medium z-10">Virement automatique programmé</div>
        </div>
      </div>

      {/* Payslips Data Table Container */}
      <div className="bg-white rounded-xl border border-outline-variant shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-low/50">
                <th className="py-4 px-6 font-semibold text-body-sm text-on-surface-variant">Period</th>
                <th className="py-4 px-6 font-semibold text-body-sm text-on-surface-variant text-right">Gross Pay</th>
                <th className="py-4 px-6 font-semibold text-body-sm text-on-surface-variant text-right">Net Pay</th>
                <th className="py-4 px-6 font-semibold text-body-sm text-on-surface-variant">Issued On</th>
                <th className="py-4 px-6 font-semibold text-body-sm text-on-surface-variant text-right">Action</th>
              </tr>
            </thead>
            <tbody className="text-body-sm text-on-surface divide-y divide-outline-variant/40">
              {currentItems.length > 0 ? (
                currentItems.map((slip) => (
                  <tr
                    key={slip.id}
                    className="hover:bg-surface-container-low transition-colors group"
                  >
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all">
                          <FileText className="w-4 h-4" />
                        </div>
                        <span className="font-semibold text-on-surface">{slip.period}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-right font-mono text-on-surface-variant">
                      {formatCurrency(slip.grossPay)}
                    </td>
                    <td className="py-4 px-6 text-right font-mono font-bold text-primary">
                      {formatCurrency(slip.netPay)}
                    </td>
                    <td className="py-4 px-6 text-on-surface-variant font-medium">
                      {slip.issuedOn}
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => handleDownload(slip)}
                        className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-primary hover:bg-primary/10 transition-colors cursor-pointer"
                        title="Download PDF"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-12 px-6 text-center text-on-surface-variant font-medium">
                    No payslips found for the selected year.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Block */}
        {filteredPayslips.length > 0 && (
          <div className="px-6 py-4 border-t border-outline-variant flex items-center justify-between bg-surface-container-lowest">
            <span className="text-caption text-on-surface-variant font-medium">
              Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredPayslips.length)} of {filteredPayslips.length}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="p-1.5 rounded border border-outline-variant text-on-surface-variant hover:bg-surface-container-low transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-1.5 rounded border border-outline-variant text-on-surface-variant hover:bg-surface-container-low transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}