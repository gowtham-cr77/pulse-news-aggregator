import { useEffect, useRef } from 'react';
import {
  Bookmark,
  Compass,
  Flag,
  LogOut,
  Moon,
  Search,
  Shield,
  Sparkles,
  Sun,
  User as UserIcon,
  X,
} from 'lucide-react';

export default function Navbar({
  view,
  onChangeView,
  selectedRegion,
  onQuickIndiaFilter,
  searchQuery,
  onSearchChange,
  user,
  bookmarksCount,
  darkMode,
  onToggleDarkMode,
  onOpenAuth,
  onOpenPreferences,
  onLogout,
}) {
  const searchInputRef = useRef(null);

  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const navItems = [
    { id: 'discover', label: 'Discover', icon: Compass },
    { id: 'india', label: 'Indian News', icon: Flag, isRegionShortcut: true },
    { id: 'for-you', label: 'For You', icon: Sparkles },
    { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark, badge: bookmarksCount },
  ];
  if (user?.role === 'admin') {
    navItems.push({ id: 'admin', label: 'Admin', icon: Shield });
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-md dark:border-slate-800/80 dark:bg-slate-950/85">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {/* Brand */}
        <button
          type="button"
          onClick={() => onChangeView('discover')}
          className="flex items-center gap-2.5 text-left"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-white shadow-xs dark:bg-indigo-600">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" />
          </span>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
                PULSE
              </span>
              <span className="hidden rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-600 sm:inline dark:bg-indigo-950 dark:text-indigo-300">
                RSS
              </span>
            </div>
            <p className="hidden text-[11px] text-slate-500 md:block dark:text-slate-400">
              News Discovery &amp; Aggregation
            </p>
          </div>
        </button>

        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              onSearchChange(e.target.value);
              if (view === 'admin' || view === 'bookmarks') {
                onChangeView('discover');
              }
            }}
            placeholder="Search headlines & descriptions... (press /)"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-8 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-800 dark:bg-slate-900 dark:text-white dark:focus:bg-slate-900"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-2 rounded p-0.5 text-slate-400 hover:text-slate-700"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Desktop Nav + User Actions */}
        <div className="flex items-center gap-2">
          <nav className="hidden items-center gap-1 lg:flex">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.isRegionShortcut
                ? view === 'discover' && selectedRegion === 'india'
                : item.id === 'discover'
                  ? view === 'discover' && selectedRegion !== 'india'
                  : view === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() =>
                    item.isRegionShortcut
                      ? onQuickIndiaFilter?.()
                      : onChangeView(item.id)
                  }
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition ${
                    active
                      ? item.isRegionShortcut
                        ? 'bg-orange-600 text-white'
                        : 'bg-slate-900 text-white dark:bg-indigo-600'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                  {item.badge > 0 && (
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                        active
                          ? 'bg-white/20 text-white'
                          : 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <button
            type="button"
            onClick={onToggleDarkMode}
            className="rounded-xl border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-100 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label="Toggle color theme"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {user ? (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={onOpenPreferences}
                className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 sm:inline-flex dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                title="Manage preferred topics"
              >
                <UserIcon className="h-3.5 w-3.5 text-indigo-500" />
                <span className="max-w-[110px] truncate">{user.display_name}</span>
                {user.role === 'admin' && (
                  <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                    Admin
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={onLogout}
                className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:border-slate-800 dark:hover:bg-slate-800"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={onOpenAuth}
              className="rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-indigo-700 sm:text-sm"
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Mobile Navigation Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-t border-slate-100 px-4 py-2 lg:hidden dark:border-slate-800/70">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = item.isRegionShortcut
            ? view === 'discover' && selectedRegion === 'india'
            : item.id === 'discover'
              ? view === 'discover' && selectedRegion !== 'india'
              : view === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() =>
                item.isRegionShortcut
                  ? onQuickIndiaFilter?.()
                  : onChangeView(item.id)
              }
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                active
                  ? item.isRegionShortcut
                    ? 'bg-orange-600 text-white'
                    : 'bg-slate-900 text-white dark:bg-indigo-600'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {item.label}
              {item.badge > 0 && <span className="ml-0.5 opacity-80">({item.badge})</span>}
            </button>
          );
        })}
      </div>
    </header>
  );
}
