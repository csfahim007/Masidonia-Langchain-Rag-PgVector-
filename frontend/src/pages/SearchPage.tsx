import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { searchAPI } from '../services/api';
import type { SearchHistoryItem, SearchResult } from '../types';

export const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const loadHistory = () => {
    searchAPI.history().then((r) => setHistory(r.data)).catch(() => {});
  };

  useEffect(() => { loadHistory(); }, []);

  const handleSearch = async (q?: string) => {
    const text = (q ?? query).trim();
    if (!text) return;
    setQuery(text);
    setIsSearching(true);
    setSuggestions([]);
    try {
      const res = await searchAPI.query(text, mode);
      setResults(res.data);
      loadHistory();
    } catch {
      toast.error('Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleInputChange = async (value: string) => {
    setQuery(value);
    if (value.length >= 2) {
      try {
        const res = await searchAPI.autocomplete(value);
        setSuggestions(res.data.suggestions || []);
      } catch {
        setSuggestions([]);
      }
    } else {
      setSuggestions([]);
    }
  };

  const handleClearHistory = async () => {
    try {
      await searchAPI.clearHistory();
      setHistory([]);
      toast.success('History cleared');
    } catch {
      toast.error('Failed to clear history');
    }
  };

  return (
    <div className="flex h-full min-h-[calc(100vh-0px)]">
      <aside className="hidden lg:flex w-56 flex-col border-r border-[var(--color-border)] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-muted uppercase">Recent</h3>
          {history.length > 0 && (
            <button onClick={handleClearHistory} className="text-xs text-red-400 hover:text-red-300">Clear</button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto space-y-1">
          {history.length === 0 ? (
            <p className="text-xs text-muted">No search history yet</p>
          ) : (
            history.map((h) => (
              <button
                key={h.id}
                onClick={() => { setMode(h.mode); handleSearch(h.query); }}
                className="w-full text-left px-3 py-2 rounded-lg text-sm text-muted hover:bg-[var(--color-surface-hover)] truncate"
              >
                {h.query}
                <span className="block text-[10px] text-muted">{h.results_count} results · {h.mode}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      <div className="flex-1 p-6 lg:p-8 max-w-4xl mx-auto w-full">
        <h1 className="text-2xl font-bold mb-6">Search</h1>

        <div className="app-card p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <input
                value={query}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search documents..."
                className="w-full px-4 py-3 rounded-xl app-input text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
              {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 rounded-xl border border-[var(--color-border)] app-card z-10 overflow-hidden">
                  {suggestions.map((s) => (
                    <button key={s} onClick={() => { setQuery(s); handleSearch(s); setSuggestions([]); }} className="w-full text-left px-4 py-2 text-sm hover:bg-[var(--color-surface-hover)]">{s}</button>
                  ))}
                </div>
              )}
            </div>
            <select value={mode} onChange={(e) => setMode(e.target.value)} className="px-3 py-3 rounded-xl app-input text-sm">
              <option value="hybrid">Hybrid</option>
              <option value="vector">Semantic</option>
              <option value="keyword">Keyword</option>
            </select>
            <button onClick={() => handleSearch()} disabled={isSearching} className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-semibold disabled:opacity-40">
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {results.length === 0 && !isSearching && (
            <p className="text-muted text-center py-8">Enter a query to search across your documents</p>
          )}
          {results.map((r) => (
            <div key={r.chunk_id} className="app-card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-indigo-400">{r.filename}</span>
                <span className="text-xs text-muted">Score: {r.score} · Chunk {r.chunk_index + 1}</span>
              </div>
              <p className="text-sm leading-relaxed">{r.snippet}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
