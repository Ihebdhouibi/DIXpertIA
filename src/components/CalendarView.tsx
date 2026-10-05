import React, { useMemo, useState } from 'react';
import { Calendar, dateFnsLocalizer, Views, View } from 'react-big-calendar';
import { X } from 'lucide-react';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { LeaveRequest, UserRole } from '../types';
import { statusTone } from './StatusBadge';
import 'react-big-calendar/lib/css/react-big-calendar.css';
// Brand and theme overrides for the library's colours; must load after it (#79).
import '../styles/calendar.css';

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
  currentEmployeeId?: number;
  onClose: () => void;
}

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  status: string;
  resource?: any;
}

/** 'YYYY-MM-DD' as a local date. `new Date('2026-10-12')` would be UTC midnight
 * and land on the previous day west of Greenwich. */
function parseLocalDate(value: string | undefined): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value ?? '');
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return isNaN(date.getTime()) ? null : date;
}

export default function CalendarView({ leaveRequests, userRole, currentEmployeeId, onClose }: CalendarViewProps) {
  // View and date are controlled here. Left to the library (defaultView /
  // defaultDate), its internal state never updated under React 19: Back,
  // Next, Week and Day did nothing and the calendar stayed on this month (#79).
  const [view, setView] = useState<View>(Views.MONTH);
  const [date, setDate] = useState(() => new Date());

  const events = useMemo(() => {
    let filtered = leaveRequests;
    if (userRole === 'employee' && currentEmployeeId) {
      filtered = leaveRequests.filter(req => req.employeeId === currentEmployeeId);
    }

    // Built from the ISO startDate / endDate the API returns, not from the
    // display string `dates`: its format changed with #104 ("Oct 12 - 14, 2026")
    // and the old parser turned every range into an invalid date, so no event
    // rendered. Leave is whole days; react-big-calendar treats an all-day end
    // as exclusive, so the end is moved to the next day to include the last one.
    return filtered
      .map((req): CalendarEvent | null => {
        const start = parseLocalDate(req.startDate);
        const last = parseLocalDate(req.endDate);
        if (!start || !last) {
          console.warn('Leave request with an invalid date range:', req.id, req.startDate, req.endDate);
          return null;
        }
        const end = new Date(last);
        end.setDate(end.getDate() + 1);

        return {
          id: req.id,
          title: `${req.employeeName} - ${req.type}`,
          start,
          end,
          allDay: true,
          status: req.status,
          resource: req,
        };
      })
      .filter((event): event is CalendarEvent => event !== null);
  }, [leaveRequests, userRole, currentEmployeeId]);

  // Same tones as the status badges, as theme variables so events follow
  // light and dark. Tint fill with tone text and a tone edge: AA in both themes.
  const eventStyleGetter = (event: CalendarEvent) => {
    const tone = statusTone(event.status);
    return {
      style: {
        backgroundColor: `var(--color-${tone}-container)`,
        border: 'none',
        borderLeft: `3px solid var(--color-${tone})`,
        borderRadius: '4px',
        color: `var(--color-${tone})`,
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
      <div className="bg-surface-container-lowest rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
          <h2 className="text-h2 font-black text-on-surface">Leave Calendar</h2>
          <button
            onClick={onClose}
            aria-label="Close calendar"
            className="p-2 hover:bg-surface-container rounded-lg text-on-surface-variant transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <div className="flex-1 p-4 overflow-auto">
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            date={date}
            onNavigate={setDate}
            style={{ height: '100%', minHeight: '500px' }}
            views={[Views.MONTH, Views.WEEK, Views.DAY]}
            view={view}
            onView={setView}
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
