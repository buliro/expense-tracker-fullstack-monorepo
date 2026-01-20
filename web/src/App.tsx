import { useState } from 'react';
import type { Expense, ExpensePayload, Income, IncomePayload } from './types';
import { useExpenses } from './hooks/useExpenses';
import { useIncomes } from './hooks/useIncomes';
import { useSummary } from './hooks/useSummary';
import { ExpenseForm } from './components/ExpenseForm';
import { IncomeForm } from './components/IncomeForm';
import { ExpenseList } from './components/ExpenseList';
import { IncomeList } from './components/IncomeList';
import { Modal } from './components/Modal';
import { formatAmount } from './utils/number';

const tabs = [
  { key: 'expenses', label: 'Expenses' },
  { key: 'incomes', label: 'Income' },
];

type TabKey = (typeof tabs)[number]['key'];

export default function App(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabKey>('expenses');
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [editingIncome, setEditingIncome] = useState<Income | null>(null);
  const [isExpenseModalOpen, setExpenseModalOpen] = useState(false);
  const [isIncomeModalOpen, setIncomeModalOpen] = useState(false);

  const expenses = useExpenses();
  const incomes = useIncomes();
  const summary = useSummary();

  const formatTotal = (value: string | null | undefined): string => {
    const formatted = value ? formatAmount(value) : '';
    return formatted || '0';
  };

  const netBalanceValue = Number.parseFloat(summary.balance ?? '0');
  const isNegativeBalance =
    !summary.loading &&
    !summary.error &&
    Number.isFinite(netBalanceValue) &&
    !Number.isNaN(netBalanceValue) &&
    netBalanceValue < 0;

  const closeExpenseModal = () => {
    setExpenseModalOpen(false);
    setEditingExpense(null);
  };

  const closeIncomeModal = () => {
    setIncomeModalOpen(false);
    setEditingIncome(null);
  };

  const handleExpenseCreate = async (values: ExpensePayload) => {
    await expenses.create(values);
    await summary.refresh();
  };

  const handleExpenseUpdate = async (id: string, values: Partial<ExpensePayload>) => {
    await expenses.update(id, values);
    setEditingExpense(null);
    await summary.refresh();
  };

  const handleIncomeCreate = async (values: IncomePayload) => {
    await incomes.create(values);
    await summary.refresh();
  };

  const handleIncomeUpdate = async (id: string, values: Partial<IncomePayload>) => {
    await incomes.update(id, values);
    setEditingIncome(null);
    await summary.refresh();
  };

  const renderExpenses = (): JSX.Element => (
    <div className="panel">
      <div className="panel-header">
        <h2>Expenses</h2>
        <p>Total: {formatTotal(expenses.total)}</p>
      </div>
      <ExpenseList
        items={expenses.items}
        loading={expenses.loading}
        error={expenses.error}
        onEdit={(expense: Expense) => {
          setEditingExpense(expense);
          setExpenseModalOpen(true);
        }}
        onDelete={async (id: string) => {
          await expenses.remove(id);
          if (editingExpense?.id === id) {
            setEditingExpense(null);
          }
          await summary.refresh();
        }}
      />
    </div>
  );

  const renderIncomes = (): JSX.Element => (
    <div className="panel">
      <div className="panel-header">
        <h2>Income</h2>
        <p>Total: {formatTotal(incomes.total)}</p>
      </div>
      <IncomeList
        items={incomes.items}
        loading={incomes.loading}
        error={incomes.error}
        onEdit={(income: Income) => {
          setEditingIncome(income);
          setIncomeModalOpen(true);
        }}
        onDelete={async (id: string) => {
          await incomes.remove(id);
          if (editingIncome?.id === id) {
            setEditingIncome(null);
          }
          await summary.refresh();
        }}
      />
    </div>
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>Expense Tracker</h1>
        <section className="summary">
          <div className="metric">
            <span className="label">Expense Total</span>
            <span className="value">{formatTotal(expenses.total)}</span>
          </div>
          <div className="metric">
            <span className="label">Income Total</span>
            <span className="value">{formatTotal(incomes.total)}</span>
          </div>
          <div className={`metric ${isNegativeBalance ? 'negative' : ''}`}>
            <span className="label">Net Balance</span>
            <span className={`value ${isNegativeBalance ? 'negative' : ''}`}>
              {summary.loading
                ? 'Loading…'
                : summary.error
                  ? summary.error
                  : formatTotal(summary.balance)}
            </span>
          </div>
        </section>
      </header>

      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={tab.key === activeTab ? 'active' : ''}
            onClick={() => {
              setActiveTab(tab.key);
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="content">
        {activeTab === 'expenses' ? renderExpenses() : renderIncomes()}
      </main>

      <button
        type="button"
        className="fab"
        onClick={() => {
          if (activeTab === 'expenses') {
            setEditingExpense(null);
            setExpenseModalOpen(true);
          } else {
            setEditingIncome(null);
            setIncomeModalOpen(true);
          }
        }}
        aria-label={activeTab === 'expenses' ? 'Add expense' : 'Add income'}
      >
        +
      </button>

      <Modal
        open={isExpenseModalOpen}
        onClose={closeExpenseModal}
        ariaLabel={editingExpense ? 'Edit expense' : 'Add expense'}
      >
        <ExpenseForm
          key={editingExpense ? editingExpense.id : 'create-expense'}
          mode={editingExpense ? 'edit' : 'create'}
          initialValues={editingExpense ?? undefined}
          loading={expenses.submitting}
          onSubmit={async (payload: ExpensePayload) => {
            if (editingExpense) {
              await handleExpenseUpdate(editingExpense.id, payload);
            } else {
              await handleExpenseCreate(payload);
            }
            closeExpenseModal();
          }}
          onCancel={closeExpenseModal}
        />
      </Modal>

      <Modal
        open={isIncomeModalOpen}
        onClose={closeIncomeModal}
        ariaLabel={editingIncome ? 'Edit income' : 'Add income'}
      >
        <IncomeForm
          key={editingIncome ? editingIncome.id : 'create-income'}
          mode={editingIncome ? 'edit' : 'create'}
          initialValues={editingIncome ?? undefined}
          loading={incomes.submitting}
          onSubmit={async (payload: IncomePayload) => {
            if (editingIncome) {
              await handleIncomeUpdate(editingIncome.id, payload);
            } else {
              await handleIncomeCreate(payload);
            }
            closeIncomeModal();
          }}
          onCancel={closeIncomeModal}
        />
      </Modal>
    </div>
  );
}
