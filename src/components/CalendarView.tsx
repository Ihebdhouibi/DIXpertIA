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
    // Filter requests based on role
    let filtered = leaveRequests;
    if (userRole === 'employee' && currentUserId) {
      filtered = leaveRequests.filter(req => req.employeeId === currentUserId);
    }

    return filtered.map((req): CalendarEvent => {
      // Parse dates from the "dates" string (e.g., "Oct 12 - Oct 16, 2024")
      const dateParts = req.dates.split(' - ');
      const startStr = dateParts[0];
      const endStr = dateParts.length > 1 ? dateParts[1] : startStr;
      // Append year if missing (we assume current year)
      const year = new Date().getFullYear();
      const startDate = parse(`${startStr}, ${year}`, 'MMM dd, yyyy', new Date());
      const endDate = parse(`${endStr}, ${year}`, 'MMM dd, yyyy', new Date());
      // For single day, end date should be same day (calendar needs end exclusive, so we add a day)
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
    });
  }, [leaveRequests, userRole, currentUserId]);

  const eventStyleGetter = (event: CalendarEvent) => {
    let backgroundColor = '#6b7280'; // default gray
    switch (event.status) {
      case 'Approved':
        backgroundColor = '#10b981'; // green
        break;
      case 'Pending':
        backgroundColor = '#f59e0b'; // yellow
        break;
      case 'Rejected':
        backgroundColor = '#ef4444'; // red
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
    alert(`Leave Request: ${req.employeeName}\nType: ${req.type}\nDates: ${req.dates}\nDuration: ${req.duration} days\nStatus: ${req.status}\nReason: ${req.reason || 'N/A'}`);
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