import { useState, useEffect } from 'react';
import { api } from '../../api/client';

export default function PresetShowcase() {
  const [presets, setPresets] = useState([]);
  const [hovered, setHovered] = useState(null);

  useEffect(() => {
    api.getPresets()
      .then((data) => setPresets(data.presets || []))
      .catch(() => {});
  }, []);

  return (
    <section className="py-16 sm:py-20 bg-[var(--color-surface)]/50">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-center mb-3">
          10 Professional Color Grades
        </h2>
        <p className="text-[var(--color-text-secondary)] text-center mb-10 max-w-lg mx-auto">
          From cinematic warmth to anime vibrance — each preset is crafted to transform your footage instantly.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {presets.map((preset) => (
            <div
              key={preset.name}
              className="group relative rounded-xl border border-white/10 bg-[var(--color-surface)] overflow-hidden transition-all duration-200 hover:border-white/20 hover:scale-[1.03]"
              onMouseEnter={() => setHovered(preset.name)}
              onMouseLeave={() => setHovered(null)}
            >
              {/* Preview image */}
              <div className="aspect-video bg-[var(--color-bg)] overflow-hidden">
                <img
                  src={api.getPresetPreview(preset.name)}
                  alt={preset.display_name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </div>

              <div className="p-3">
                {/* Color swatches */}
                <div className="flex gap-1 mb-2">
                  {preset.preview_colors.map((color, i) => (
                    <div
                      key={i}
                      className="h-2 flex-1 rounded-sm"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
                <p className="text-sm font-medium truncate">{preset.display_name}</p>
                <p className="text-xs text-[var(--color-text-secondary)] truncate mt-0.5">
                  {preset.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-8">
          Or upload any reference video to match its color style
        </p>
      </div>
    </section>
  );
}
