import { TrendingUp, SlidersHorizontal, Info, Sparkles, Radio } from 'lucide-react';

export default function TrendingSidebar({
  trending,
  trendingWindow,
  onChangeTrendingWindow,
  selectedRegion,
  onSelectTopic,
  activeQuery,
  user,
  preferredCategoryNames,
  onOpenPreferences,
  totalArticles,
  sourcesCount,
}) {
  const topics = trending?.topics || [];
  const maxMentions = topics.length > 0 ? Math.max(...topics.map((t) => t.mention_count), 1) : 1;

  return (
    <aside className="space-y-5">
      {/* Trending Topics Widget (FR-10) */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400">
              <TrendingUp className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                {selectedRegion === 'india' ? 'Trending in India' : 'Trending Topics'}
              </h3>
              <p className="text-[11px] text-slate-400">
                {selectedRegion === 'india' ? 'Indian news frequency' : 'Frequency indicator'}
              </p>
            </div>
          </div>

          <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-xs dark:bg-slate-800">
            {['24h', '7d'].map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => onChangeTrendingWindow(w)}
                className={`rounded-md px-2 py-1 font-medium transition ${
                  trendingWindow === w
                    ? 'bg-white text-slate-900 shadow-xs dark:bg-slate-700 dark:text-white'
                    : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
                }`}
              >
                {w}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 space-y-2.5">
          {topics.length === 0 ? (
            <p className="py-4 text-center text-xs text-slate-400">
              Not enough recent articles to compute keyword trends yet.
            </p>
          ) : (
            topics.map((item, idx) => {
              const pct = Math.max(12, Math.round((item.mention_count / maxMentions) * 100));
              const isSelected = activeQuery?.toLowerCase() === item.topic.toLowerCase();
              return (
                <button
                  key={item.topic}
                  type="button"
                  onClick={() => onSelectTopic(isSelected ? '' : item.topic)}
                  className={`group block w-full rounded-xl border px-3 py-2 text-left transition ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50/70 dark:border-indigo-500 dark:bg-indigo-950/40'
                      : 'border-transparent hover:border-slate-200 hover:bg-slate-50 dark:hover:border-slate-800 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800 group-hover:text-indigo-600 dark:text-slate-200 dark:group-hover:text-indigo-400">
                      <span className="mr-1.5 font-mono-code text-[11px] text-slate-400">
                        {String(idx + 1).padStart(2, '0')}
                      </span>
                      {item.topic}
                    </span>
                    <span className="font-mono-code text-[11px] text-slate-500 dark:text-slate-400">
                      {item.mention_count}
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500 transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </button>
              );
            })
          )}
        </div>

        <div className="mt-4 flex items-start gap-2 rounded-xl bg-slate-50 p-2.5 text-[11px] leading-relaxed text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span>
            {trending?.disclaimer ||
              'Frequency-based indicator over recent articles, not a claim of objective importance.'}
          </span>
        </div>
      </div>

      {/* Personalization Card (FR-08) */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">My Topics</h3>
          </div>
          {user && (
            <button
              type="button"
              onClick={onOpenPreferences}
              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400"
            >
              <SlidersHorizontal className="h-3 w-3" />
              Edit
            </button>
          )}
        </div>

        {user ? (
          preferredCategoryNames.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {preferredCategoryNames.map((name) => (
                <span
                  key={name}
                  className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-300"
                >
                  {name}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              No preferred categories selected yet. Pick topics to personalize your feed.
            </p>
          )
        ) : (
          <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            Sign in as a reader to bookmark articles and personalize your home feed by topic.
          </p>
        )}
      </div>

      {/* Pulse Index Summary */}
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-900 to-indigo-950 p-5 text-white shadow-xs dark:border-slate-800">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-300">
          <Radio className="h-3.5 w-3.5 animate-pulse" />
          Live Aggregation
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-white/10 p-3">
            <div className="text-xl font-bold">{totalArticles}</div>
            <div className="text-[11px] text-slate-300">Matching Stories</div>
          </div>
          <div className="rounded-xl bg-white/10 p-3">
            <div className="text-xl font-bold">{sourcesCount}</div>
            <div className="text-[11px] text-slate-300">Active Sources</div>
          </div>
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-slate-300">
          Ethical RSS aggregation: PULSE stores metadata &amp; short snippets only and links directly to original publishers.
        </p>
      </div>
    </aside>
  );
}
