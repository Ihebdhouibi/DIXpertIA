import { createContext, useContext } from 'react';

/**
 * Whether App's data load is in flight or failed (#28), so a list can show a
 * designed loading or error state instead of "No results" while it is still
 * empty for another reason.
 */
export interface DataStatus {
  loading: boolean;
  error: string | null;
  retry: () => void;
}

export const DataStatusContext = createContext<DataStatus>({ loading: false, error: null, retry: () => {} });

export function useDataStatus(): DataStatus {
  return useContext(DataStatusContext);
}
