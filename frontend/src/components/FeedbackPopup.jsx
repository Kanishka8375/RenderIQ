import { useState } from 'react';
import { X } from 'lucide-react';
import { api } from '../api/client';

export default function FeedbackPopup({ jobId, onClose }) {
  const [rating, setRating] = useState(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (r) => {
    setRating(r);
    if (r === 'bad') return; // Show comment input first
    try {
      await api.submitFeedback(jobId, r);
    } catch {
      // Silently fail — don't block the user
    }
    setSubmitted(true);
    setTimeout(onClose, 1500);
  };

  const handleBadSubmit = async () => {
    try {
      await api.submitFeedback(jobId, 'bad', comment);
    } catch {
      // Silently fail
    }
    setSubmitted(true);
    setTimeout(onClose, 1500);
  };

  if (submitted) {
    return (
      <div className="fixed bottom-6 right-6 z-50 bg-[var(--color-surface)] border border-white/10 rounded-xl p-4 shadow-2xl shadow-black/40 w-72">
        <p className="text-sm text-center">Thanks for your feedback!</p>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 bg-[var(--color-surface)] border border-white/10 rounded-xl p-4 shadow-2xl shadow-black/40 w-72">
      <button
        onClick={onClose}
        className="absolute top-2 right-2 text-[var(--color-text-secondary)] hover:text-white"
      >
        <X size={14} />
      </button>

      {rating !== 'bad' ? (
        <div className="space-y-3">
          <p className="text-sm font-medium">How's the result?</p>
          <div className="flex gap-2">
            <button
              onClick={() => handleSubmit('great')}
              className="flex-1 py-2 rounded-lg bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 hover:bg-[var(--color-success)]/20 text-sm transition-colors"
            >
              Great
            </button>
            <button
              onClick={() => handleSubmit('ok')}
              className="flex-1 py-2 rounded-lg bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 hover:bg-[var(--color-warning)]/20 text-sm transition-colors"
            >
              OK
            </button>
            <button
              onClick={() => setRating('bad')}
              className="flex-1 py-2 rounded-lg bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 hover:bg-[var(--color-error)]/20 text-sm transition-colors"
            >
              Bad
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm font-medium">What went wrong?</p>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Tell us what happened..."
            className="w-full h-20 px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-white/10 text-sm resize-none focus:outline-none focus:border-[var(--color-primary)]"
          />
          <button
            onClick={handleBadSubmit}
            className="w-full py-2 rounded-lg bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-sm font-medium transition-colors"
          >
            Submit
          </button>
        </div>
      )}
    </div>
  );
}
