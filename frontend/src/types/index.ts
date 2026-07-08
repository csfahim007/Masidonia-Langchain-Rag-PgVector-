export interface User {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
  created_at?: string;
  is_active?: boolean;
}

export interface Document {
  id: string;
  filename: string;
  title?: string;
  content_type: string;
  file_size: number;
  status: string;
  category?: string;
  tags: string[];
  chunks_count: number;
  version?: number;
  folder_id?: string | null;
  uploaded_at: string;
}

export interface DocumentPreview {
  document_id: string;
  filename: string;
  title?: string;
  category?: string;
  tags: string[];
  version: number;
  chunks_count: number;
  word_count: number;
  preview: string;
  uploaded_at: string;
}

export interface SearchHistoryItem {
  id: string;
  query: string;
  mode: string;
  results_count: number;
  created_at: string;
}

export interface PlatformOverview {
  users_total: number;
  documents_total: number;
  queries_total: number;
  conversations_total: number;
  active_users_week: number;
}

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  document_count: number;
  created_at: string;
}

export interface BulkUploadResult {
  filename: string;
  status: 'success' | 'error';
  document_id?: string;
  chunks_created?: number;
  category?: string;
  error?: string;
}

export interface BulkUploadResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: BulkUploadResult[];
}

export interface UploadResponse {
  message: string;
  document_id: string;
  filename: string;
  chunks_created: number;
  category?: string;
  tags?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  conversation_id: string;
  follow_up_questions: string[];
}

export type ChatStreamEvent =
  | { type: 'token'; content: string }
  | { type: 'sources'; sources: string[] }
  | { type: 'done'; conversation_id: string; follow_up_questions: string[] }
  | { type: 'error'; detail: string };

export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  sources: string[];
  created_at: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  snippet: string;
  score: number;
  chunk_index: number;
}

export interface AnalyticsOverview {
  documents_total: number;
  documents_ready: number;
  queries_total: number;
  queries_this_week: number;
  conversations_total: number;
  avg_response_time_ms: number;
  tokens_used_total: number;
  cache_hit_count: number;
}

export interface QueryTrend {
  date: string;
  queries: number;
}
