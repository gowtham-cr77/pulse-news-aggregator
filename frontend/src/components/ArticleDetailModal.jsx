import { Bookmark, Calendar, ExternalLink, Layers, Tag, X } from 'lucide-react';

export default function ArticleDetailModal({
  article,
  onClose,
  onToggleBookmark,
  categories,
  user,
  onCategoryOverridden,
}) {
  if (!article) return null;

  const publishedStr = article.published_at
    ? new Date(article.published_at).toLocaleString()
    : 'Not specified by publisher';
  const fetchedStr = article.fetched_at
    ? new Date(article.fetched_at).toLocaleString()
    : 'Unknown';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
      <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          aria-label="Close detail view"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Source attribution header */}
        <div className="flex flex-wrap items-center gap-2.5 pr-8">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-800 dark:bg-slate-800 dark:text-slate-200">
            <span className="flex h-4 w-4 items-center justify-center rounded bg-indigo-600 text-[10px] font-bold text-white">
              {article.source_name.slice(0, 1).toUpperCase()}
            </span>
            {article.source_name}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-300">
            <Tag className="h-3 w-3" />
            {article.category_name || 'Uncategorized'}
          </span>
          {article.source_region === 'india' && (
            <span className="inline-flex items-center rounded-full border border-orange-200 bg-orange-50 px-2.5 py-0.5 text-xs font-semibold text-orange-700 dark:border-orange-800/60 dark:bg-orange-950/50 dark:text-orange-300">
              Indian News
            </span>
          )}
        </div>

        <h2 className="mt-4 text-2xl font-bold leading-tight text-slate-900 dark:text-white">
          {article.title}
        </h2>

        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" />
            Published: {publishedStr}
          </span>
          <span>Indexed: {fetchedStr}</span>
        </div>

        {/* Feed-provided snippet */}
        <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-800/40">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Feed Summary Snippet
          </p>
          <p className="mt-2 text-base leading-relaxed text-slate-700 dark:text-slate-300">
            {article.description || 'No description snippet was provided in the RSS feed for this article.'}
          </p>
        </div>

        {/* Cross-source duplicate attribution */}
        {article.also_seen_sources?.length > 0 && (
          <div className="mt-4 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Layers className="h-3.5 w-3.5 text-indigo-500" />
              Also Covered By ({article.also_seen_sources.length})
            </div>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {article.also_seen_sources.map((src) => (
                <a
                  key={`${src.source_id}-${src.url}`}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  {src.source_name}
                  <ExternalLink className="h-3 w-3" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Admin category override */}
        {user?.role === 'admin' && categories?.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed border-slate-300 px-4 py-3 dark:border-slate-700">
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
              Admin Category Override:
            </span>
            <select
              value={article.category_id || ''}
              onChange={(e) => onCategoryOverridden?.(article.id, Number(e.target.value))}
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Attribution disclaimer */}
        <p className="mt-5 text-xs text-slate-400 dark:text-slate-500">
          PULSE indexes metadata and short RSS snippets only. Full content belongs to{' '}
          <span className="font-medium text-slate-600 dark:text-slate-300">{article.source_name}</span>.
        </p>

        {/* Actions */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
          <button
            type="button"
            onClick={() => onToggleBookmark(article)}
            className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition ${
              article.is_bookmarked
                ? 'border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300'
                : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
            }`}
          >
            <Bookmark className={`h-4 w-4 ${article.is_bookmarked ? 'fill-current' : ''}`} />
            {article.is_bookmarked ? 'Bookmarked' : 'Save Bookmark'}
          </button>

          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
          >
            Read Full Article at {article.source_name}
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
