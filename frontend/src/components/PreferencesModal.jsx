import { useEffect, useState } from 'react';
import { Check, SlidersHorizontal, X } from 'lucide-react';
import { api } from '../api/client';

export default function PreferencesModal({
  isOpen,
  onClose,
  categories,
  selectedIds,
  onSaved,
}) {
  const [chosen, setChosen] = useState(selectedIds || []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setChosen(selectedIds || []);
  }, [selectedIds, isOpen]);

  if (!isOpen) return null;

  const selectable = categories.filter((c) => c.slug !== 'uncategorized');

  function toggleCategory(id) {
    setChosen((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  async function handleSave() {
    setSaving(true);
    setError('');
    try {
      const updated = await api.updatePreferences(chosen);
      onSaved(updated.category_ids);
      onClose();
    } catch (err) {
      setError(err.message || 'Could not save preferences');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
          <SlidersHorizontal className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-widest">Personalization</span>
        </div>
        <h2 className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">
          Choose Preferred Topics
        </h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Your &ldquo;For You&rdquo; feed prioritizes stories from these categories while keeping all topics accessible.
        </p>

        {error && (
          <div className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </div>
        )}

        <div className="mt-5 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {selectable.map((cat) => {
            const active = chosen.includes(cat.id);
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => toggleCategory(cat.id)}
                className={`flex items-center justify-between rounded-xl border px-3.5 py-2.5 text-left text-sm font-medium transition ${
                  active
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-800 dark:border-indigo-500 dark:bg-indigo-950/50 dark:text-indigo-200'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                }`}
              >
                <span>{cat.name}</span>
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                    active
                      ? 'border-indigo-600 bg-indigo-600 text-white'
                      : 'border-slate-300 dark:border-slate-600'
                  }`}
                >
                  {active && <Check className="h-3 w-3" />}
                </span>
              </button>
            );
          })}
        </div>

        <div className="mt-6 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Topics'}
          </button>
        </div>
      </div>
    </div>
  );
}
