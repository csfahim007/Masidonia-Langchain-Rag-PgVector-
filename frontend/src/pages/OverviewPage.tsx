import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { analyticsAPI } from '../services/api';
import type { AnalyticsOverview } from '../types';

export const OverviewPage = () => {
  const [stats, setStats] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.overview()
      .then((r) => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const cards = stats
    ? [
        { label: 'Documents', value: stats.documents_ready, sub: `${stats.documents_total} total` },
        { label: 'Queries', value: stats.queries_total, sub: `${stats.queries_this_week} this week` },
        { label: 'Conversations', value: stats.conversations_total, sub: 'active threads' },
        { label: 'Avg Response', value: `${stats.avg_response_time_ms}ms`, sub: `${stats.cache_hit_count} cache hits` },
      ]
    : [];

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Welcome back 👋</h1>
      <p className="text-muted mb-8">Your intelligent document platform is ready.</p>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="app-card p-5 h-24 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {cards.map((c) => (
            <div key={c.label} className="app-card p-5">
              <p className="text-xs text-muted uppercase tracking-wide">{c.label}</p>
              <p className="text-2xl font-bold mt-1">{c.value}</p>
              <p className="text-xs text-muted mt-1">{c.sub}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { to: '/documents', title: 'Upload Documents', desc: 'PDF, DOCX, TXT, Markdown — bulk supported', icon: '📄' },
          { to: '/chat', title: 'Ask AI', desc: 'Streaming RAG chat with citations', icon: '💬' },
          { to: '/search', title: 'Search', desc: 'Hybrid vector + keyword search', icon: '🔍' },
        ].map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="app-card p-6 hover:border-indigo-500/40 transition-all group"
          >
            <span className="text-3xl">{item.icon}</span>
            <h3 className="text-lg font-semibold mt-3 group-hover:text-indigo-400 transition-colors">{item.title}</h3>
            <p className="text-sm text-muted mt-1">{item.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
};
