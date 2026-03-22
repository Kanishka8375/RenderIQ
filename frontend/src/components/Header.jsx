import { Github } from 'lucide-react';

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--color-bg)]/95 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-white">Render</span>
            <span className="text-[var(--color-primary)]">IQ</span>
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-[var(--color-primary)]/15 text-[var(--color-primary)] border border-[var(--color-primary)]/30">
            Free Beta
          </span>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--color-text-secondary)] hover:text-white transition-colors"
            aria-label="GitHub"
          >
            <Github size={20} />
          </a>
        </div>
      </div>
      <div className="h-px bg-gradient-to-r from-[var(--color-primary)] via-[var(--color-secondary)] to-transparent" />
    </header>
  );
}
