import { Expense } from '../types';
import { formatDateTime } from '../utils/datetime';
import { formatAmount } from '../utils/number';

interface ExpenseListProps {
  items: Expense[];
  loading: boolean;
  error: string | null;
  onEdit: (expense: Expense) => void;
  onDelete: (id: string) => Promise<void> | void;
}

export function ExpenseList({ items, loading, error, onEdit, onDelete }: ExpenseListProps) {
  if (loading) {
    return <p className="status">Loading expenses…</p>;
  }

  if (error) {
    return <p className="status error">{error}</p>;
  }

  if (items.length === 0) {
    return <p className="status">No expenses recorded yet.</p>;
  }

  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Category</th>
            <th>Merchant</th>
            <th>Amount</th>
            <th>Payment</th>
            <th>Tags</th>
            <th aria-label="actions" />
          </tr>
        </thead>
        <tbody>
          {items.map((expense) => (
            <tr key={expense.id}>
              <td>{formatDateTime(expense.incurred_at)}</td>
              <td>{expense.category}</td>
              <td>{expense.merchant || '—'}</td>
              <td>
                {expense.currency} {formatAmount(expense.amount)}
              </td>
              <td>{expense.payment_method}</td>
              <td>{expense.tags.length ? expense.tags.join(', ') : '—'}</td>
              <td className="actions">
                <button type="button" className="link" onClick={() => onEdit(expense)}>
                  Edit
                </button>
                <button
                  type="button"
                  className="link destructive"
                  onClick={() => {
                    void onDelete(expense.id);
                  }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
