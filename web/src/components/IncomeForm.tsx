import {
  ChangeEvent,
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { Income, IncomePayload } from '../types';
import {
  combineDateAndTime,
  getCurrentTimeInput,
  isFutureDate,
  toIsoString,
  toLocalDateInput,
  toLocalTimeInput,
} from '../utils/datetime';
import { formatAmount, sanitizeAmountInput } from '../utils/number';

const RECEIVED_METHODS = [
  { value: 'salary', label: 'Salary' },
  { value: 'bonus', label: 'Bonus' },
  { value: 'interest', label: 'Interest' },
  { value: 'gift', label: 'Gift' },
  { value: 'other', label: 'Other' },
];

interface IncomeFormProps {
  mode: 'create' | 'edit';
  initialValues?: Income;
  loading: boolean;
  onSubmit: (payload: IncomePayload) => Promise<void> | void;
  onCancel?: () => void;
}

interface IncomeFormState {
  amount: string;
  currency: string;
  source: string;
  received_method: string;
  received_date: string;
  received_time: string;
  description: string;
  tags: string;
  attachment_path: string;
}

const DEFAULT_CURRENCY = 'USD';

type IncomeFormErrors = Partial<
  Record<'amount' | 'source' | 'received_method' | 'received_date', string>
>;

interface IncomeValidationResult {
  errors: IncomeFormErrors;
  hasFutureDateError: boolean;
}

const validateIncome = (state: IncomeFormState): IncomeValidationResult => {
  const errors: IncomeFormErrors = {};
  let hasFutureDateError = false;

  const amountValue = Number(state.amount);
  if (!state.amount.trim()) {
    errors.amount = 'Amount is required.';
  } else if (Number.isNaN(amountValue) || amountValue <= 0) {
    errors.amount = 'Enter a positive amount.';
  }

  if (!state.source.trim()) {
    errors.source = 'Source is required.';
  }

  if (!state.received_method.trim()) {
    errors.received_method = 'Choose a received method.';
  }

  if (!state.received_date) {
    errors.received_date = 'Date is required.';
  } else if (isFutureDate(state.received_date)) {
    errors.received_date = 'Received date cannot be in the future.';
    hasFutureDateError = true;
  }

  return { errors, hasFutureDateError };
};

const emptyState: IncomeFormState = {
  amount: '',
  currency: DEFAULT_CURRENCY,
  source: '',
  received_method: 'salary',
  received_date: '',
  received_time: '',
  description: '',
  tags: '',
  attachment_path: '',
};

export function IncomeForm(props: IncomeFormProps): JSX.Element {
  const { mode, initialValues, loading, onSubmit, onCancel } = props;
  const [state, setState] = useState<IncomeFormState>(emptyState);
  const [error, setError] = useState<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);

  useEffect(() => {
    if (initialValues) {
      setState({
        amount: sanitizeAmountInput(initialValues.amount),
        currency: initialValues.currency || DEFAULT_CURRENCY,
        source: initialValues.source,
        received_method: initialValues.received_method,
        received_date: toLocalDateInput(initialValues.received_at),
        received_time: toLocalTimeInput(initialValues.received_at),
        description: initialValues.description ?? '',
        tags: initialValues.tags.join(', '),
        attachment_path: initialValues.attachment_path ?? '',
      });
    } else {
      setState(emptyState);
    }
    setHasSubmitted(false);
    setError(null);
  }, [initialValues]);

  const isEdit = mode === 'edit';
  const heading = useMemo(() => (isEdit ? 'Edit Income' : 'Add Income'), [isEdit]);

  const updateField = (
    field: keyof IncomeFormState
  ) =>
    (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { value } = event.target;
      if (field === 'amount') {
        const sanitized = sanitizeAmountInput(value);
        setState((prev: IncomeFormState) => ({ ...prev, amount: sanitized }));
        return;
      }
      setState((prev: IncomeFormState) => ({ ...prev, [field]: value }));
    };

  const { errors: validationErrors, hasFutureDateError } = useMemo(
    () => validateIncome(state),
    [state]
  );

  const isFormValid = Object.keys(validationErrors).length === 0;

  useEffect(() => {
    if (hasSubmitted && isFormValid) {
      setError(null);
    }
  }, [hasSubmitted, isFormValid]);

  const getFieldError = (field: keyof IncomeFormErrors): string | null => {
    const message = validationErrors[field];
    if (!message) {
      return null;
    }

    if (field === 'received_date') {
      if (!state.received_date && !hasSubmitted) {
        return null;
      }
      return message;
    }

    if (!hasSubmitted) {
      if (field === 'amount') {
        return state.amount.trim() ? message : null;
      }
      if (field === 'source') {
        return state.source.trim() ? message : null;
      }
      if (field === 'received_method') {
        return state.received_method.trim() ? message : null;
      }
      return null;
    }

    return message;
  };

  const amountError = getFieldError('amount');
  const sourceError = getFieldError('source');
  const receivedMethodError = getFieldError('received_method');
  const receivedDateError = getFieldError('received_date');

  const disableSubmit = loading || hasFutureDateError;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setHasSubmitted(true);

    if (!isFormValid) {
      setError('Please correct the highlighted fields.');
      return;
    }

    const payload: IncomePayload = {
      amount: state.amount,
      currency: state.currency.toUpperCase(),
      source: state.source,
      received_method: state.received_method,
      received_at: toIsoString(
        combineDateAndTime(state.received_date, state.received_time)
      ),
      description: state.description || undefined,
      tags: state.tags
        ? state.tags
            .split(',')
            .map((tag: string) => tag.trim())
            .filter(Boolean)
        : undefined,
      attachment_path: state.attachment_path || undefined,
    };

    try {
      await onSubmit(payload);
      if (!isEdit) {
        setState(emptyState);
      }
      setHasSubmitted(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit income');
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
            <span>Source</span>
            <input type="text" value={state.source} onChange={updateField('source')} required />
            {sourceError ? <p className="field-error">{sourceError}</p> : null}
          </label>
          <label>
            <span>Received Method</span>
            <select value={state.received_method} onChange={updateField('received_method')}>
              {RECEIVED_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
            {receivedMethodError ? <p className="field-error">{receivedMethodError}</p> : null}
          </label>
        </div>

        <label>
          <span>Received At</span>
          <div className="datetime-fields">
            <input
              type="date"
              value={state.received_date}
              onChange={updateField('received_date')}
              required
            />
            <input
              type="time"
              value={state.received_time}
              onChange={updateField('received_time')}
            />
            <button
              type="button"
              className="secondary"
              onClick={() =>
                setState((prev: IncomeFormState) => ({
                  ...prev,
                  received_time: getCurrentTimeInput(),
                }))
              }
            >
              Use current time
            </button>
          </div>
          {receivedDateError ? <p className="field-error">{receivedDateError}</p> : null}
        </label>

        <label>
          <span>Description</span>
          <textarea value={state.description} onChange={updateField('description')} rows={2} />
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

        {error ? <p className="form-error">{error}</p> : null}

        <div className="form-actions">
          {isEdit && onCancel ? (
            <button type="button" className="secondary" onClick={onCancel} disabled={loading}>
              Cancel
            </button>
          ) : null}
          <button type="submit" disabled={disableSubmit}>
            {loading ? 'Saving…' : isEdit ? 'Update Income' : 'Add Income'}
          </button>
        </div>
      </form>
    </section>
  );
}
