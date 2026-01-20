import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { Income, IncomeListResponse, IncomePayload } from '../types';
import { getApiErrorMessage } from '../utils/errors';

interface IncomeState {
  items: Income[];
  total: string;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  create: (payload: IncomePayload) => Promise<void>;
  update: (id: string, payload: Partial<IncomePayload>) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export function useIncomes(): IncomeState {
  const [items, setItems] = useState<Income[]>([]);
  const [total, setTotal] = useState('0.00');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<IncomeListResponse>('/incomes');
      setItems(data.items);
      setTotal(data.total);
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

  const create = useCallback(
    async (payload: IncomePayload) => {
      setSubmitting(true);
      try {
        await api.post('/incomes', payload);
        await refresh();
        setError(null);
      } catch (err) {
        setError(getApiErrorMessage(err));
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    [refresh]
  );

  const update = useCallback(
    async (id: string, payload: Partial<IncomePayload>) => {
      setSubmitting(true);
      try {
        await api.put(`/incomes/${id}`, payload);
        await refresh();
        setError(null);
      } catch (err) {
        setError(getApiErrorMessage(err));
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    [refresh]
  );

  const remove = useCallback(
    async (id: string) => {
      setSubmitting(true);
      try {
        await api.delete(`/incomes/${id}`);
        await refresh();
        setError(null);
      } catch (err) {
        setError(getApiErrorMessage(err));
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    [refresh]
  );

  return useMemo(
    () => ({ items, total, loading, submitting, error, refresh, create, update, remove }),
    [items, total, loading, submitting, error, refresh, create, update, remove]
  );
}
