import {
  ChangeEvent,
  KeyboardEvent,
  useMemo,
  useState,
} from 'react';
import { useCategories } from '../hooks/useCategories';
import type { Category } from '../types';

interface CategoryManagerProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function CategoryManager(props: CategoryManagerProps): JSX.Element {
  const { value, onChange, disabled = false } = props;
  const categories = useCategories();
  const [showManager, setShowManager] = useState(false);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const hasSelectedValue = useMemo(
    () => categories.items.some((category) => category.name === value),
    [categories.items, value]
  );

  const isBusy = disabled || categories.submitting;
  const isLoading = categories.loading;

  const handleSelect = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  const toggleManager = () => {
    setShowManager((prev: boolean) => {
      const next = !prev;
      if (!next) {
        setEditingId(null);
        setEditingName('');
      }
      return next;
    });
  };

  const handleAdd = async () => {
    const trimmed = newName.trim();
    if (!trimmed) {
      return;
    }
    try {
      const created = await categories.create({ name: trimmed });
      onChange(created.name);
      setNewName('');
      setShowManager(true);
    } catch (error) {
      console.error('Failed to add category', error);
    }
  };

  const handleAddKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      void handleAdd();
    }
  };

  const beginEdit = (category: Category) => {
    setEditingId(category.id);
    setEditingName(category.name);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };

  const handleUpdate = async () => {
    if (!editingId) {
      return;
    }
    const trimmed = editingName.trim();
    if (!trimmed) {
      return;
    }
    try {
      const updated = await categories.update(editingId, { name: trimmed });
      onChange(updated.name);
      cancelEdit();
    } catch (error) {
      console.error('Failed to update category', error);
    }
  };

  const handleDelete = async (category: Category) => {
    try {
      await categories.remove(category.id);
      if (value === category.name) {
        onChange('');
      }
    } catch (error) {
      console.error('Failed to delete category', error);
    }
  };

  return (
    <div className="category-field">
      <div className="category-select">
        <select value={value} onChange={handleSelect} disabled={isBusy || isLoading} required>
          <option value="" disabled>
            Select a category
          </option>
          {categories.items.map((category) => (
            <option key={category.id} value={category.name}>
              {category.name}
            </option>
          ))}
          {!hasSelectedValue && value ? <option value={value}>{value}</option> : null}
        </select>
        <button
          type="button"
          className="secondary"
          onClick={toggleManager}
          disabled={isLoading}
        >
          {showManager ? 'Close' : 'Manage'}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => categories.refresh()}
          disabled={isLoading}
          aria-label="Refresh categories"
        >
          Refresh
        </button>
      </div>
      {isLoading ? <p className="status">Loading categories…</p> : null}
      {categories.error ? <p className="form-error">{categories.error}</p> : null}
      {showManager ? (
        <div className="category-manager-panel">
          <div className="category-add">
            <input
              type="text"
              value={newName}
              placeholder="New category name"
              onChange={(event: ChangeEvent<HTMLInputElement>) => setNewName(event.target.value)}
              onKeyDown={handleAddKeyDown}
              disabled={isBusy}
            />
            <button type="button" onClick={() => void handleAdd()} disabled={isBusy}>
              Add
            </button>
          </div>
          <ul className="category-list">
            {categories.items.length === 0 ? (
              <li className="category-empty">No categories yet.</li>
            ) : (
              categories.items.map((category) => (
                <li key={category.id}>
                  {editingId === category.id ? (
                    <div className="category-edit">
                      <input
                        type="text"
                        value={editingName}
                        onChange={(event: ChangeEvent<HTMLInputElement>) =>
                          setEditingName(event.target.value)
                        }
                        onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            void handleUpdate();
                          }
                        }}
                        disabled={isBusy}
                      />
                      <div className="category-actions">
                        <button
                          type="button"
                          onClick={() => void handleUpdate()}
                          disabled={isBusy}
                        >
                          Save
                        </button>
                        <button type="button" className="secondary" onClick={cancelEdit}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="category-row">
                      <span>{category.name}</span>
                      <div className="category-actions">
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => beginEdit(category)}
                          disabled={isBusy}
                        >
                          Rename
                        </button>
                        <button
                          type="button"
                          className="link destructive"
                          onClick={() => void handleDelete(category)}
                          disabled={isBusy}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              ))
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
