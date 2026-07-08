import { useEffect, useState } from 'react';
import { analyticsAPI } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { AnalyticsOverview, PlatformOverview, QueryTrend } from '../types';

export const AnalyticsPage = () => {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [platform, setPlatform] = useState<PlatformOverview | null>(null);
  const [trends, setTrends] = useState<QueryTrend[]>([]);
  const [topics, setTopics] = useState<{ question: string; count: number }[]>([]);

  useEffect(() => {
    Promise.all([
      analyticsAPI.overview(),
      analyticsAPI.trends(7),
      analyticsAPI.topics(),
    ]).then(([o, t, tp]) => {
      setOverview(o.data);
      setTrends(t.data);
      setTopics(tp.data);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    analyticsAPI.platform().then((r) => setPlatform(r.data)).catch(() => {});
  }, [isAdmin]);

  if (!overview) {
    return <div className="p-8 text-center text-muted">Loading analytics...</div>;
  }

  const maxQueries = Math.max(...trends.map((t) => t.queries), 1);

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>

      {isAdmin && platform && (
        <div className="app-card p-6 mb-8 border-indigo-500/30">
          <h2 className="text-sm font-semibold text-indigo-400 mb-4">Platform Overview (Admin)</h2>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { label: 'Users', value: platform.users_total },
              { label: 'Documents', value: platform.documents_total },
              { label: 'Queries', value: platform.queries_total },
              { label: 'Conversations', value: platform.conversations_total },
              { label: 'Active (7d)', value: platform.active_users_week },
            ].map((c) => (
              <div key={c.label}>
                <p className="text-xs text-muted">{c.label}</p>
                <p className="text-xl font-bold">{c.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Documents', value: overview.documents_ready },
          { label: 'Total Queries', value: overview.queries_total },
          { label: 'This Week', value: overview.queries_this_week },
          { label: 'Tokens Used', value: overview.tokens_used_total },
        ].map((c) => (
          <div key={c.label} className="app-card p-5">
            <p className="text-xs text-muted">{c.label}</p>
            <p className="text-2xl font-bold mt-1">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="app-card p-6">
          <h2 className="text-sm font-semibold mb-4">Query Volume (7 days)</h2>
          <div className="flex items-end gap-2 h-32">
            {trends.map((t) => (
              <div key={t.date} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-indigo-500/60 rounded-t"
                  style={{ height: `${(t.queries / maxQueries) * 100}%`, minHeight: t.queries ? 4 : 0 }}
                />
                <span className="text-[10px] text-muted">{t.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="app-card p-6">
          <h2 className="text-sm font-semibold mb-4">Popular Questions</h2>
          {topics.length === 0 ? (
            <p className="text-muted text-sm">No queries yet</p>
          ) : (
            <ul className="space-y-2">
              {topics.map((t, i) => (
                <li key={i} className="flex justify-between text-sm">
                  <span className="truncate mr-4">{t.question}</span>
                  <span className="text-muted flex-shrink-0">{t.count}x</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="app-card p-6 lg:col-span-2">
          <h2 className="text-sm font-semibold mb-4">Performance</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold">{overview.avg_response_time_ms}ms</p>
              <p className="text-xs text-muted">Avg Response Time</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{overview.cache_hit_count}</p>
              <p className="text-xs text-muted">Cache Hits</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{overview.conversations_total}</p>
              <p className="text-xs text-muted">Conversations</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
