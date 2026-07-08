import { useEffect, useRef, useState, type MouseEvent } from 'react';
import toast from 'react-hot-toast';
import { chatAPI, documentsAPI, getErrorMessage } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { ChatMessage, ChatStreamEvent, Conversation, Document } from '../types';

export const ChatPage = () => {
  const { user } = useAuthStore();
  const canWrite = user?.role !== 'viewer';

  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeConversation, setActiveConversation] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState('');
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingSources, setStreamingSources] = useState<string[]>([]);
  const [followUps, setFollowUps] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    documentsAPI.list().then((r) => setDocuments(r.data)).catch(() => {});
    chatAPI.conversations().then((r) => setConversations(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking, streamingContent]);

  const loadMessages = async (convId: string) => {
    setActiveConversation(convId);
    setFollowUps([]);
    const res = await chatAPI.messages(convId);
    setMessages(res.data);
  };

  const startNewConversation = () => {
    setActiveConversation(null);
    setMessages([]);
    setFollowUps([]);
    setStreamingContent('');
    setStreamingSources([]);
  };

  const handleDeleteConversation = async (convId: string, e: MouseEvent) => {
    e.stopPropagation();
    if (!canWrite || !confirm('Delete this conversation?')) return;
    try {
      await chatAPI.deleteConversation(convId);
      if (activeConversation === convId) startNewConversation();
      const res = await chatAPI.conversations();
      setConversations(res.data);
      toast.success('Conversation deleted');
    } catch {
      toast.error('Failed to delete conversation');
    }
  };

  const handleStreamEvent = (event: ChatStreamEvent, convId: string | null) => {
    if (event.type === 'sources') {
      setStreamingSources(event.sources);
    } else if (event.type === 'token') {
      setStreamingContent((prev) => prev + event.content);
    } else if (event.type === 'done') {
      setFollowUps(event.follow_up_questions);
      const newConvId = event.conversation_id;
      if (!convId) {
        setActiveConversation(newConvId);
        chatAPI.conversations().then((r) => setConversations(r.data)).catch(() => {});
      }
      loadMessages(newConvId);
      setStreamingContent('');
      setStreamingSources([]);
    } else if (event.type === 'error') {
      toast.error(event.detail);
    }
  };

  const handleAsk = async (q?: string) => {
    const text = (q ?? question).trim();
    if (!text || isAsking) return;
    if (!canWrite) return toast.error('Viewers cannot send messages');

    setIsAsking(true);
    setQuestion('');
    setStreamingContent('');
    setStreamingSources([]);
    setFollowUps([]);

    const convId = activeConversation;

    try {
      await chatAPI.stream(
        { question: text, document_id: selectedDoc || undefined, conversation_id: convId || undefined },
        (event) => handleStreamEvent(event, convId),
      );
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Failed to get answer'));
    } finally {
      setIsAsking(false);
      setStreamingContent('');
      setStreamingSources([]);
    }
  };

  return (
    <div className="flex h-[calc(100vh-0px)] md:h-screen">
      <aside className="hidden lg:flex w-64 flex-col border-r border-[var(--color-border)] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-muted uppercase">Conversations</h3>
          {canWrite && (
            <button onClick={startNewConversation} className="text-xs text-indigo-400 hover:text-indigo-300">+ New</button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto space-y-1">
          {conversations.map((c) => (
            <div key={c.id} className="group flex items-center gap-1">
              <button
                onClick={() => loadMessages(c.id)}
                className={`flex-1 text-left px-3 py-2 rounded-lg text-sm truncate transition-all ${
                  activeConversation === c.id ? 'bg-indigo-600/20 text-indigo-400' : 'text-muted hover:bg-[var(--color-surface-hover)]'
                }`}
              >
                {c.title}
              </button>
              {canWrite && (
                <button
                  onClick={(e) => handleDeleteConversation(c.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-xs text-red-400 px-1"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-[var(--color-border)] flex gap-3 items-center">
          <select
            value={selectedDoc}
            onChange={(e) => setSelectedDoc(e.target.value)}
            className="flex-1 max-w-xs px-3 py-2 rounded-xl app-input text-sm"
          >
            <option value="">All documents</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.title || d.filename}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-4">
          {messages.length === 0 && !isAsking && (
            <div className="text-center py-16">
              <p className="text-muted">Ask anything about your documents</p>
              <p className="text-xs text-muted mt-2">Responses stream in real time with source citations</p>
              {canWrite && (
                <div className="flex flex-wrap gap-2 justify-center mt-4">
                  {['What are the key skills?', 'Summarize experience', 'List education'].map((q) => (
                    <button key={q} onClick={() => handleAsk(q)} className="px-3 py-1.5 rounded-full text-xs app-card hover:border-indigo-500/40">{q}</button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                m.role === 'user' ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20' : 'app-card'
              }`}>
                <p className="leading-relaxed whitespace-pre-wrap">{m.content}</p>
                {m.sources?.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[var(--color-border)] flex flex-wrap gap-1">
                    {m.sources.map((s, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded app-card text-muted">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isAsking && streamingContent && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm app-card">
                <p className="leading-relaxed whitespace-pre-wrap">{streamingContent}</p>
                {streamingSources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[var(--color-border)] flex flex-wrap gap-1">
                    {streamingSources.map((s, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded app-card text-muted">{s}</span>
                    ))}
                  </div>
                )}
                <span className="inline-block w-2 h-4 ml-0.5 bg-violet-400 animate-pulse align-middle" />
              </div>
            </div>
          )}

          {isAsking && !streamingContent && (
            <div className="flex gap-2 items-center text-muted text-sm">
              <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
              Retrieving context...
            </div>
          )}

          {followUps.length > 0 && !isAsking && canWrite && (
            <div className="flex flex-wrap gap-2 pt-2">
              {followUps.map((q) => (
                <button key={q} onClick={() => handleAsk(q)} className="px-3 py-1.5 rounded-full text-xs app-card hover:border-indigo-500/40">{q}</button>
              ))}
            </div>
          )}

          <div ref={endRef} />
        </div>

        {canWrite ? (
          <div className="p-4 border-t border-[var(--color-border)]">
            <form onSubmit={(e) => { e.preventDefault(); handleAsk(); }} className="flex gap-3">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question..."
                disabled={isAsking}
                className="flex-1 px-4 py-3 rounded-xl app-input text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
              <button type="submit" disabled={isAsking || !question.trim()} className="px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-semibold disabled:opacity-40">
                Send
              </button>
            </form>
          </div>
        ) : (
          <div className="p-4 border-t border-[var(--color-border)] text-center text-sm text-muted">
            Viewer accounts can read conversations but cannot send messages.
          </div>
        )}
      </div>
    </div>
  );
};
