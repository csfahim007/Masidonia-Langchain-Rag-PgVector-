import type { DocumentPreview } from '../types';

interface Props {
  preview: DocumentPreview | null;
  onClose: () => void;
}

export const DocumentPreviewModal = ({ preview, onClose }: Props) => {
  if (!preview) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="app-card w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between p-6 border-b border-[var(--color-border)]">
          <div>
            <h2 className="text-lg font-bold">{preview.title || preview.filename}</h2>
            <p className="text-sm text-muted mt-1">
              v{preview.version} · {preview.chunks_count} chunks · {preview.word_count} words · {preview.category}
            </p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-[var(--color-text)] text-xl leading-none px-2">×</button>
        </div>
        {preview.tags?.length > 0 && (
          <div className="px-6 pt-4 flex flex-wrap gap-1">
            {preview.tags.map((tag) => (
              <span key={tag} className="px-2 py-0.5 rounded-md text-xs app-card">{tag}</span>
            ))}
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-6">
          <pre className="text-sm whitespace-pre-wrap leading-relaxed font-sans text-[var(--color-text)]">{preview.preview}</pre>
        </div>
      </div>
    </div>
  );
};
