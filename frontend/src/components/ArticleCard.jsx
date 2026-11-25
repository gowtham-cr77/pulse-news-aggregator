import { Bookmark, ExternalLink, Layers, Clock } from 'lucide-react';

const CATEGORY_STYLES = {
  technology: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/50 dark:text-indigo-300 dark:border-indigo-800/60',
  business: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800/60',
  politics: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800/60',
  science: 'bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-950/50 dark:text-cyan-300 dark:border-cyan-800/60',
  sports: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800/60',
  uncategorized: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
};

export function formatRelativeTime(isoDate) {
  if (!isoDate) return 'Recently';
  const date = new Date(isoDate);
  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function ArticleCard({
  article,
  isPreferredCategory,
  onToggleBookmark,
  onOpenDetail,
  onFilterSource,
}) {
  const catSlug = article.category_slug || 'uncategorized';
  const catStyle = CATEGORY_STYLES[catSlug] || CATEGORY_STYLES.uncategorized;
  const displayDate = article.published_at || article.fetched_at;
  const alsoCount = article.also_seen_sources?.length || 0;

  return (
    <article className="group flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs transition duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
      <div>
        {/* Meta row */}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${catStyle}`}>
              {article.category_name || 'Uncategorized'}
            </span>
            {article.source_region === 'india' && (
              <span className="inline-flex items-center rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-[11px] font-semibold text-orange-700 dark:border-orange-800/60 dark:bg-orange-950/50 dark:text-orange-300">
                India
              </span>
            )}
            {isPreferredCategory && (
              <span className="inline-flex items-center rounded-full bg-indigo-600/10 px-2 py-0.5 text-[11px] font-medium text-indigo-600 dark:bg-indigo-400/10 dark:text-indigo-300">
                For You
              </span>
            )}
          </div>

          <span
            className="inline-flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500"
            title={displayDate ? new Date(displayDate).toLocaleString() : ''}
          >
            <Clock className="h-3 w-3" />
            {formatRelativeTime(displayDate)}
          </span>
        </div>

        {/* Headline */}
        <h3
          onClick={() => onOpenDetail(article)}
          className="cursor-pointer text-lg font-bold leading-snug text-slate-900 transition group-hover:text-indigo-600 dark:text-slate-100 dark:group-hover:text-indigo-400"
        >
          {article.title}
        </h3>

        {/* Snippet */}
        {article.description && (
          <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            {article.description}
          </p>
        )}
      </div>

      {/* Footer Attribution & Actions */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3.5 dark:border-slate-800/80">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onFilterSource?.(article.source_id)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            title={`Filter by ${article.source_name}`}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded bg-slate-800 text-[10px] font-bold text-white dark:bg-indigo-500">
              {article.source_name.slice(0, 1).toUpperCase()}
            </span>
            {article.source_name}
          </button>

          {alsoCount > 0 && (
            <button
              type="button"
              onClick={() => onOpenDetail(article)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-500 hover:border-indigo-300 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-400"
              title="Duplicate story detected across multiple feeds"
            >
              <Layers className="h-3 w-3" />
              +{alsoCount} source{alsoCount > 1 ? 's' : ''}
            </button>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onToggleBookmark(article)}
            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
              article.is_bookmarked
                ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
            }`}
            aria-label={article.is_bookmarked ? 'Remove bookmark' : 'Bookmark article'}
            title={article.is_bookmarked ? 'Saved to bookmarks' : 'Save for later'}
          >
            <Bookmark
              className={`h-3.5 w-3.5 ${article.is_bookmarked ? 'fill-current' : ''}`}
            />
            <span className="hidden sm:inline">{article.is_bookmarked ? 'Saved' : 'Save'}</span>
          </button>

          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-600 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-indigo-400 dark:hover:text-white"
          >
            Read
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </article>
  );
}
