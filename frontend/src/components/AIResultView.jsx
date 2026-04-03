import { CheckCircle, Clock, Volume2, Sparkles, Film, User, Zap, ArrowLeftRight, Palette, Type, Image, FileText, Scissors, Music } from 'lucide-react';

const STEP_ICONS = {
  audio_clean: Volume2,
  enhancement: Sparkles,
  scene_detection: Film,
  face_tracking: User,
  smart_cuts: Scissors,
  music_sync: Music,
  speed_ramp: Zap,
  transitions: ArrowLeftRight,
  color_grading: Palette,
  auto_zoom: Film,
  reframe: Scissors,
  auto_captions: FileText,
  text_overlays: Type,
  thumbnail: Image,
};

const STEP_LABELS = {
  audio_clean: 'Audio cleaned',
  enhancement: 'Enhanced',
  scene_detection: 'Scenes detected',
  face_tracking: 'Faces tracked',
  smart_cuts: 'Smart cuts',
  music_sync: 'Music synced',
  speed_ramp: 'Speed ramp',
  transitions: 'Transitions',
  color_grading: 'Color graded',
  auto_zoom: 'Auto zoom',
  reframe: 'Reframed',
  auto_captions: 'Captions generated',
  text_overlays: 'Text overlays',
  thumbnail: 'Thumbnail generated',
};

export default function AIResultView({ aiInfo }) {
  if (!aiInfo || aiInfo.mode !== 'ai_edit') return null;

  const steps = aiInfo.steps_completed || [];
  const details = aiInfo.step_details || {};
  const processingTime = aiInfo.processing_time || 0;

  return (
    <div className="rounded-xl border border-[var(--color-primary)]/20 bg-gradient-to-br from-[var(--color-primary)]/5 to-[var(--color-secondary)]/5 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <CheckCircle size={16} className="text-green-400" />
          AI Edit Complete — {steps.length} steps applied
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
          <Clock size={12} />
          {(processingTime ?? 0).toFixed(1)}s
        </div>
      </div>

      {/* Steps list */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {steps.map((step) => {
          const Icon = STEP_ICONS[step] || CheckCircle;
          const label = STEP_LABELS[step] || step.replace(/_/g, ' ');
          const detail = details[step] || '';

          return (
            <div
              key={step}
              className="flex items-start gap-2 p-2 rounded-lg bg-[var(--color-surface)] border border-white/5"
            >
              <Icon size={14} className="text-[var(--color-primary)] mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium capitalize">{label}</p>
                {detail && (
                  <p className="text-[10px] text-[var(--color-text-secondary)] truncate">
                    {detail}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit plan tags */}
      {aiInfo.prompt && (
        <div className="pt-2 border-t border-white/5">
          <p className="text-xs text-[var(--color-text-secondary)] italic truncate">
            "{aiInfo.prompt}"
          </p>
        </div>
      )}
    </div>
  );
}
