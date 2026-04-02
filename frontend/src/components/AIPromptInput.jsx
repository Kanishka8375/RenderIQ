import { useState, useEffect } from 'react';
import { Sparkles, Send, Film, Zap, Smartphone, Sun, Moon, Video, Palette, Camera, Share2, Wand2 } from 'lucide-react';
import { api } from '../api/client';

const ICON_MAP = {
  film: Film,
  zap: Zap,
  smartphone: Smartphone,
  sun: Sun,
  moon: Moon,
  video: Video,
  palette: Palette,
  camera: Camera,
  share: Share2,
  sparkles: Wand2,
};

export default function AIPromptInput({ onSubmit, disabled }) {
  const [prompt, setPrompt] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    api.getAISuggestions()
      .then((data) => setSuggestions(data.suggestions || []))
      .catch(() => {
        // Use hardcoded fallbacks if API fails
        setSuggestions([
          { label: 'Full Cinematic Edit', icon: 'film', prompt: 'Make this a full cinematic edit with transitions and dramatic pacing' },
          { label: 'Fast Montage', icon: 'zap', prompt: 'Create a fast-paced montage with speed ramps and quick cuts' },
          { label: 'TikTok Ready', icon: 'smartphone', prompt: 'Make this vertical for TikTok with viral captions and fast pacing' },
          { label: 'Warm & Golden', icon: 'sun', prompt: 'Apply warm golden hour color grading with smooth transitions' },
          { label: 'Dark & Moody', icon: 'moon', prompt: 'Dark moody edit with slow pacing and dramatic zoom effects' },
          { label: 'Professional Edit', icon: 'video', prompt: 'Professional edit with auto enhancement, captions, and clean transitions' },
        ]);
      });
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim() && !disabled) {
      onSubmit(prompt.trim());
    }
  };

  const handleChipClick = (chipPrompt) => {
    setPrompt(chipPrompt);
    if (!disabled) {
      onSubmit(chipPrompt);
    }
  };

  return (
    <div className="space-y-4">
      {/* Prompt Input */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-center gap-2 p-2 rounded-xl border border-white/15 bg-[var(--color-surface)] focus-within:border-[var(--color-primary)]/50 transition-colors">
          <Sparkles size={18} className="text-[var(--color-primary)] ml-2 shrink-0" />
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe how you want your video edited..."
            disabled={disabled}
            className="flex-1 bg-transparent border-none outline-none text-sm placeholder:text-[var(--color-text-secondary)] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!prompt.trim() || disabled}
            className="px-4 py-2 rounded-lg bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shrink-0"
          >
            <Send size={14} />
            Edit
          </button>
        </div>
      </form>

      {/* Suggestion Chips */}
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-secondary)] font-medium uppercase tracking-wider">
          Quick suggestions
        </p>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((chip) => {
            const Icon = ICON_MAP[chip.icon] || Sparkles;
            return (
              <button
                key={chip.label}
                onClick={() => handleChipClick(chip.prompt)}
                disabled={disabled}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-white/10 hover:border-[var(--color-primary)]/40 hover:bg-[var(--color-primary)]/10 text-[var(--color-text-secondary)] hover:text-white transition-all disabled:opacity-40"
              >
                <Icon size={12} />
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
