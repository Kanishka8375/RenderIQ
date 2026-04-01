import { useState, useEffect } from 'react';
import { Upload, Check, Info, Wand2, Brain, Music, Eye, User, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../api/client';
import StrengthSlider from './StrengthSlider';

export default function StylePicker({ jobId, onStartGrade, onReferenceUploaded }) {
  const [tab, setTab] = useState('smart');
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [strength, setStrength] = useState(80);
  const [useAutoStrength, setUseAutoStrength] = useState(true);
  const [multiScene, setMultiScene] = useState(false);
  const [autoWb, setAutoWb] = useState(false);
  const [outputFormat, setOutputFormat] = useState('both');
  const [refUploading, setRefUploading] = useState(false);
  const [refUploaded, setRefUploaded] = useState(false);
  const [refError, setRefError] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [recommending, setRecommending] = useState(false);
  const [recommendations, setRecommendations] = useState(null);
  const [recommendError, setRecommendError] = useState(null);

  useEffect(() => {
    api.getPresets()
      .then((data) => setPresets(data.presets || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleAutoSuggest = async () => {
    setRecommending(true);
    setRecommendError(null);
    try {
      const data = await api.getRecommendations(jobId);
      setRecommendations(data);
      if (data.recommendations?.length > 0) {
        setSelectedPreset(data.recommendations[0].name);
      }
    } catch (err) {
      setRecommendError(err.message);
    } finally {
      setRecommending(false);
    }
  };

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
    tab === 'smart' ||
    (tab === 'presets' && selectedPreset) ||
    (tab === 'reference' && refUploaded);

  const handleGrade = () => {
    if (!canGrade) return;
    if (tab === 'smart') {
      onStartGrade({
        job_id: jobId,
        mode: 'smart',
        strength: strength / 100,
        use_auto_strength: useAutoStrength,
        output_format: outputFormat,
      });
      return;
    }
    onStartGrade({
      job_id: jobId,
      mode: tab === 'presets' ? 'preset' : 'reference',
      preset_name: selectedPreset,
      strength: strength / 100,
      multi_scene: multiScene,
      auto_wb: autoWb,
      output_format: outputFormat,
    });
  };

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--color-surface)] rounded-xl">
        {[
          { key: 'smart', label: 'Smart Grade', icon: Brain },
          { key: 'presets', label: 'Presets', icon: Wand2 },
          { key: 'reference', label: 'Reference', icon: Upload },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5 ${
              tab === key
                ? 'bg-[var(--color-primary)] text-white'
                : 'text-[var(--color-text-secondary)] hover:text-white'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Smart Grade Tab */}
      {tab === 'smart' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-[var(--color-primary)]/20 bg-gradient-to-br from-[var(--color-primary)]/5 to-[var(--color-secondary)]/5 p-6 space-y-5">
            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-[var(--color-primary)]/15 flex items-center justify-center">
                <Brain size={24} className="text-[var(--color-primary)]" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Smart Auto Grade</h3>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  AI analyzes your video's mood — visuals, music, pacing — then applies the perfect color grade automatically.
                </p>
              </div>
            </div>

            {/* Feature list */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div className="flex items-center gap-2.5 text-[var(--color-text-secondary)]">
                <Music size={14} className="text-[var(--color-secondary)] shrink-0" />
                <span>Analyzes music tempo &amp; energy</span>
              </div>
              <div className="flex items-center gap-2.5 text-[var(--color-text-secondary)]">
                <Eye size={14} className="text-[var(--color-secondary)] shrink-0" />
                <span>Detects scene type &amp; lighting</span>
              </div>
              <div className="flex items-center gap-2.5 text-[var(--color-text-secondary)]">
                <User size={14} className="text-[var(--color-secondary)] shrink-0" />
                <span>Protects skin tones (face detection)</span>
              </div>
              <div className="flex items-center gap-2.5 text-[var(--color-text-secondary)]">
                <Check size={14} className="text-[var(--color-success)] shrink-0" />
                <span>Matches grade to content mood</span>
              </div>
            </div>

            {/* Info callout */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-[var(--color-surface)] border border-white/5">
              <Info size={14} className="text-[var(--color-text-secondary)] shrink-0 mt-0.5" />
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                No configuration needed — just click <strong className="text-white">Smart Grade My Video</strong> and let the AI do the work.
                You can still adjust the strength slider below to fine-tune the result.
              </p>
            </div>

            {/* Auto strength toggle */}
            <label className="flex items-center justify-between cursor-pointer p-3 rounded-lg bg-[var(--color-surface)] border border-white/5">
              <div>
                <span className="text-sm font-medium">Auto strength</span>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  {useAutoStrength
                    ? 'AI picks the optimal intensity based on mood analysis'
                    : 'Using manual strength from slider below'}
                </p>
              </div>
              <input
                type="checkbox"
                checked={useAutoStrength}
                onChange={(e) => setUseAutoStrength(e.target.checked)}
                className="w-4 h-4 accent-[var(--color-primary)]"
              />
            </label>
          </div>
        </div>
      )}

      {/* Presets Grid */}
      {tab === 'presets' && (
        <div className="space-y-4">
          {/* Auto Suggest Button */}
          <button
            onClick={handleAutoSuggest}
            disabled={recommending}
            className={`
              w-full py-3 rounded-xl font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2
              ${recommending
                ? 'bg-[var(--color-secondary)]/20 text-[var(--color-secondary)] cursor-wait'
                : 'bg-gradient-to-r from-[var(--color-primary)]/15 to-[var(--color-secondary)]/15 border border-[var(--color-primary)]/30 text-white hover:border-[var(--color-primary)]/60 hover:from-[var(--color-primary)]/25 hover:to-[var(--color-secondary)]/25'
              }
            `}
          >
            <Wand2 size={16} className={recommending ? 'animate-spin' : ''} />
            {recommending ? 'Analyzing your video...' : 'Auto Suggest Best Style'}
          </button>

          {recommendError && (
            <p className="text-sm text-[var(--color-error)] text-center">{recommendError}</p>
          )}

          {/* Recommendations */}
          {recommendations && !recommending && (
            <div className="rounded-xl border border-[var(--color-primary)]/20 bg-[var(--color-primary)]/5 p-4 space-y-3">
              <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">
                Recommended for your video
              </p>
              <div className="space-y-2">
                {recommendations.recommendations.map((rec, i) => (
                  <button
                    key={rec.name}
                    onClick={() => setSelectedPreset(rec.name)}
                    className={`w-full text-left p-3 rounded-lg border transition-all duration-200 flex items-center gap-3 ${
                      selectedPreset === rec.name
                        ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                        : 'border-white/10 bg-[var(--color-surface)] hover:border-white/20'
                    }`}
                  >
                    <div className={`
                      w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0
                      ${i === 0 ? 'bg-[var(--color-primary)] text-white' : 'bg-white/10 text-[var(--color-text-secondary)]'}
                    `}>
                      {i + 1}
                    </div>
                    <div className="flex gap-1 shrink-0">
                      {rec.preview_colors.map((color, ci) => (
                        <div
                          key={ci}
                          className="w-3 h-3 rounded-sm"
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{rec.display_name}</p>
                      <p className="text-xs text-[var(--color-text-secondary)] truncate">{rec.reason}</p>
                    </div>
                    {selectedPreset === rec.name && (
                      <Check size={16} className="text-[var(--color-primary)] shrink-0" />
                    )}
                  </button>
                ))}
              </div>
              {recommendations.analysis && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {recommendations.analysis.tags.slice(0, 5).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-full text-[10px] bg-white/5 text-[var(--color-text-secondary)] border border-white/5"
                    >
                      {tag.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-28 rounded-xl bg-[var(--color-surface)] animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {presets.map((preset) => {
                const rec = recommendations?.recommendations?.find((r) => r.name === preset.name);
                return (
                  <button
                    key={preset.name}
                    onClick={() => setSelectedPreset(preset.name)}
                    className={`relative text-left p-3 rounded-xl border transition-all duration-200 ${
                      selectedPreset === preset.name
                        ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 ring-1 ring-[var(--color-primary)]'
                        : rec
                          ? 'border-[var(--color-primary)]/30 bg-[var(--color-surface)] hover:border-[var(--color-primary)]/50 hover:scale-[1.02]'
                          : 'border-white/10 bg-[var(--color-surface)] hover:border-white/20 hover:scale-[1.02]'
                    }`}
                  >
                    {selectedPreset === preset.name && (
                      <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[var(--color-primary)] flex items-center justify-center">
                        <Check size={12} className="text-white" />
                      </div>
                    )}
                    {rec && selectedPreset !== preset.name && (
                      <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md bg-[var(--color-primary)]/20 text-[var(--color-primary)] text-[10px] font-bold">
                        TOP {recommendations.recommendations.indexOf(rec) + 1}
                      </div>
                    )}
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
                );
              })}
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

      {/* Output Format */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Output Format</label>
        <div className="flex gap-2">
          {[
            { key: 'video', label: 'Video (MP4)' },
            { key: 'lut', label: 'LUT File (.cube)' },
            { key: 'both', label: 'Both' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setOutputFormat(key)}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                outputFormat === key
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-white border border-white/5'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Options */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors flex items-center gap-1"
        >
          {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {showAdvanced ? 'Hide' : 'Show'} advanced options
        </button>
        {showAdvanced && (
          <div className="mt-3 space-y-3 p-4 rounded-xl bg-[var(--color-surface)] border border-white/5">
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
        {tab === 'smart' ? 'Smart Grade My Video' : 'Grade My Video'}
      </button>
    </div>
  );
}
