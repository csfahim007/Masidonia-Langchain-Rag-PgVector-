import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { DocumentPreviewModal } from '../components/DocumentPreviewModal';
import { documentsAPI, foldersAPI, getErrorMessage } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { BulkUploadResult, Document, DocumentPreview } from '../types';

type UploadProgress = {
  filename: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
};

const ACCEPT = '.pdf,.docx,.txt,.md,.markdown';

export const DocumentsPage = () => {
  const { user } = useAuthStore();
  const canWrite = user?.role !== 'viewer';

  const [folders, setFolders] = useState<Awaited<ReturnType<typeof foldersAPI.list>>['data']>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [newFolderName, setNewFolderName] = useState('');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const loadFolders = async () => {
    const res = await foldersAPI.list();
    setFolders(res.data);
  };

  const loadDocuments = async (folderId?: string | null) => {
    const res = await documentsAPI.list(folderId || undefined);
    setDocuments(res.data);
  };

  const load = useCallback(async (folderId?: string | null) => {
    setIsLoading(true);
    try {
      await Promise.all([loadFolders(), loadDocuments(folderId)]);
    } catch {
      toast.error('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(selectedFolder);
  }, [selectedFolder, load]);

  const handleCreateFolder = async () => {
    if (!canWrite) return toast.error('Viewers cannot create folders');
    const name = newFolderName.trim();
    if (!name) return toast.error('Enter a folder name');
    try {
      await foldersAPI.create(name);
      setNewFolderName('');
      toast.success('Folder created');
      await loadFolders();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Failed to create folder'));
    }
  };

  const handleDeleteFolder = async (id: string) => {
    if (!canWrite) return;
    if (!confirm('Delete this folder? It must be empty.')) return;
    try {
      await foldersAPI.delete(id);
      if (selectedFolder === id) setSelectedFolder(null);
      toast.success('Folder deleted');
      await load(selectedFolder === id ? null : selectedFolder);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Failed to delete folder'));
    }
  };

  const addFiles = (incoming: FileList | File[]) => {
    const validExts = ['.pdf', '.docx', '.txt', '.md', '.markdown'];
    const list = Array.from(incoming).filter((f) =>
      validExts.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    if (list.length === 0) return toast.error('Unsupported file type');
    setFiles(list);
    setUploadProgress([]);
  };

  const handleUpload = async () => {
    if (!canWrite) return toast.error('Viewers cannot upload documents');
    if (files.length === 0) return toast.error('Select at least one file');

    setIsUploading(true);
    setUploadProgress(files.map((f) => ({ filename: f.name, status: 'pending' as const })));

    try {
      if (files.length === 1) {
        setUploadProgress([{ filename: files[0].name, status: 'uploading' }]);
        const res = await documentsAPI.upload(files[0], selectedFolder || undefined);
        setUploadProgress([{ filename: files[0].name, status: 'success', message: `${res.data.chunks_created} chunks` }]);
        toast.success(`${res.data.filename} processed`);
      } else {
        setUploadProgress(files.map((f) => ({ filename: f.name, status: 'uploading' })));
        const res = await documentsAPI.bulkUpload(files, selectedFolder || undefined);
        setUploadProgress(
          res.data.results.map((r: BulkUploadResult) => ({
            filename: r.filename,
            status: r.status === 'success' ? 'success' as const : 'error' as const,
            message: r.status === 'success' ? `${r.chunks_created} chunks` : r.error,
          }))
        );
        toast.success(`Uploaded ${res.data.succeeded}/${res.data.total} files`);
      }
      setFiles([]);
      await loadDocuments(selectedFolder);
      await loadFolders();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Upload failed'));
    } finally {
      setIsUploading(false);
    }
  };

  const handlePreview = async (id: string) => {
    try {
      const res = await documentsAPI.preview(id);
      setPreview(res.data);
    } catch {
      toast.error('Could not load preview');
    }
  };

  const handleDelete = async (id: string) => {
    if (!canWrite) return;
    if (!confirm('Delete this document?')) return;
    try {
      await documentsAPI.delete(id);
      toast.success('Document deleted');
      await load(selectedFolder);
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleMoveDocument = async (documentId: string, folderId: string) => {
    if (!canWrite) return;
    try {
      await foldersAPI.moveDocument(documentId, folderId || null);
      toast.success('Document moved');
      await load(selectedFolder);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Move failed'));
    }
  };

  const selectedFolderName = selectedFolder
    ? folders.find((f) => f.id === selectedFolder)?.name
    : 'All documents';

  return (
    <div className="flex h-full min-h-[calc(100vh-0px)]">
      <DocumentPreviewModal preview={preview} onClose={() => setPreview(null)} />

      <aside className="hidden md:flex w-56 flex-col border-r border-[var(--color-border)] p-4">
        <h3 className="text-xs font-semibold text-muted uppercase mb-3">Folders</h3>
        <button
          onClick={() => setSelectedFolder(null)}
          className={`text-left px-3 py-2 rounded-lg text-sm mb-1 transition-all ${
            selectedFolder === null ? 'bg-indigo-600/20 text-indigo-400' : 'text-muted hover:bg-[var(--color-surface-hover)]'
          }`}
        >
          All documents
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          {folders.map((folder) => (
            <div key={folder.id} className="flex items-center gap-1 group">
              <button
                onClick={() => setSelectedFolder(folder.id)}
                className={`flex-1 text-left px-3 py-2 rounded-lg text-sm truncate transition-all ${
                  selectedFolder === folder.id ? 'bg-indigo-600/20 text-indigo-400' : 'text-muted hover:bg-[var(--color-surface-hover)]'
                }`}
              >
                📁 {folder.name} ({folder.document_count})
              </button>
              {canWrite && (
                <button onClick={() => handleDeleteFolder(folder.id)} className="opacity-0 group-hover:opacity-100 text-xs text-red-400 px-1">×</button>
              )}
            </div>
          ))}
        </div>
        {canWrite && (
          <div className="mt-4 pt-4 border-t border-[var(--color-border)] space-y-2">
            <input
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="New folder..."
              className="w-full px-3 py-2 rounded-lg app-input text-sm"
              onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
            />
            <button onClick={handleCreateFolder} className="w-full px-3 py-2 rounded-lg text-sm app-card hover:bg-[var(--color-surface-hover)]">
              Create folder
            </button>
          </div>
        )}
      </aside>

      <div className="flex-1 p-6 lg:p-8 max-w-5xl mx-auto w-full">
        <h1 className="text-2xl font-bold mb-1">Documents</h1>
        <p className="text-sm text-muted mb-4">{selectedFolderName}</p>

        <select
          value={selectedFolder || ''}
          onChange={(e) => setSelectedFolder(e.target.value || null)}
          className="md:hidden w-full mb-6 px-3 py-2 rounded-xl app-input text-sm"
        >
          <option value="">All documents</option>
          {folders.map((f) => (
            <option key={f.id} value={f.id}>{f.name} ({f.document_count})</option>
          ))}
        </select>

        {canWrite && (
          <div className="app-card p-6 mb-8">
            <h2 className="text-sm font-semibold mb-4">Upload Documents</h2>
            <div
              className={`flex flex-col sm:flex-row gap-4 ${isDragging ? 'ring-2 ring-indigo-500/50 rounded-xl' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); }}
            >
              <label className="flex-1 flex flex-col items-center justify-center px-4 py-8 rounded-xl border-2 border-dashed border-[var(--color-border)] hover:border-indigo-500/50 cursor-pointer transition-all">
                <input type="file" multiple className="hidden" accept={ACCEPT} onChange={(e) => e.target.files && addFiles(e.target.files)} />
                <span className="text-sm text-muted text-center">
                  {files.length > 0 ? `${files.length} file(s) selected` : 'Drag & drop or click — PDF, DOCX, TXT, MD'}
                </span>
              </label>
              <button
                onClick={handleUpload}
                disabled={files.length === 0 || isUploading}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-semibold disabled:opacity-40 self-start"
              >
                {isUploading ? 'Processing...' : `Upload${files.length > 1 ? ` (${files.length})` : ''}`}
              </button>
            </div>
            {uploadProgress.length > 0 && (
              <div className="mt-4 space-y-2">
                {uploadProgress.map((item) => (
                  <div key={item.filename} className="flex items-center justify-between text-sm px-3 py-2 rounded-lg app-card">
                    <span className="truncate">{item.filename}</span>
                    <span className={
                      item.status === 'success' ? 'text-emerald-500' :
                      item.status === 'error' ? 'text-red-500' :
                      item.status === 'uploading' ? 'text-amber-500' : 'text-muted'
                    }>
                      {item.status === 'uploading' ? 'Processing...' : item.message || item.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isLoading ? (
          <p className="text-muted text-center py-8">Loading documents...</p>
        ) : documents.length === 0 ? (
          <p className="text-muted text-center py-8">No documents in this folder yet.</p>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.id} className="app-card p-4 flex items-center justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{doc.title || doc.filename}</p>
                  <p className="text-xs text-muted mt-1">
                    v{doc.version || 1} · {doc.chunks_count} chunks · {doc.category} · {(doc.file_size / 1024).toFixed(1)} KB
                  </p>
                  {doc.tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {doc.tags.map((tag) => (
                        <span key={tag} className="px-2 py-0.5 rounded-md text-xs app-card">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                  <button onClick={() => handlePreview(doc.id)} className="text-xs text-indigo-400 hover:text-indigo-300">Preview</button>
                  {canWrite && folders.length > 0 && (
                    <select
                      value={doc.folder_id || ''}
                      onChange={(e) => handleMoveDocument(doc.id, e.target.value)}
                      className="text-xs px-2 py-1 rounded-lg app-input"
                    >
                      <option value="">No folder</option>
                      {folders.map((f) => (
                        <option key={f.id} value={f.id}>{f.name}</option>
                      ))}
                    </select>
                  )}
                  <span className={`text-xs px-2 py-1 rounded-full ${doc.status === 'ready' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
                    {doc.status}
                  </span>
                  {canWrite && (
                    <button onClick={() => handleDelete(doc.id)} className="text-xs text-red-400 hover:text-red-300">Delete</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
