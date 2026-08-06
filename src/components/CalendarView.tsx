import React, { useMemo } from 'react';
import { Calendar, dateFnsLocalizer, Views } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { LeaveRequest, UserRole } from '../types';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const locales = { 'en-US': enUS };
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

interface CalendarViewProps {
  leaveRequests: LeaveRequest[];
  userRole: UserRole;
  currentUserId?: string;
  onClose: () => void;
}

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  status: string;
  resource?: any;
}

export default function CalendarView({ leaveRequests, userRole, currentUserId, onClose }: CalendarViewProps) {
  const events = useMemo(() => {
    let filtered = leaveRequests;
    if (userRole === 'employee' && currentUserId) {
      filtered = leaveRequests.filter(req => req.employeeId === currentUserId);
    }

    console.log('📥 Filtered leave requests:', filtered);

    return filtered
      .map((req): CalendarEvent | null => {
        // Extract year from the date string (e.g., "Aug 10 - Aug 20, 2026")
        const yearMatch = req.dates.match(/\d{4}/);
        const year = yearMatch ? parseInt(yearMatch[0]) : new Date().getFullYear();

        // Split the date range
        const parts = req.dates.split(' - ');
        const startStr = parts[0].trim();
        const endStr = parts.length > 1 ? parts[1].trim() : startStr;

        // Build full date strings with year
        const startFull = `${startStr}, ${year}`;
        const endFull = `${endStr}, ${year}`;

        // Parse using JavaScript Date (works for "Aug 10, 2026")
        const startDate = new Date(startFull);
        const endDate = new Date(endFull);

        // Validate
        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
          console.warn('⚠️ Invalid date for request:', req.id, req.dates);
          return null;
        }

        // For single-day events, add one day to make it a full-day event
        const endDateAdjusted = new Date(endDate);
        if (endDateAdjusted.getTime() === startDate.getTime()) {
          endDateAdjusted.setDate(endDateAdjusted.getDate() + 1);
        }

        return {
          id: req.id,
          title: `${req.employeeName} - ${req.type}`,
          start: startDate,
          end: endDateAdjusted,
          status: req.status,
          resource: req,
        };
      })
      .filter((event): event is CalendarEvent => event !== null);
  }, [leaveRequests, userRole, currentUserId]);

  console.log('📅 Generated events:', events);

  const eventStyleGetter = (event: CalendarEvent) => {
    let backgroundColor = '#6b7280';
    switch (event.status) {
      case 'Approved':
        backgroundColor = '#10b981';
        break;
      case 'Pending':
        backgroundColor = '#f59e0b';
        break;
      case 'Rejected':
        backgroundColor = '#ef4444';
        break;
    }
    return {
      style: {
        backgroundColor,
        border: 'none',
        borderRadius: '4px',
        color: 'white',
        padding: '2px 4px',
        fontSize: '0.75rem',
      },
    };
  };

  const handleSelectEvent = (event: CalendarEvent) => {
    const req = event.resource;
    alert(
      `Leave Request: ${req.employeeName}\n` +
      `Type: ${req.type}\n` +
      `Dates: ${req.dates}\n` +
      `Duration: ${req.duration} days\n` +
      `Status: ${req.status}\n` +
      `Reason: ${req.reason || 'N/A'}`
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
          <h2 className="text-h2 font-black text-on-surface">Leave Calendar</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-container rounded-lg text-on-surface-variant transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 p-4 overflow-auto">
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            defaultDate={new Date()}
            style={{ height: '100%', minHeight: '500px' }}
            views={[Views.MONTH, Views.WEEK, Views.DAY]}
            defaultView={Views.MONTH}
            eventPropGetter={eventStyleGetter}
            onSelectEvent={handleSelectEvent}
            tooltipAccessor={(event) =>
              `${event.resource.employeeName}\n${event.resource.type}\n${event.resource.dates}\nStatus: ${event.resource.status}`
            }
          />
        </div>
      </div>
    </div>
  );
}