import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import {
  Expense,
  ExpenseListResponse,
  ExpensePayload,
} from '../types';
import { getApiErrorMessage } from '../utils/errors';

interface ExpenseState {
  items: Expense[];
  total: string;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  create: (payload: ExpensePayload) => Promise<void>;
  update: (id: string, payload: Partial<ExpensePayload>) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export function useExpenses(): ExpenseState {
  const [items, setItems] = useState<Expense[]>([]);
  const [total, setTotal] = useState('0.00');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<ExpenseListResponse>('/expenses');
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
    async (payload: ExpensePayload) => {
      setSubmitting(true);
      try {
        await api.post('/expenses', payload);
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
    async (id: string, payload: Partial<ExpensePayload>) => {
      setSubmitting(true);
      try {
        await api.put(`/expenses/${id}`, payload);
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
        await api.delete(`/expenses/${id}`);
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
