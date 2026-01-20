import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { SummaryResponse } from '../types';
import { getApiErrorMessage } from '../utils/errors';

interface SummaryState {
  balance: string;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useSummary(): SummaryState {
  const [balance, setBalance] = useState('0.00');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<SummaryResponse>('/summary');
      setBalance(data.balance);
      setError(null);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return useMemo(
    () => ({ balance, loading, error, refresh }),
    [balance, loading, error, refresh]
  );
}
