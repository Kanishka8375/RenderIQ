import { Github, Twitter } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="py-10 border-t border-white/5">
      <div className="max-w-5xl mx-auto px-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-sm text-[var(--color-text-secondary)]">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors flex items-center gap-1.5">
              <Github size={16} />
              GitHub
            </a>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors flex items-center gap-1.5">
              <Twitter size={16} />
              Twitter
            </a>
          </div>

          <p className="text-sm text-[var(--color-text-secondary)]">
            Built by Kanishka &middot; &copy; 2026 RenderIQ
          </p>
        </div>
      </div>
    </footer>
  );
}
