import {
  ChangeEvent,
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { Expense, ExpensePayload } from '../types';
import {
  combineDateAndTime,
  getCurrentTimeInput,
  isFutureDate,
  toIsoString,
  toLocalDateInput,
  toLocalTimeInput,
} from '../utils/datetime';
import { formatAmount, sanitizeAmountInput } from '../utils/number';
import { CategoryManager } from './CategoryManager';

const PAYMENT_METHODS = [
  { value: 'cash', label: 'Cash' },
  { value: 'debit_card', label: 'Debit Card' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'mobile_payment', label: 'Mobile Payment' },
  { value: 'other', label: 'Other' },
];

interface ExpenseFormProps {
  mode: 'create' | 'edit';
  initialValues?: Expense;
  loading: boolean;
  onSubmit: (payload: ExpensePayload) => Promise<void> | void;
  onCancel?: () => void;
}

interface ExpenseFormState {
  amount: string;
  currency: string;
  category: string;
  payment_method: string;
  incurred_date: string;
  incurred_time: string;
  description: string;
  merchant: string;
  tags: string;
  receipt_image_path: string;
}

const DEFAULT_CURRENCY = 'USD';

type ExpenseFormErrors = Partial<
  Record<'amount' | 'category' | 'payment_method' | 'incurred_date', string>
>;

interface ExpenseValidationResult {
  errors: ExpenseFormErrors;
  hasFutureDateError: boolean;
}

const validateExpense = (state: ExpenseFormState): ExpenseValidationResult => {
  const errors: ExpenseFormErrors = {};
  let hasFutureDateError = false;

  const amountValue = Number(state.amount);
  if (!state.amount.trim()) {
    errors.amount = 'Amount is required.';
  } else if (Number.isNaN(amountValue) || amountValue <= 0) {
    errors.amount = 'Enter a positive amount.';
  }

  if (!state.category.trim()) {
    errors.category = 'Select or create a category.';
  }

  if (!state.payment_method.trim()) {
    errors.payment_method = 'Choose a payment method.';
  }

  if (!state.incurred_date) {
    errors.incurred_date = 'Date is required.';
  } else if (isFutureDate(state.incurred_date)) {
    errors.incurred_date = 'Incurred date cannot be in the future.';
    hasFutureDateError = true;
  }

  return { errors, hasFutureDateError };
};

const emptyState: ExpenseFormState = {
  amount: '',
  currency: DEFAULT_CURRENCY,
  category: '',
  payment_method: 'cash',
  incurred_date: '',
  incurred_time: '',
  description: '',
  merchant: '',
  tags: '',
  receipt_image_path: '',
};

export function ExpenseForm(props: ExpenseFormProps): JSX.Element {
  const { mode, initialValues, loading, onSubmit, onCancel } = props;
  const [state, setState] = useState<ExpenseFormState>(emptyState);
  const [error, setError] = useState<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);

  useEffect(() => {
    if (initialValues) {
      setState({
        amount: sanitizeAmountInput(initialValues.amount),
        currency: initialValues.currency || DEFAULT_CURRENCY,
        category: initialValues.category,
        payment_method: initialValues.payment_method,
        incurred_date: toLocalDateInput(initialValues.incurred_at),
        incurred_time: toLocalTimeInput(initialValues.incurred_at),
        description: initialValues.description ?? '',
        merchant: initialValues.merchant ?? '',
        tags: initialValues.tags.join(', '),
        receipt_image_path: initialValues.receipt_image_path ?? '',
      });
    } else {
      setState(emptyState);
    }
    setHasSubmitted(false);
    setError(null);
  }, [initialValues]);

  const isEdit = mode === 'edit';

  const heading = useMemo(() => (isEdit ? 'Edit Expense' : 'Add Expense'), [isEdit]);

  const updateField = (
    field: keyof ExpenseFormState
  ) =>
    (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { value } = event.target;
      if (field === 'amount') {
        const sanitized = sanitizeAmountInput(value);
        setState((prev: ExpenseFormState) => ({ ...prev, amount: sanitized }));
        return;
      }
      setState((prev: ExpenseFormState) => ({ ...prev, [field]: value }));
    };

  const handleCategoryChange = useCallback((next: string) => {
    setState((prev: ExpenseFormState) => ({ ...prev, category: next }));
  }, []);

  const handleUseCurrentTime = () => {
    setState((prev: ExpenseFormState) => ({ ...prev, incurred_time: getCurrentTimeInput() }));
  };

  const { errors: validationErrors, hasFutureDateError } = useMemo(
    () => validateExpense(state),
    [state]
  );

  const isFormValid = Object.keys(validationErrors).length === 0;

  useEffect(() => {
    if (hasSubmitted && isFormValid) {
      setError(null);
    }
  }, [hasSubmitted, isFormValid]);

  const getFieldError = (field: keyof ExpenseFormErrors): string | null => {
    const message = validationErrors[field];
    if (!message) {
      return null;
    }

    if (field === 'incurred_date') {
      if (!state.incurred_date && !hasSubmitted) {
        return null;
      }
      return message;
    }

    if (!hasSubmitted) {
      if (field === 'amount') {
        return state.amount.trim() ? message : null;
      }
      if (field === 'category') {
        return state.category.trim() ? message : null;
      }
      if (field === 'payment_method') {
        return state.payment_method.trim() ? message : null;
      }
      return null;
    }

    return message;
  };

  const amountError = getFieldError('amount');
  const categoryError = getFieldError('category');
  const paymentMethodError = getFieldError('payment_method');
  const incurredDateError = getFieldError('incurred_date');

  const disableSubmit = loading || hasFutureDateError;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setHasSubmitted(true);

    if (!isFormValid) {
      setError('Please correct the highlighted fields.');
      return;
    }

    const payload: ExpensePayload = {
      amount: state.amount,
      currency: state.currency.toUpperCase(),
      category: state.category,
      payment_method: state.payment_method,
      incurred_at: toIsoString(
        combineDateAndTime(state.incurred_date, state.incurred_time)
      ),
      description: state.description || undefined,
      merchant: state.merchant || undefined,
      tags: state.tags
        ? state.tags
            .split(',')
            .map((tag: string) => tag.trim())
            .filter(Boolean)
        : undefined,
      receipt_image_path: state.receipt_image_path || undefined,
    };

    try {
      await onSubmit(payload);
      if (!isEdit) {
        setState(emptyState);
      }
      setHasSubmitted(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit expense');
    }
  };

  return (
    <section className="card">
      <header className="card-header">
        <h3>{heading}</h3>
      </header>
      <form className="card-body" onSubmit={handleSubmit}>
        <div className="grid two-columns">
          <label>
            <span>Amount</span>
            <input
              type="text"
              inputMode="decimal"
              value={formatAmount(state.amount)}
              onChange={updateField('amount')}
              required
            />
            {amountError ? <p className="field-error">{amountError}</p> : null}
          </label>
          <label>
            <span>Currency</span>
            <input type="text" value={state.currency} disabled aria-readonly="true" />
          </label>
        </div>

        <div className="grid two-columns">
          <label>
            <span>Category</span>
            <CategoryManager
              value={state.category}
              onChange={handleCategoryChange}
              disabled={loading}
            />
            {categoryError ? <p className="field-error">{categoryError}</p> : null}
          </label>
          <label>
            <span>Payment Method</span>
            <select
              value={state.payment_method}
              onChange={updateField('payment_method')}
            >
              {PAYMENT_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
            {paymentMethodError ? <p className="field-error">{paymentMethodError}</p> : null}
          </label>
        </div>

        <label>
          <span>Incurred At</span>
          <div className="datetime-fields">
            <input
              type="date"
              value={state.incurred_date}
              onChange={updateField('incurred_date')}
              required
            />
            <input
              type="time"
              value={state.incurred_time}
              onChange={updateField('incurred_time')}
            />
            <button type="button" className="secondary" onClick={handleUseCurrentTime}>
              Use current time
            </button>
          </div>
          {incurredDateError ? <p className="field-error">{incurredDateError}</p> : null}
        </label>

        <label>
          <span>Description</span>
          <textarea value={state.description} onChange={updateField('description')} rows={2} />
        </label>

        <div className="grid two-columns">
          <label>
            <span>Merchant</span>
            <input type="text" value={state.merchant} onChange={updateField('merchant')} />
          </label>
          <label>
            <span>Tags</span>
            <input
              type="text"
              placeholder="Comma separated"
              value={state.tags}
              onChange={updateField('tags')}
            />
          </label>
        </div>

        {error ? <p className="form-error">{error}</p> : null}

        <div className="form-actions">
          {onCancel ? (
            <button type="button" className="secondary" onClick={onCancel} disabled={loading}>
              Cancel
            </button>
          ) : null}
          <button type="submit" disabled={disableSubmit}>
            {loading ? 'Saving…' : isEdit ? 'Update Expense' : 'Add Expense'}
          </button>
        </div>
      </form>
    </section>
  );
}
