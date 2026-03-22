import { Download, FileDown, RotateCcw } from 'lucide-react';
import { api } from '../api/client';

export default function DownloadPanel({ jobId, result, onReset }) {
  if (!result) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {result.graded_video_url && (
          <a
            href={api.getDownloadUrl(jobId, 'video')}
            download
            className="flex items-center justify-center gap-2 py-3.5 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] font-semibold transition-colors shadow-lg shadow-[var(--color-primary)]/25"
          >
            <Download size={18} />
            Download Video
          </a>
        )}
        {result.lut_url && (
          <a
            href={api.getDownloadUrl(jobId, 'lut')}
            download
            className="flex flex-col items-center justify-center gap-1 py-3 rounded-xl border border-white/15 hover:border-white/30 hover:bg-white/5 font-medium transition-all"
          >
            <span className="flex items-center gap-2">
              <FileDown size={18} />
              Download LUT File
            </span>
            <span className="text-xs text-[var(--color-text-secondary)] font-normal">
              Use in DaVinci Resolve, Premiere, Final Cut
            </span>
          </a>
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
