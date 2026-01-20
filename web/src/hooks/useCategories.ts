import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import type { Category, CategoryListResponse } from '../types';
import { getApiErrorMessage } from '../utils/errors';

export interface CategoryPayload {
  name: string;
}

export interface CategoryState {
  items: Category[];
  loading: boolean;
  submitting: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  create: (payload: CategoryPayload) => Promise<Category>;
  update: (id: string, payload: CategoryPayload) => Promise<Category>;
  remove: (id: string) => Promise<void>;
}

const sortCategories = (items: Category[]): Category[] =>
  [...items].sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));

export function useCategories(): CategoryState {
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<CategoryListResponse>('/categories');
      setItems(sortCategories(data.items));
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
    async (payload: CategoryPayload) => {
      setSubmitting(true);
      try {
        const { data } = await api.post<Category>('/categories', payload);
        setItems((prev: Category[]) => sortCategories([...prev, data]));
        setError(null);
        return data;
      } catch (err) {
        const message = getApiErrorMessage(err);
        setError(message);
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  const update = useCallback(
    async (id: string, payload: CategoryPayload) => {
      setSubmitting(true);
      try {
        const { data } = await api.put<Category>(`/categories/${id}`, payload);
        setItems((prev: Category[]) =>
          sortCategories(prev.map((item: Category) => (item.id === id ? data : item)))
        );
        setError(null);
        return data;
      } catch (err) {
        const message = getApiErrorMessage(err);
        setError(message);
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  const remove = useCallback(
    async (id: string) => {
      setSubmitting(true);
      try {
        await api.delete(`/categories/${id}`);
        setItems((prev: Category[]) => prev.filter((item: Category) => item.id !== id));
        setError(null);
      } catch (err) {
        const message = getApiErrorMessage(err);
        setError(message);
        throw err;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  return useMemo(
    () => ({ items, loading, submitting, error, refresh, create, update, remove }),
    [items, loading, submitting, error, refresh, create, update, remove]
  );
}
