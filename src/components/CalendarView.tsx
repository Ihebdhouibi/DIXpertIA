import React, { useMemo, useState } from 'react';
import { Calendar, dateFnsLocalizer, Views, View, type Messages } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS, fr } from 'date-fns/locale';
import { LeaveRequest, UserRole } from '../types';
import StatusBadge, { statusTone } from './StatusBadge';
import Dialog from './ui/Dialog';
import { labelOf, useLocale, useT } from '../i18n';
import 'react-big-calendar/lib/css/react-big-calendar.css';
// Brand and theme overrides for the library's colours; must load after it (#79).
import '../styles/calendar.css';

// Keyed by the app's languages: the calendar's `culture` is useLocale().
const locales = { fr, en: enUS };
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
  const t = useT();
  const locale = useLocale();

  const messages: Messages<CalendarEvent> = {
    today: t('people.calendar.today'),
    previous: t('people.calendar.previous'),
    next: t('people.calendar.next'),
    month: t('people.calendar.month'),
    week: t('people.calendar.week'),
    day: t('people.calendar.day'),
    agenda: t('people.calendar.agenda'),
    date: t('people.calendar.date'),
    time: t('people.calendar.time'),
    event: t('people.calendar.event'),
    allDay: t('people.calendar.allDay'),
    noEventsInRange: t('people.calendar.noEvents'),
    showMore: (count) => t('people.calendar.showMore', { count }),
  };

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
          return null;
        }
        const end = new Date(last);
        end.setDate(end.getDate() + 1);

        return {
          id: req.id,
          // The status in words as well as in colour (#31, WCAG 1.4.1): a hover
          // tooltip alone reached neither keyboard, touch nor colour-blind users.
          title: `${req.employeeName} - ${labelOf(t, 'common.leaveType', req.type)} · ${labelOf(t, 'common.status', req.status)}`,
          start,
          end,
          allDay: true,
          status: req.status,
          resource: req,
        };
      })
      .filter((event): event is CalendarEvent => event !== null);
    // t changes with the language; `locale` stands for it in the dependencies.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leaveRequests, userRole, currentEmployeeId, locale]);

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

  // Leave details open in a themed dialog; this used to be a browser alert() (#106).
  const [selected, setSelected] = useState<LeaveRequest | null>(null);
  const handleSelectEvent = (event: CalendarEvent) => setSelected(event.resource);

  return (
    <Dialog open onClose={onClose} title={t('people.calendar.title')} size="full" bodyClassName="p-4 overflow-auto">
      <Calendar
        localizer={localizer}
        culture={locale}
        messages={messages}
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
          [
            event.resource.employeeName,
            labelOf(t, 'common.leaveType', event.resource.type),
            event.resource.dates,
            t('people.calendar.statusLine', { status: labelOf(t, 'common.status', event.resource.status) }),
          ].join('\n')
        }
      />

      <Dialog
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? `${selected.employeeName} - ${labelOf(t, 'common.leaveType', selected.type)}` : ''}
        size="sm"
        headerActions={selected && <StatusBadge status={selected.status} />}
      >
        {selected && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
            <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant pt-0.5">{t('people.col.dates')}</dt>
            <dd className="font-mono">{selected.dates}</dd>
            <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant pt-0.5">{t('people.col.duration')}</dt>
            <dd className="font-mono">{t('people.days', { count: selected.duration })}</dd>
            <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant pt-0.5">{t('people.col.reason')}</dt>
            <dd>{selected.reason || '-'}</dd>
            {selected.rejectionReason && (
              <>
                <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant pt-0.5">{t('people.calendar.rejected')}</dt>
                <dd>{selected.rejectionReason}</dd>
              </>
            )}
          </dl>
        )}
      </Dialog>
    </Dialog>
  );
}
