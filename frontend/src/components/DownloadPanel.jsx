import { useState } from 'react';
import { Download, FileDown, RotateCcw, Loader2, FileText, Image } from 'lucide-react';
import { api } from '../api/client';

function useDownload() {
  const [downloading, setDownloading] = useState(null);

  const download = async (url, filename, headers = {}) => {
    setDownloading(filename);
    let blobUrl = null;
    try {
      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error('Download error:', err);
    } finally {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      setDownloading(null);
    }
  };

  return { download, downloading };
}

export default function DownloadPanel({ jobId, result, onReset, aiInfo }) {
  const { download, downloading } = useDownload();

  if (!result) return null;

  const isAIEdit = aiInfo?.mode === 'ai_edit';
  const hasSrt = isAIEdit && aiInfo?.steps_completed?.includes('auto_captions');
  const hasThumbnail = isAIEdit && aiInfo?.steps_completed?.includes('thumbnail');

  return (
    <div className="space-y-4">
      {/* Primary downloads */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {result.graded_video_url && (
          <button
            onClick={() =>
              download(
                api.getDownloadUrl(jobId, 'video'),
                `renderiq_graded_${jobId.slice(0, 8)}.mp4`,
                api.getDownloadHeaders(jobId)
              )
            }
            disabled={!!downloading}
            className="flex items-center justify-center gap-2 py-3.5 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] font-semibold transition-colors shadow-lg shadow-[var(--color-primary)]/25 disabled:opacity-60"
          >
            {downloading?.endsWith('.mp4') ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Download size={18} />
            )}
            Download Video
          </button>
        )}
        {result.lut_url && (
          <button
            onClick={() =>
              download(
                api.getDownloadUrl(jobId, 'lut'),
                'renderiq_grade.cube',
                api.getDownloadHeaders(jobId)
              )
            }
            disabled={!!downloading}
            className="flex flex-col items-center justify-center gap-1 py-3 rounded-xl border border-white/15 hover:border-white/30 hover:bg-white/5 font-medium transition-all disabled:opacity-60"
          >
            <span className="flex items-center gap-2">
              {downloading?.endsWith('.cube') ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <FileDown size={18} />
              )}
              Download LUT File
            </span>
            <span className="text-xs text-[var(--color-text-secondary)] font-normal">
              Use in DaVinci Resolve, Premiere, Final Cut
            </span>
          </button>
        )}
      </div>

      {/* AI Edit extra downloads */}
      {(hasSrt || hasThumbnail) && (
        <div className="grid grid-cols-2 gap-2">
          {hasSrt && (
            <button
              onClick={() =>
                download(
                  api.getDownloadUrl(jobId, 'srt'),
                  'renderiq_captions.srt',
                  api.getDownloadHeaders(jobId)
                )
              }
              disabled={!!downloading}
              className="flex items-center justify-center gap-2 py-2.5 rounded-lg border border-white/10 hover:border-white/20 hover:bg-white/5 text-sm transition-all disabled:opacity-60"
            >
              <FileText size={14} />
              Download SRT
            </button>
          )}
          {hasThumbnail && (
            <button
              onClick={() =>
                download(
                  api.getDownloadUrl(jobId, 'thumbnail'),
                  'renderiq_thumbnail.jpg',
                  api.getDownloadHeaders(jobId)
                )
              }
              disabled={!!downloading}
              className="flex items-center justify-center gap-2 py-2.5 rounded-lg border border-white/10 hover:border-white/20 hover:bg-white/5 text-sm transition-all disabled:opacity-60"
            >
              <Image size={14} />
              Download Thumbnail
            </button>
          )}
        </div>
      )}

      <button
        onClick={onReset}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-white/10 hover:border-white/20 hover:bg-white/5 text-[var(--color-text-secondary)] hover:text-white transition-all text-sm"
      >
        <RotateCcw size={16} />
        {isAIEdit ? 'Edit Another Video' : 'Grade Another Video'}
      </button>
    </div>
  );
}
