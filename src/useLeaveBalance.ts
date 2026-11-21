import { useEffect, useState } from 'react';
import { leaveBalances } from './api';
import type { LeaveBalance } from './types';

export type LeaveBalanceState =
  | { status: 'loading' }
  | { status: 'ready'; byType: Partial<Record<LeaveBalance['type'], LeaveBalance>> }
  // No employee record behind the account, or the request failed.
  | { status: 'unavailable' };

/** The signed-in person's leave balance for the current year (#121). */
export function useLeaveBalance(): LeaveBalanceState {
  const [state, setState] = useState<LeaveBalanceState>({ status: 'loading' });

  useEffect(() => {
    let alive = true;
    leaveBalances.get()
      .then(({ balances }) => {
        if (alive) setState({ status: 'ready', byType: Object.fromEntries(balances.map((b) => [b.type, b])) });
      })
      .catch(() => {
        if (alive) setState({ status: 'unavailable' });
      });
    return () => {
      alive = false;
    };
  }, []);

  return state;
}
