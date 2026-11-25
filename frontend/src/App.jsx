import { useCallback, useEffect, useState } from 'react';
import {
  Bookmark,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Filter,
  Flag,
  Globe,
  Newspaper,
  RefreshCw,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { api, getStoredToken, setStoredToken } from './api/client';
import AdminDashboard from './components/AdminDashboard';
import ArticleCard from './components/ArticleCard';
import ArticleDetailModal from './components/ArticleDetailModal';
import AuthModal from './components/AuthModal';
import Navbar from './components/Navbar';
import PreferencesModal from './components/PreferencesModal';
import TrendingSidebar from './components/TrendingSidebar';

export default function App() {
  // Theme state
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('pulse_theme') === 'dark');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('pulse_theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // Navigation & Auth state
  const [view, setView] = useState('discover'); // discover | for-you | bookmarks | admin
  const [user, setUser] = useState(null);
  const [preferredCategoryIds, setPreferredCategoryIds] = useState([]);
  const [authOpen, setAuthOpen] = useState(false);
  const [prefsOpen, setPrefsOpen] = useState(false);
  const [detailArticle, setDetailArticle] = useState(null);

  // Reference metadata
  const [categories, setCategories] = useState([]);
  const [sources, setSources] = useState([]);
  const [trending, setTrending] = useState(null);
  const [trendingWindow, setTrendingWindow] = useState('7d');

  // Feed filters & pagination
  const [selectedRegion, setSelectedRegion] = useState('all'); // all | india | global
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedSource, setSelectedSource] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [refreshingLive, setRefreshingLive] = useState(false);

  // Articles & Bookmarks state
  const [articlesData, setArticlesData] = useState({ items: [], total: 0, page: 1, total_pages: 0 });
  const [bookmarksData, setBookmarksData] = useState({ items: [], total: 0, page: 1, total_pages: 0 });
  const [bookmarksPage, setBookmarksPage] = useState(1);
  const [loadingFeed, setLoadingFeed] = useState(true);

  // Toast feedback
  const [toast, setToast] = useState(null);
  const notify = useCallback((message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3800);
  }, []);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Restore session on mount
  useEffect(() => {
    async function restoreUser() {
      if (!getStoredToken()) return;
      try {
        const me = await api.getMe();
        setUser(me);
        const prefs = await api.getPreferences();
        setPreferredCategoryIds(prefs.category_ids || []);
      } catch {
        setStoredToken(null);
      }
    }
    restoreUser();
  }, []);

  // Load categories, sources, and trending (scoped by active region)
  const loadMetadata = useCallback(async () => {
    try {
      const [cats, srcs, trend] = await Promise.all([
        api.getCategories(selectedRegion),
        api.getSources(selectedRegion),
        api.getTrending(trendingWindow, 10, selectedRegion),
      ]);
      setCategories(cats);
      setSources(srcs);
      setTrending(trend);
    } catch {
      // Non-fatal metadata load failure
    }
  }, [trendingWindow, selectedRegion]);

  useEffect(() => {
    loadMetadata();
  }, [loadMetadata]);

  // Load main / personalized article feed
  const loadArticles = useCallback(async () => {
    setLoadingFeed(true);
    try {
      const data = await api.getArticles({
        page,
        size: pageSize,
        region: selectedRegion,
        category: selectedCategory,
        source: selectedSource,
        from: dateFrom || undefined,
        to: dateTo || undefined,
        q: debouncedQuery || undefined,
        prioritize_preferred: view === 'for-you' && Boolean(user),
      });
      setArticlesData(data);
    } catch (err) {
      notify(err.message || 'Could not load articles', 'error');
    } finally {
      setLoadingFeed(false);
    }
  }, [page, pageSize, selectedRegion, selectedCategory, selectedSource, dateFrom, dateTo, debouncedQuery, view, user, notify]);

  useEffect(() => {
    if (view === 'discover' || view === 'for-you') {
      loadArticles();
    }
  }, [view, loadArticles]);

  // Load bookmarks when signed in
  const loadBookmarks = useCallback(async () => {
    if (!user) {
      setBookmarksData({ items: [], total: 0, page: 1, total_pages: 0 });
      return;
    }
    try {
      const data = await api.getBookmarks(bookmarksPage, pageSize);
      setBookmarksData(data);
    } catch {
      // Ignore if unauthorized
    }
  }, [user, bookmarksPage, pageSize]);

  useEffect(() => {
    loadBookmarks();
  }, [loadBookmarks]);

  function handleAuthSuccess(authRes) {
    setStoredToken(authRes.access_token);
    setUser(authRes.user);
    notify(`Signed in as ${authRes.user.display_name}`);
    api
      .getPreferences()
      .then((prefs) => setPreferredCategoryIds(prefs.category_ids || []))
      .catch(() => {});
  }

  function handleLogout() {
    api.logout().catch(() => {});
    setStoredToken(null);
    setUser(null);
    setPreferredCategoryIds([]);
    if (view === 'admin' || view === 'bookmarks' || view === 'for-you') {
      setView('discover');
    }
    notify('Signed out');
  }

  async function handleToggleBookmark(article) {
    if (!user) {
      setAuthOpen(true);
      notify('Sign in to save bookmarks', 'info');
      return;
    }
    try {
      if (article.is_bookmarked) {
        await api.removeBookmark(article.id);
        notify('Removed from bookmarks');
      } else {
        await api.addBookmark(article.id);
        notify('Saved to bookmarks');
      }
      // Update local state optimistically and refresh bookmarks list
      setArticlesData((prev) => ({
        ...prev,
        items: prev.items.map((item) =>
          item.id === article.id ? { ...item, is_bookmarked: !article.is_bookmarked } : item
        ),
      }));
      if (detailArticle?.id === article.id) {
        setDetailArticle((prev) => (prev ? { ...prev, is_bookmarked: !prev.is_bookmarked } : null));
      }
      loadBookmarks();
    } catch (err) {
      notify(err.message || 'Bookmark update failed', 'error');
    }
  }

  async function handleCategoryOverride(articleId, categoryId) {
    try {
      await api.overrideArticleCategory(articleId, categoryId);
      notify('Article category updated');
      setDetailArticle(null);
      loadArticles();
      loadMetadata();
    } catch (err) {
      notify(err.message || 'Category override failed', 'error');
    }
  }

  async function handleRefreshLive() {
    setRefreshingLive(true);
    try {
      const res = await api.refreshLiveNews(selectedRegion);
      notify(res.message);
      await Promise.all([loadMetadata(), loadArticles()]);
    } catch (err) {
      notify(err.message || 'Live refresh failed', 'error');
    } finally {
      setRefreshingLive(false);
    }
  }

  function handleRegionChange(nextRegion) {
    setSelectedRegion(nextRegion);
    setSelectedSource('all');
    setPage(1);
  }

  function resetFilters() {
    setSelectedRegion('all');
    setSelectedCategory('all');
    setSelectedSource('all');
    setDateFrom('');
    setDateTo('');
    setSearchQuery('');
    setDebouncedQuery('');
    setPage(1);
  }

  const preferredCategoryNames = categories
    .filter((c) => preferredCategoryIds.includes(c.id))
    .map((c) => c.name);

  const hasActiveFilters =
    selectedRegion !== 'all' ||
    selectedCategory !== 'all' ||
    selectedSource !== 'all' ||
    dateFrom !== '' ||
    dateTo !== '' ||
    debouncedQuery !== '';

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-100">
      <Navbar
        view={view}
        selectedRegion={selectedRegion}
        onQuickIndiaFilter={() => {
          setView('discover');
          handleRegionChange(selectedRegion === 'india' ? 'all' : 'india');
        }}
        onChangeView={(nextView) => {
          if ((nextView === 'bookmarks' || nextView === 'for-you') && !user) {
            setAuthOpen(true);
            return;
          }
          if (nextView === 'discover') {
            setSelectedRegion('all');
          }
          setView(nextView);
        }}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        user={user}
        bookmarksCount={bookmarksData.total}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode((d) => !d)}
        onOpenAuth={() => setAuthOpen(true)}
        onOpenPreferences={() => setPrefsOpen(true)}
        onLogout={handleLogout}
      />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
        {/* Toast notification */}
        {toast && (
          <div
            className={`fixed bottom-5 right-5 z-50 rounded-xl border px-4 py-3 text-sm font-medium shadow-xl backdrop-blur-md ${
              toast.type === 'error'
                ? 'border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200'
                : 'border-emerald-300 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
            }`}
          >
            {toast.message}
          </div>
        )}

        {view === 'admin' && user?.role === 'admin' ? (
          <AdminDashboard
            categories={categories}
            onFeedsSynced={() => {
              loadMetadata();
              loadArticles();
            }}
            notify={notify}
          />
        ) : view === 'bookmarks' ? (
          <section className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                  <Bookmark className="h-4 w-4" />
                  Saved Reading List
                </div>
                <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">
                  Your Bookmarks ({bookmarksData.total})
                </h1>
              </div>
              <button
                type="button"
                onClick={() => setView('discover')}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
              >
                Back to Feed
              </button>
            </div>

            {bookmarksData.items.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
                <Bookmark className="mx-auto h-10 w-10 text-slate-300 dark:text-slate-700" />
                <h3 className="mt-3 text-lg font-semibold text-slate-800 dark:text-white">
                  No saved articles yet
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  Click &ldquo;Save&rdquo; on any story in the Discover feed to keep it here for later.
                </p>
              </div>
            ) : (
              <>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {bookmarksData.items.map((article) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      isPreferredCategory={preferredCategoryIds.includes(article.category_id)}
                      onToggleBookmark={handleToggleBookmark}
                      onOpenDetail={setDetailArticle}
                      onFilterSource={(srcId) => {
                        setSelectedSource(String(srcId));
                        setView('discover');
                      }}
                    />
                  ))}
                </div>
                {bookmarksData.total_pages > 1 && (
                  <Pagination
                    page={bookmarksPage}
                    totalPages={bookmarksData.total_pages}
                    onPageChange={setBookmarksPage}
                  />
                )}
              </>
            )}
          </section>
        ) : (
          /* Discover & For You Views */
          <div className="grid grid-cols-1 gap-7 lg:grid-cols-12">
            {/* Main Feed Column */}
            <div className="space-y-5 lg:col-span-8">
              {/* Hero / Header Banner */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                      {view === 'for-you' ? (
                        <>
                          <Sparkles className="h-3.5 w-3.5" />
                          Personalized Feed
                        </>
                      ) : selectedRegion === 'india' ? (
                        <>
                          <Flag className="h-3.5 w-3.5 text-orange-600" />
                          <span className="text-orange-600 dark:text-orange-400">
                            Indian News Edition
                          </span>
                        </>
                      ) : (
                        <>
                          <Newspaper className="h-3.5 w-3.5" />
                          Unified RSS Discovery
                        </>
                      )}
                    </div>
                    <h1 className="mt-1 font-editorial text-3xl tracking-tight text-slate-900 dark:text-white sm:text-4xl">
                      {view === 'for-you'
                        ? 'Stories prioritized around your topics'
                        : selectedRegion === 'india'
                          ? 'Real-time headlines across India'
                          : 'Today’s pulse across trusted publishers'}
                    </h1>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={refreshingLive}
                      onClick={handleRefreshLive}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                      title="Fetch latest live articles from configured sources"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${refreshingLive ? 'animate-spin' : ''}`} />
                      {refreshingLive ? 'Refreshing...' : 'Refresh Live'}
                    </button>
                    {view === 'for-you' && (
                      <button
                        type="button"
                        onClick={() => setPrefsOpen(true)}
                        className="rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300"
                      >
                        Customize Topics
                      </button>
                    )}
                  </div>
                </div>

                {/* Region Switcher (Indian News Filter) */}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {[
                    { id: 'all', label: 'All Regions', icon: Globe },
                    { id: 'india', label: 'Indian News', icon: Flag },
                    { id: 'global', label: 'Global News', icon: Newspaper },
                  ].map((reg) => {
                    const Icon = reg.icon;
                    const active = selectedRegion === reg.id;
                    return (
                      <button
                        key={reg.id}
                        type="button"
                        onClick={() => handleRegionChange(reg.id)}
                        className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                          active
                            ? reg.id === 'india'
                              ? 'border-orange-500 bg-orange-600 text-white shadow-xs'
                              : 'border-indigo-600 bg-indigo-600 text-white shadow-xs'
                            : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                        }`}
                      >
                        <Icon className="h-3.5 w-3.5" />
                        {reg.label}
                      </button>
                    );
                  })}
                </div>

                {/* Category Ribbon */}
                <div className="mt-5 flex items-center gap-2 overflow-x-auto pb-1">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedCategory('all');
                      setPage(1);
                    }}
                    className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                      selectedCategory === 'all'
                        ? 'bg-slate-900 text-white dark:bg-indigo-600'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                    }`}
                  >
                    All Topics
                  </button>
                  {categories.map((cat) => {
                    const active = selectedCategory === cat.slug;
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => {
                          setSelectedCategory(cat.slug);
                          setPage(1);
                        }}
                        className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                          active
                            ? 'bg-slate-900 text-white dark:bg-indigo-600'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                        }`}
                      >
                        {cat.name}
                        <span className="opacity-60">{cat.article_count}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Filter Bar: Publisher & Date Range */}
                <div className="mt-4 flex flex-wrap items-center gap-2.5 border-t border-slate-100 pt-4 dark:border-slate-800">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                    <Filter className="h-3.5 w-3.5" />
                    Filters:
                  </div>

                  <select
                    value={selectedSource}
                    onChange={(e) => {
                      setSelectedSource(e.target.value);
                      setPage(1);
                    }}
                    aria-label="Filter by publisher"
                    className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  >
                    <option value="all">All Publishers ({sources.length})</option>
                    {sources.map((src) => (
                      <option key={src.id} value={String(src.id)}>
                        {src.name}
                      </option>
                    ))}
                  </select>

                  <div className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs dark:border-slate-700 dark:bg-slate-800">
                    <Calendar className="h-3.5 w-3.5 text-slate-400" />
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => {
                        setDateFrom(e.target.value);
                        setPage(1);
                      }}
                      aria-label="From date"
                      className="bg-transparent text-xs text-slate-700 outline-none dark:text-slate-200"
                    />
                    <span className="text-slate-400">to</span>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => {
                        setDateTo(e.target.value);
                        setPage(1);
                      }}
                      aria-label="To date"
                      className="bg-transparent text-xs text-slate-700 outline-none dark:text-slate-200"
                    />
                  </div>

                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={resetFilters}
                      className="inline-flex items-center gap-1 rounded-xl px-2.5 py-1.5 text-xs font-semibold text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
                    >
                      <RotateCcw className="h-3 w-3" />
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {/* Active Search / Result Summary */}
              <div className="flex items-center justify-between px-1 text-xs text-slate-500 dark:text-slate-400">
                <span>
                  Showing <strong className="text-slate-800 dark:text-slate-200">{articlesData.items.length}</strong> of{' '}
                  <strong className="text-slate-800 dark:text-slate-200">{articlesData.total}</strong> articles
                  {debouncedQuery ? ` matching "${debouncedQuery}"` : ''}
                </span>
                {articlesData.total_pages > 0 && (
                  <span>
                    Page {articlesData.page} of {articlesData.total_pages}
                  </span>
                )}
              </div>

              {/* Article Cards Grid */}
              {loadingFeed ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  {[...Array(6)].map((_, idx) => (
                    <div
                      key={idx}
                      className="h-56 animate-pulse rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
                    >
                      <div className="h-4 w-24 rounded bg-slate-200 dark:bg-slate-800" />
                      <div className="mt-4 h-5 w-full rounded bg-slate-200 dark:bg-slate-800" />
                      <div className="mt-2 h-5 w-3/4 rounded bg-slate-200 dark:bg-slate-800" />
                      <div className="mt-4 h-12 w-full rounded bg-slate-100 dark:bg-slate-800/60" />
                    </div>
                  ))}
                </div>
              ) : articlesData.items.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
                  <Newspaper className="mx-auto h-10 w-10 text-slate-300 dark:text-slate-700" />
                  <h3 className="mt-3 text-lg font-semibold text-slate-800 dark:text-white">
                    No matching articles found
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Try adjusting your search query, date range, or category filters.
                  </p>
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={resetFilters}
                      className="mt-4 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
                    >
                      Clear All Filters
                    </button>
                  )}
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {articlesData.items.map((article) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      isPreferredCategory={
                        Boolean(user) && preferredCategoryIds.includes(article.category_id)
                      }
                      onToggleBookmark={handleToggleBookmark}
                      onOpenDetail={setDetailArticle}
                      onFilterSource={(srcId) => {
                        setSelectedSource(String(srcId));
                        setPage(1);
                      }}
                    />
                  ))}
                </div>
              )}

              {/* Pagination */}
              {articlesData.total_pages > 1 && (
                <Pagination
                  page={page}
                  totalPages={articlesData.total_pages}
                  onPageChange={(next) => {
                    setPage(next);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                />
              )}
            </div>

            {/* Right Sidebar */}
            <div className="lg:col-span-4">
              <div className="lg:sticky lg:top-24">
                <TrendingSidebar
                  trending={trending}
                  trendingWindow={trendingWindow}
                  onChangeTrendingWindow={setTrendingWindow}
                  selectedRegion={selectedRegion}
                  onSelectTopic={(topic) => {
                    setSearchQuery(topic);
                    setPage(1);
                  }}
                  activeQuery={debouncedQuery}
                  user={user}
                  preferredCategoryNames={preferredCategoryNames}
                  onOpenPreferences={() => setPrefsOpen(true)}
                  totalArticles={articlesData.total}
                  sourcesCount={sources.filter((s) => s.enabled).length}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        onSuccess={handleAuthSuccess}
      />

      <PreferencesModal
        isOpen={prefsOpen}
        onClose={() => setPrefsOpen(false)}
        categories={categories}
        selectedIds={preferredCategoryIds}
        onSaved={(ids) => {
          setPreferredCategoryIds(ids);
          notify('Topic preferences saved');
          if (view === 'for-you') loadArticles();
        }}
      />

      <ArticleDetailModal
        article={detailArticle}
        onClose={() => setDetailArticle(null)}
        onToggleBookmark={handleToggleBookmark}
        categories={categories}
        user={user}
        onCategoryOverridden={handleCategoryOverride}
      />
    </div>
  );
}

function Pagination({ page, totalPages, onPageChange }) {
  return (
    <div className="flex items-center justify-center gap-2 pt-2">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
      >
        <ChevronLeft className="h-4 w-4" />
        Previous
      </button>

      <span className="rounded-xl bg-slate-100 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
        Page {page} / {totalPages}
      </span>

      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
