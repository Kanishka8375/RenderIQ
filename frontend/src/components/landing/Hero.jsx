import { useState, useEffect, useRef } from 'react';
import { ArrowRight, Play } from 'lucide-react';
import { api } from '../../api/client';

export default function Hero({ onTryIt, onSeeDemo }) {
  const [sliderPos, setSliderPos] = useState(50);
  const directionRef = useRef(1);

  // Auto-animate the slider
  useEffect(() => {
    const interval = setInterval(() => {
      setSliderPos((prev) => {
        if (prev >= 85) directionRef.current = -1;
        if (prev <= 15) directionRef.current = 1;
        return prev + directionRef.current * 0.5;
      });
    }, 50);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative py-16 sm:py-24 overflow-hidden">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--color-primary)]/5 via-transparent to-transparent pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-4 text-center">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight tracking-tight mb-6">
          Make Any Video Look{' '}
          <span className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-secondary)] bg-clip-text text-transparent">
            Cinematic
          </span>{' '}
          in Seconds
        </h1>

        <p className="text-lg sm:text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto mb-8">
          AI-powered color grading. Upload your footage, pick a style, download.
          No editing skills required.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-12">
          <button
            onClick={onTryIt}
            className="flex items-center gap-2 px-7 py-3.5 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] font-semibold text-base transition-all shadow-lg shadow-[var(--color-primary)]/25 hover:shadow-[var(--color-primary)]/40"
          >
            Try It Free — No Signup
            <ArrowRight size={18} />
          </button>
          <button
            onClick={onSeeDemo}
            className="flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/15 hover:border-white/30 hover:bg-white/5 font-medium text-[var(--color-text-secondary)] hover:text-white transition-all"
          >
            <Play size={16} />
            See Demo
          </button>
        </div>

        {/* Auto-animated before/after preview */}
        <div className="relative max-w-3xl mx-auto rounded-2xl overflow-hidden border border-white/10 shadow-2xl shadow-black/30">
          <img
            src={api.getPresetPreview('cinematic_warm')}
            alt="Before and after color grading comparison"
            className="w-full h-auto block"
          />
          {/* Animated slider line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white/80 transition-none"
            style={{ left: `${sliderPos}%` }}
          >
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-white shadow-lg flex items-center justify-center">
              <div className="flex gap-0.5">
                <div className="w-0.5 h-2.5 bg-gray-400 rounded-full" />
                <div className="w-0.5 h-2.5 bg-gray-400 rounded-full" />
              </div>
            </div>
          </div>
          <span className="absolute bottom-3 left-3 text-xs font-semibold bg-black/60 px-2 py-1 rounded-md backdrop-blur-sm">
            BEFORE
          </span>
          <span className="absolute bottom-3 right-3 text-xs font-semibold bg-black/60 px-2 py-1 rounded-md backdrop-blur-sm">
            AFTER
          </span>
        </div>
      </div>
    </section>
  );
}
