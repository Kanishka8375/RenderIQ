import { useState, useCallback, useRef } from 'react';
import { Upload, Film, X } from 'lucide-react';

export default function UploadZone({ onUpload, uploading, progress, result, error, onReset }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }, [onUpload]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragOver(false), []);

  const handleClick = () => inputRef.current?.click();

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) onUpload(file);
  };

  // Show uploaded video info
  if (result) {
    return (
      <div className="bg-[var(--color-surface)] rounded-2xl p-6 border border-white/10">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[var(--color-success)]/15 flex items-center justify-center shrink-0">
            <Film className="text-[var(--color-success)]" size={24} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold truncate">{result.filename}</p>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {result.resolution} &middot; {result.fps}fps &middot; {result.duration}s &middot; {result.file_size_mb}MB
            </p>
          </div>
          <button
            onClick={onReset}
            className="text-[var(--color-text-secondary)] hover:text-white transition-colors p-2"
            aria-label="Remove video"
          >
            <X size={18} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={`
          relative rounded-2xl border-2 border-dashed p-12 sm:p-16 text-center cursor-pointer
          transition-all duration-200
          ${dragOver
            ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/5'
            : 'border-white/15 bg-[var(--color-surface)] hover:border-white/30 hover:bg-[var(--color-surface-hover)]'
          }
          ${uploading ? 'pointer-events-none' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.avi,.mkv,.webm"
          onChange={handleChange}
          className="hidden"
        />

        {uploading ? (
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-[var(--color-primary)]/15 flex items-center justify-center">
              <Upload className="text-[var(--color-primary)] animate-pulse" size={28} />
            </div>
            <p className="text-lg font-medium">Uploading... {progress}%</p>
            <div className="max-w-xs mx-auto h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-secondary)] transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center">
              <Upload className="text-[var(--color-primary)]" size={28} />
            </div>
            <div>
              <p className="text-lg font-medium">Drop your video here</p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                or click to browse &middot; MP4, MOV, AVI, MKV, WebM &middot; Max 500MB
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 px-4 py-2.5 rounded-xl bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 text-[var(--color-error)] text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
