import { AlertCircle } from 'lucide-react';

export default function ProcessingView({ progress, currentStep, elapsed, estimated, error, onRetry }) {
  if (error) {
    return (
      <div className="text-center py-12 space-y-4">
        <div className="w-20 h-20 mx-auto rounded-full bg-[var(--color-error)]/10 flex items-center justify-center">
          <AlertCircle className="text-[var(--color-error)]" size={36} />
        </div>
        <p className="text-lg font-medium">Something went wrong</p>
        <p className="text-sm text-[var(--color-text-secondary)] max-w-md mx-auto">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-4 px-6 py-2.5 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] font-medium transition-colors"
          >
            Try Again
          </button>
        )}
      </div>
    );
  }

  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="text-center py-8 space-y-6">
      {/* Progress Ring */}
      <div className="relative w-44 h-44 mx-auto">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
          <circle
            cx="80" cy="80" r={radius}
            fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8"
          />
          <circle
            cx="80" cy="80" r={radius}
            fill="none" stroke="url(#progressGrad)" strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-500"
          />
          <defs>
            <linearGradient id="progressGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-primary)" />
              <stop offset="100%" stopColor="var(--color-secondary)" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-3xl font-bold">{progress}%</span>
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-base font-medium">{currentStep || 'Starting...'}</p>
        {estimated != null && estimated > 0 && (
          <p className="text-sm text-[var(--color-text-secondary)]">
            ~{Math.ceil(estimated)}s remaining
          </p>
        )}
      </div>

      <p className="text-xs text-[var(--color-text-secondary)]">
        Processing your video &mdash; don't close this tab
      </p>
    </div>
  );
}
