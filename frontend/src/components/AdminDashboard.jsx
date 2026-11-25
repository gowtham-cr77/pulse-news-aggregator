import { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Edit3,
  Plus,
  RefreshCw,
  Rss,
  Trash2,
  X,
} from 'lucide-react';
import { api } from '../api/client';
import { formatRelativeTime } from './ArticleCard';

export default function AdminDashboard({ categories, onFeedsSynced, notify }) {
  const [feeds, setFeeds] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncingAll, setSyncingAll] = useState(false);
  const [syncingId, setSyncingId] = useState(null);
  const [activeTab, setActiveTab] = useState('feeds');
  const [lastSummary, setLastSummary] = useState(null);

  // Add / Edit feed state
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingFeed, setEditingFeed] = useState(null);
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formRegion, setFormRegion] = useState('india');
  const [formSourceType, setFormSourceType] = useState('rss');
  const [formCategoryId, setFormCategoryId] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);
  const [savingFeed, setSavingFeed] = useState(false);
  const [regionFilter, setRegionFilter] = useState('all');

  // Category keyword rule editor
  const [editingCategory, setEditingCategory] = useState(null);
  const [keywordsText, setKeywordsText] = useState('');

  async function loadAdminData() {
    setLoading(true);
    try {
      const [feedsRes, runsRes] = await Promise.all([
        api.getAdminFeeds(),
        api.getIngestionRuns(50),
      ]);
      setFeeds(feedsRes);
      setRuns(runsRes);
    } catch (err) {
      notify(err.message || 'Failed to load admin dashboard', 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAdminData();
  }, []);

  function openAddModal() {
    setEditingFeed(null);
    setFormName('');
    setFormUrl('');
    setFormRegion('india');
    setFormSourceType('rss');
    setFormCategoryId(categories[0]?.id ? String(categories[0].id) : '');
    setFormEnabled(true);
    setShowAddForm(true);
  }

  function openEditModal(feed) {
    setEditingFeed(feed);
    setFormName(feed.name);
    setFormUrl(feed.feed_url);
    setFormRegion(feed.region || 'global');
    setFormSourceType(feed.source_type || 'rss');
    setFormCategoryId(feed.default_category_id ? String(feed.default_category_id) : '');
    setFormEnabled(feed.enabled);
    setShowAddForm(true);
  }

  async function handleSaveFeed(e) {
    e.preventDefault();
    setSavingFeed(true);
    try {
      const payload = {
        name: formName.trim(),
        feed_url: formUrl.trim(),
        region: formRegion,
        source_type: formSourceType,
        default_category_id: formCategoryId ? Number(formCategoryId) : null,
        enabled: formEnabled,
      };
      if (editingFeed) {
        await api.updateAdminFeed(editingFeed.id, payload);
        notify(`Updated "${payload.name}"`);
      } else {
        await api.createAdminFeed(payload);
        notify(`Added feed "${payload.name}"`);
      }
      setShowAddForm(false);
      await loadAdminData();
      onFeedsSynced?.();
    } catch (err) {
      notify(err.message || 'Could not save feed source', 'error');
    } finally {
      setSavingFeed(false);
    }
  }

  async function handleToggleEnabled(feed) {
    try {
      await api.updateAdminFeed(feed.id, { enabled: !feed.enabled });
      notify(`${feed.name} ${!feed.enabled ? 'enabled' : 'disabled'}`);
      await loadAdminData();
    } catch (err) {
      notify(err.message || 'Failed to toggle feed', 'error');
    }
  }

  async function handleDeleteFeed(feed) {
    if (!window.confirm(`Delete feed source "${feed.name}" and its indexed articles?`)) return;
    try {
      await api.deleteAdminFeed(feed.id);
      notify(`Deleted "${feed.name}"`);
      await loadAdminData();
      onFeedsSynced?.();
    } catch (err) {
      notify(err.message || 'Failed to delete feed', 'error');
    }
  }

  async function handleSyncAll() {
    setSyncingAll(true);
    setLastSummary(null);
    try {
      const summary = await api.ingestAllFeeds();
      setLastSummary(summary);
      notify(
        `Sync complete: ${summary.total_items_added} new articles (${summary.feeds_succeeded}/${summary.feeds_processed} feeds ok)`
      );
      await loadAdminData();
      onFeedsSynced?.();
    } catch (err) {
      notify(err.message || 'Feed sync failed', 'error');
    } finally {
      setSyncingAll(false);
    }
  }

  async function handleSyncOne(feed) {
    setSyncingId(feed.id);
    try {
      const run = await api.ingestSingleFeed(feed.id);
      if (run.status === 'success') {
        notify(`${feed.name}: +${run.items_added} new, ${run.duplicates_skipped} duplicates skipped`);
      } else {
        notify(`${feed.name} failed: ${run.error_message || 'Fetch error'}`, 'error');
      }
      await loadAdminData();
      onFeedsSynced?.();
    } catch (err) {
      notify(err.message || 'Single feed sync failed', 'error');
    } finally {
      setSyncingId(null);
    }
  }

  async function handleSaveKeywords(e) {
    e.preventDefault();
    if (!editingCategory) return;
    try {
      const kws = keywordsText
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      await api.updateCategoryKeywords(editingCategory.id, kws);
      notify(`Updated keyword rules for ${editingCategory.name}`);
      setEditingCategory(null);
      onFeedsSynced?.();
    } catch (err) {
      notify(err.message || 'Failed to update keywords', 'error');
    }
  }

  const enabledCount = feeds.filter((f) => f.enabled).length;
  const healthyCount = feeds.filter((f) => f.last_status === 'success').length;
  const errorCount = feeds.filter((f) => f.last_status === 'error').length;
  const totalIndexed = feeds.reduce((acc, f) => acc + (f.article_count || 0), 0);

  return (
    <section className="space-y-6">
      {/* Header & Sync Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
            <Activity className="h-4 w-4" />
            Administration &amp; Ingestion Health
          </div>
          <h2 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">
            RSS / Atom Feed Control Center
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Manage approved publishers, trigger manual ingestion, inspect errors, and tune categorization rules.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={openAddModal}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <Plus className="h-4 w-4" />
            Add Feed
          </button>
          <button
            type="button"
            disabled={syncingAll}
            onClick={handleSyncAll}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${syncingAll ? 'animate-spin' : ''}`} />
            {syncingAll ? 'Syncing Feeds...' : 'Sync All Feeds Now'}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-xs font-medium text-slate-500">Configured Feeds</div>
          <div className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">
            {feeds.length}{' '}
            <span className="text-xs font-normal text-slate-400">({enabledCount} active)</span>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-xs font-medium text-slate-500">Healthy Feeds</div>
          <div className="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {healthyCount}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-xs font-medium text-slate-500">Failing Feeds</div>
          <div className="mt-1 text-2xl font-bold text-rose-600 dark:text-rose-400">
            {errorCount}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-xs font-medium text-slate-500">Total Articles Stored</div>
          <div className="mt-1 text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {totalIndexed}
          </div>
        </div>
      </div>

      {/* Manual Sync Batch Summary Banner */}
      {lastSummary && (
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-900 dark:border-indigo-900/50 dark:bg-indigo-950/40 dark:text-indigo-200">
          <strong>Batch Sync Result:</strong> Processed {lastSummary.feeds_processed} feeds —{' '}
          {lastSummary.feeds_succeeded} succeeded, {lastSummary.feeds_failed} failed. Found{' '}
          {lastSummary.total_items_found} items, added {lastSummary.total_items_added} new articles,
          skipped {lastSummary.total_duplicates_skipped} duplicates.
        </div>
      )}

      {/* Sub-tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        {[
          { id: 'feeds', label: `Feed Sources (${feeds.length})` },
          { id: 'logs', label: `Ingestion Logs (${runs.length})` },
          { id: 'rules', label: 'Category Keyword Rules' },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`border-b-2 px-4 py-2.5 text-sm font-semibold transition ${
              activeTab === tab.id
                ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Feed Sources Table */}
      {activeTab === 'feeds' && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'all', label: `All Sources (${feeds.length})` },
              { id: 'india', label: `Indian News (${feeds.filter((f) => f.region === 'india').length})` },
              { id: 'global', label: `Global (${feeds.filter((f) => f.region === 'global').length})` },
            ].map((rf) => (
              <button
                key={rf.id}
                type="button"
                onClick={() => setRegionFilter(rf.id)}
                className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                  regionFilter === rf.id
                    ? 'bg-slate-900 text-white dark:bg-indigo-600'
                    : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300'
                }`}
              >
                {rf.label}
              </button>
            ))}
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {loading ? (
              <div className="p-8 text-center text-sm text-slate-500">Loading feed sources...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-3 font-semibold">Publisher &amp; URL</th>
                      <th className="px-3 py-3 font-semibold">Region / Category</th>
                      <th className="px-3 py-3 font-semibold">Status</th>
                      <th className="px-3 py-3 font-semibold">Last Fetch</th>
                      <th className="px-3 py-3 font-semibold text-right">Items</th>
                      <th className="px-3 py-3 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {feeds
                      .filter((f) => regionFilter === 'all' || f.region === regionFilter)
                      .map((feed) => (
                      <tr key={feed.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30">
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
                            <Rss className="h-3.5 w-3.5 shrink-0 text-indigo-500" />
                            <span className="truncate">{feed.name}</span>
                          </div>
                          <div className="mt-0.5 max-w-[190px] truncate font-mono-code text-xs text-slate-400 xl:max-w-xs">
                            {feed.feed_url}
                          </div>
                          {feed.last_status === 'error' && feed.last_error && (
                            <div className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                              Error: {feed.last_error}
                            </div>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-600 dark:text-slate-300">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                                feed.region === 'india'
                                  ? 'bg-orange-50 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300'
                                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                              }`}
                            >
                              {feed.region}
                            </span>
                            <span>{feed.default_category_name || 'Uncategorized'}</span>
                          </div>
                        </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-col gap-1">
                          <button
                            type="button"
                            onClick={() => handleToggleEnabled(feed)}
                            className={`inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              feed.enabled
                                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                                : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                            }`}
                          >
                            {feed.enabled ? 'Enabled' : 'Disabled'}
                          </button>
                          {feed.last_status && (
                            <span
                              className={`inline-flex w-fit items-center gap-1 text-xs ${
                                feed.last_status === 'success'
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-rose-600 dark:text-rose-400'
                              }`}
                            >
                              {feed.last_status === 'success' ? (
                                <CheckCircle2 className="h-3 w-3" />
                              ) : (
                                <AlertTriangle className="h-3 w-3" />
                              )}
                              {feed.last_status}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500 dark:text-slate-400">
                        {feed.last_fetched_at ? formatRelativeTime(feed.last_fetched_at) : 'Never'}
                      </td>
                      <td className="px-3 py-3 text-right font-mono-code text-xs font-semibold text-slate-700 dark:text-slate-300">
                        {feed.article_count}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            disabled={syncingId === feed.id}
                            onClick={() => handleSyncOne(feed)}
                            title="Sync this feed now"
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-indigo-50 hover:text-indigo-600 dark:hover:bg-slate-800"
                          >
                            <RefreshCw
                              className={`h-4 w-4 ${syncingId === feed.id ? 'animate-spin' : ''}`}
                            />
                          </button>
                          <button
                            type="button"
                            onClick={() => openEditModal(feed)}
                            title="Edit feed"
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
                          >
                            <Edit3 className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteFeed(feed)}
                            title="Delete feed"
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-slate-800"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        </div>
      )}

      {/* Ingestion Logs Table */}
      {activeTab === 'logs' && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-semibold">Timestamp</th>
                  <th className="px-4 py-3 font-semibold">Source</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold text-right">Found</th>
                  <th className="px-4 py-3 font-semibold text-right">Added</th>
                  <th className="px-4 py-3 font-semibold text-right">Dups Skipped</th>
                  <th className="px-4 py-3 font-semibold">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                      {run.feed_source_name}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          run.status === 'success'
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                            : 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono-code text-xs">{run.items_found}</td>
                    <td className="px-4 py-3 text-right font-mono-code text-xs text-emerald-600 dark:text-emerald-400">
                      +{run.items_added}
                    </td>
                    <td className="px-4 py-3 text-right font-mono-code text-xs text-slate-400">
                      {run.duplicates_skipped}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-xs text-rose-600 dark:text-rose-400">
                      {run.error_message || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Category Keyword Rules */}
      {activeTab === 'rules' && (
        <div className="grid gap-4 sm:grid-cols-2">
          {categories
            .filter((c) => c.slug !== 'uncategorized')
            .map((cat) => (
              <div
                key={cat.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-slate-900 dark:text-white">{cat.name}</h4>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingCategory(cat);
                      setKeywordsText((cat.keywords || []).join(', '));
                    }}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    <Edit3 className="h-3 w-3" />
                    Edit Rules
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(cat.keywords || []).map((kw) => (
                    <span
                      key={kw}
                      className="rounded-md bg-slate-100 px-2 py-0.5 font-mono-code text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Add / Edit Feed Modal */}
      {showAddForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <button
              onClick={() => setShowAddForm(false)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"
            >
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              {editingFeed ? 'Edit RSS/Atom Feed' : 'Add RSS/Atom Feed'}
            </h3>
            <form onSubmit={handleSaveFeed} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                  Publisher Name
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="MIT Technology Review"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                  Feed URL (RSS or Atom)
                </label>
                <input
                  type="url"
                  required
                  value={formUrl}
                  onChange={(e) => setFormUrl(e.target.value)}
                  placeholder="https://example.com/rss.xml"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                    Region
                  </label>
                  <select
                    value={formRegion}
                    onChange={(e) => setFormRegion(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  >
                    <option value="india">India</option>
                    <option value="global">Global</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                    Source Type
                  </label>
                  <select
                    value={formSourceType}
                    onChange={(e) => setFormSourceType(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  >
                    <option value="rss">RSS / Atom Feed</option>
                    <option value="gnews_api">GNews API</option>
                    <option value="newsdata_api">NewsData.io API</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                  Default Category Fallback
                </label>
                <select
                  value={formCategoryId}
                  onChange={(e) => setFormCategoryId(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="">Uncategorized</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={formEnabled}
                  onChange={(e) => setFormEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                />
                Enable periodic scheduled fetching
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingFeed}
                  className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {savingFeed ? 'Saving...' : 'Save Feed'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Keywords Modal */}
      {editingCategory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Keyword Rules: {editingCategory.name}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Comma-separated keywords used when RSS metadata tags are missing or ambiguous.
            </p>
            <form onSubmit={handleSaveKeywords} className="mt-4 space-y-4">
              <textarea
                rows={4}
                value={keywordsText}
                onChange={(e) => setKeywordsText(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono-code text-xs dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingCategory(null)}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Update Rules
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
