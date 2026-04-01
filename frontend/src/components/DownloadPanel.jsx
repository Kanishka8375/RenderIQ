import { useState } from 'react';
import { Download, FileDown, RotateCcw, Loader2 } from 'lucide-react';
import { api } from '../api/client';

function useDownload() {
  const [downloading, setDownloading] = useState(null);

  const download = async (url, filename) => {
    setDownloading(filename);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(a.href);
      a.remove();
    } catch (err) {
      console.error('Download error:', err);
    } finally {
      setDownloading(null);
    }
  };

  return { download, downloading };
}

export default function DownloadPanel({ jobId, result, onReset }) {
  const { download, downloading } = useDownload();

  if (!result) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {result.graded_video_url && (
          <button
            onClick={() =>
              download(
                api.getDownloadUrl(jobId, 'video'),
                `renderiq_graded_${jobId.slice(0, 8)}.mp4`
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
                'renderiq_grade.cube'
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

      <button
        onClick={onReset}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-white/10 hover:border-white/20 hover:bg-white/5 text-[var(--color-text-secondary)] hover:text-white transition-all text-sm"
      >
        <RotateCcw size={16} />
        Grade Another Video
      </button>
    </div>
  );
}
