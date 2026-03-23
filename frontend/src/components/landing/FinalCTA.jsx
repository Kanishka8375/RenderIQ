import { ArrowRight } from 'lucide-react';

export default function FinalCTA({ onTryIt }) {
  return (
    <section className="py-16 sm:py-24">
      <div className="max-w-2xl mx-auto px-4 text-center">
        <h2 className="text-2xl sm:text-3xl font-bold mb-4">
          Ready to grade your first video?
        </h2>

        <button
          onClick={onTryIt}
          className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] font-semibold text-lg transition-all shadow-lg shadow-[var(--color-primary)]/25 hover:shadow-[var(--color-primary)]/40 mb-4"
        >
          Start Now — It's Free
          <ArrowRight size={20} />
        </button>

        <p className="text-sm text-[var(--color-text-secondary)]">
          No signup. No credit card. Just results.
        </p>
      </div>
    </section>
  );
}
