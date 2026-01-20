import { Income } from '../types';
import { formatDateTime } from '../utils/datetime';
import { formatAmount } from '../utils/number';

interface IncomeListProps {
  items: Income[];
  loading: boolean;
  error: string | null;
  onEdit: (income: Income) => void;
  onDelete: (id: string) => Promise<void> | void;
}

export function IncomeList({ items, loading, error, onEdit, onDelete }: IncomeListProps) {
  if (loading) {
    return <p className="status">Loading income…</p>;
  }

  if (error) {
    return <p className="status error">{error}</p>;
  }

  if (items.length === 0) {
    return <p className="status">No income recorded yet.</p>;
  }

  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Source</th>
            <th>Method</th>
            <th>Amount</th>
            <th>Tags</th>
            <th aria-label="actions" />
          </tr>
        </thead>
        <tbody>
          {items.map((income) => (
            <tr key={income.id}>
              <td>{formatDateTime(income.received_at)}</td>
              <td>{income.source}</td>
              <td>{income.received_method}</td>
              <td>
                {income.currency} {formatAmount(income.amount)}
              </td>
              <td>{income.tags.length ? income.tags.join(', ') : '—'}</td>
              <td className="actions">
                <button type="button" className="link" onClick={() => onEdit(income)}>
                  Edit
                </button>
                <button
                  type="button"
                  className="link destructive"
                  onClick={() => {
                    void onDelete(income.id);
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
