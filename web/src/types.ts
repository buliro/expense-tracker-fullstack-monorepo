export interface Category {
  id: string;
  name: string;
}

export interface Expense {
  id: string;
  amount: string;
  currency: string;
  category: string;
  payment_method: string;
  incurred_at: string;
  recorded_at: string;
  description?: string | null;
  merchant?: string | null;
  tags: string[];
  receipt_image_path?: string | null;
}

export interface Income {
  id: string;
  amount: string;
  currency: string;
  source: string;
  received_method: string;
  received_at: string;
  recorded_at: string;
  description?: string | null;
  tags: string[];
  attachment_path?: string | null;
}

export interface ExpenseListResponse {
  items: Expense[];
  total: string;
}

export interface IncomeListResponse {
  items: Income[];
  total: string;
}

export interface SummaryResponse {
  balance: string;
}

export interface CategoryListResponse {
  items: Category[];
}

export type ExpensePayload = Partial<Omit<Expense, 'id' | 'recorded_at'>> & {
  amount: string;
  currency: string;
  category: string;
  payment_method: string;
  incurred_at: string;
};

export type IncomePayload = Partial<Omit<Income, 'id' | 'recorded_at'>> & {
  amount: string;
  currency: string;
  source: string;
  received_method: string;
  received_at: string;
};
