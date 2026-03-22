import { useState, useEffect } from 'react';
import { Upload, Check, Info } from 'lucide-react';
import { api } from '../api/client';
import StrengthSlider from './StrengthSlider';

export default function StylePicker({ jobId, onStartGrade, onReferenceUploaded }) {
  const [tab, setTab] = useState('presets');
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [strength, setStrength] = useState(80);
  const [multiScene, setMultiScene] = useState(false);
  const [autoWb, setAutoWb] = useState(false);
  const [refUploading, setRefUploading] = useState(false);
  const [refUploaded, setRefUploaded] = useState(false);
  const [refError, setRefError] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    api.getPresets()
      .then((data) => setPresets(data.presets || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleRefUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setRefUploading(true);
    setRefError(null);
    try {
      await api.uploadReference(jobId, file);
      setRefUploaded(true);
      onReferenceUploaded?.();
    } catch (err) {
      setRefError(err.message);
    } finally {
      setRefUploading(false);
    }
  };

  const canGrade =
    (tab === 'presets' && selectedPreset) ||
    (tab === 'reference' && refUploaded);

  const handleGrade = () => {
    if (!canGrade) return;
    onStartGrade({
      job_id: jobId,
      mode: tab === 'presets' ? 'preset' : 'reference',
      preset_name: selectedPreset,
      strength: strength / 100,
      multi_scene: multiScene,
      auto_wb: autoWb,
      output_format: 'both',
    });
  };

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--color-surface)] rounded-xl">
        {['presets', 'reference'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
              tab === t
                ? 'bg-[var(--color-primary)] text-white'
                : 'text-[var(--color-text-secondary)] hover:text-white'
            }`}
          >
            {t === 'presets' ? 'Presets' : 'Custom Reference'}
          </button>
        ))}
      </div>

      {/* Presets Grid */}
      {tab === 'presets' && (
        <div className="space-y-4">
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-28 rounded-xl bg-[var(--color-surface)] animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {presets.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => setSelectedPreset(preset.name)}
                  className={`relative text-left p-3 rounded-xl border transition-all duration-200 ${
                    selectedPreset === preset.name
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 ring-1 ring-[var(--color-primary)]'
                      : 'border-white/10 bg-[var(--color-surface)] hover:border-white/20 hover:scale-[1.02]'
                  }`}
                >
                  {selectedPreset === preset.name && (
                    <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[var(--color-primary)] flex items-center justify-center">
                      <Check size={12} className="text-white" />
                    </div>
                  )}
                  {/* Color swatches */}
                  <div className="flex gap-1 mb-2">
                    {preset.preview_colors.map((color, i) => (
                      <div
                        key={i}
                        className="h-3 flex-1 rounded-sm"
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                  <p className="text-sm font-medium truncate">{preset.display_name}</p>
                  <p className="text-xs text-[var(--color-text-secondary)] truncate mt-0.5">
                    {preset.description}
                  </p>
                </button>
              ))}
            </div>
          )}

          {/* Live preview */}
          {selectedPreset && (
            <div className="rounded-xl overflow-hidden border border-white/10">
              <img
                src={api.getPresetPreview(selectedPreset)}
                alt={`${selectedPreset} preview`}
                className="w-full h-auto"
                loading="lazy"
              />
            </div>
          )}
        </div>
      )}

      {/* Custom Reference */}
      {tab === 'reference' && (
        <div className="space-y-4">
          {refUploaded ? (
            <div className="bg-[var(--color-surface)] rounded-xl p-4 border border-[var(--color-success)]/30 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--color-success)]/15 flex items-center justify-center">
                <Check className="text-[var(--color-success)]" size={20} />
              </div>
              <div>
                <p className="font-medium">Reference uploaded</p>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  Your video will be color-graded to match this reference
                </p>
              </div>
            </div>
          ) : (
            <label className={`
              block rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all
              ${refUploading
                ? 'border-[var(--color-primary)]/50 bg-[var(--color-primary)]/5'
                : 'border-white/15 bg-[var(--color-surface)] hover:border-white/30'}
            `}>
              <input
                type="file"
                accept=".mp4,.mov,.avi,.mkv,.webm"
                onChange={handleRefUpload}
                className="hidden"
                disabled={refUploading}
              />
              <Upload className="mx-auto text-[var(--color-text-secondary)] mb-2" size={24} />
              <p className="text-sm font-medium">
                {refUploading ? 'Uploading...' : 'Upload a reference video'}
              </p>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                MP4, MOV, AVI, MKV, WebM
              </p>
            </label>
          )}
          {refError && (
            <p className="text-sm text-[var(--color-error)]">{refError}</p>
          )}
        </div>
      )}

      {/* Strength Slider */}
      <StrengthSlider value={strength} onChange={setStrength} />

      {/* Advanced Options */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors"
        >
          {showAdvanced ? 'Hide' : 'Show'} advanced options
        </button>
        {showAdvanced && (
          <div className="mt-3 space-y-3 p-4 rounded-xl bg-[var(--color-surface)] border border-white/5">
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-2">
                <span className="text-sm">Multi-scene mode</span>
                <span className="text-xs text-[var(--color-text-secondary)]" title="Generates separate LUTs for different scenes">
                  <Info size={14} />
                </span>
              </div>
              <input
                type="checkbox"
                checked={multiScene}
                onChange={(e) => setMultiScene(e.target.checked)}
                className="w-4 h-4 accent-[var(--color-primary)]"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-2">
                <span className="text-sm">Auto white balance</span>
                <span className="text-xs text-[var(--color-text-secondary)]" title="Normalize white balance before grading">
                  <Info size={14} />
                </span>
              </div>
              <input
                type="checkbox"
                checked={autoWb}
                onChange={(e) => setAutoWb(e.target.checked)}
                className="w-4 h-4 accent-[var(--color-primary)]"
              />
            </label>
          </div>
        )}
      </div>

      {/* Grade Button */}
      <button
        onClick={handleGrade}
        disabled={!canGrade}
        className={`
          w-full py-3.5 rounded-xl font-semibold text-base transition-all duration-200
          ${canGrade
            ? 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white shadow-lg shadow-[var(--color-primary)]/25'
            : 'bg-white/5 text-white/30 cursor-not-allowed'}
        `}
      >
        Grade My Video
      </button>
    </div>
  );
}
