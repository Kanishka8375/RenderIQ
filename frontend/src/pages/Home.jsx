import { useState, useCallback, useRef } from 'react';
import { Upload, Palette, Sparkles, Check, ArrowLeft, Brain, Music, Eye, User } from 'lucide-react';
import Hero from '../components/landing/Hero';
import HowItWorks from '../components/landing/HowItWorks';
import PresetShowcase from '../components/landing/PresetShowcase';
import DemoCompare from '../components/landing/DemoCompare';
import FinalCTA from '../components/landing/FinalCTA';
import UploadZone from '../components/UploadZone';
import StylePicker from '../components/StylePicker';
import ProcessingView from '../components/ProcessingView';
import PreviewCompare from '../components/PreviewCompare';
import DownloadPanel from '../components/DownloadPanel';
import FeedbackPopup from '../components/FeedbackPopup';
import { useUpload } from '../hooks/useUpload';
import { useJob } from '../hooks/useJob';
import { api } from '../api/client';

const STEPS = [
  { id: 1, label: 'Upload', icon: Upload },
  { id: 2, label: 'Style', icon: Palette },
  { id: 3, label: 'Result', icon: Sparkles },
];

export default function Home() {
  const [showTool, setShowTool] = useState(false);
  const [step, setStep] = useState(1);
  const [jobId, setJobId] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [hasGraded, setHasGraded] = useState(false);
  const upload = useUpload();
  const job = useJob(jobId);
  const toolRef = useRef(null);

  const scrollToTool = useCallback(() => {
    setShowTool(true);
    setTimeout(() => {
      toolRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  }, []);

  const scrollToDemo = useCallback(() => {
    document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleUpload = useCallback(async (file) => {
    const result = await upload.uploadRaw(file);
    if (result) {
      setJobId(result.job_id);
      setStep(2);
    }
  }, [upload]);

  const handleStartGrade = useCallback(async (config) => {
    try {
      await api.startGrade(config);
      setStep(3);
      setHasGraded(true);
      job.startPolling();
    } catch (err) {
      // Handle inline
    }
  }, [job]);

  const handleRegrade = useCallback(async (config) => {
    try {
      await api.regrade({ ...config, job_id: jobId });
      setStep(3);
      job.startPolling();
    } catch (err) {
      // Handle inline
    }
  }, [job, jobId]);

  const handleTryDifferentPreset = useCallback(() => {
    job.stopPolling();
    setStep(2);
  }, [job]);

  const handleReset = useCallback(() => {
    upload.reset();
    job.stopPolling();
    setStep(1);
    setJobId(null);
    setShowFeedback(false);
    setHasGraded(false);
  }, [upload, job]);

  const isProcessing = step === 3 && job.status === 'processing';
  const isCompleted = step === 3 && job.status === 'completed';
  const isFailed = step === 3 && job.status === 'failed';

  // Show feedback popup when download becomes available
  const shouldShowFeedback = isCompleted && !showFeedback;

  return (
    <div>
      {/* Landing sections */}
      <Hero onTryIt={scrollToTool} onSeeDemo={scrollToDemo} />
      <HowItWorks />
      <PresetShowcase />
      <DemoCompare />
      <FinalCTA onTryIt={scrollToTool} />

      {/* Tool section */}
      <section
        ref={toolRef}
        id="tool"
        className="py-16 sm:py-20 border-t border-white/5"
      >
        <div className="max-w-3xl mx-auto px-4">
          {!showTool ? (
            <div className="text-center">
              <h2 className="text-2xl sm:text-3xl font-bold mb-4">
                Start Color Grading
              </h2>
              <button
                onClick={() => setShowTool(true)}
                className="px-8 py-3.5 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] font-semibold transition-all shadow-lg shadow-[var(--color-primary)]/25"
              >
                Upload Your Video
              </button>
            </div>
          ) : (
            <>
              {/* Step Indicator */}
              <div className="flex items-center justify-center gap-2 mb-10">
                {STEPS.map((s, i) => {
                  const Icon = s.icon;
                  const isActive = step === s.id;
                  const isDone = step > s.id;
                  return (
                    <div key={s.id} className="flex items-center gap-2">
                      {i > 0 && (
                        <div className={`w-8 sm:w-12 h-px ${isDone ? 'bg-[var(--color-primary)]' : 'bg-white/10'}`} />
                      )}
                      <div className="flex items-center gap-2">
                        <div className={`
                          w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all
                          ${isDone ? 'bg-[var(--color-primary)] text-white' :
                            isActive ? 'bg-[var(--color-primary)] text-white ring-2 ring-[var(--color-primary)]/30' :
                            'bg-white/5 text-[var(--color-text-secondary)]'}
                        `}>
                          {isDone ? <Check size={14} /> : <Icon size={14} />}
                        </div>
                        <span className={`text-sm font-medium hidden sm:block ${
                          isActive ? 'text-white' : 'text-[var(--color-text-secondary)]'
                        }`}>
                          {s.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Step Content */}
              <div className="space-y-6">
                {step === 1 && (
                  <div>
                    <h2 className="text-2xl font-bold mb-2 text-center">Upload your video</h2>
                    <p className="text-[var(--color-text-secondary)] text-center mb-6">
                      Start by uploading the footage you want to color grade
                    </p>
                    <UploadZone
                      onUpload={handleUpload}
                      uploading={upload.uploading}
                      progress={upload.progress}
                      result={upload.uploadResult}
                      error={upload.error}
                      onReset={upload.reset}
                    />
                  </div>
                )}

                {step === 2 && (
                  <div>
                    <button
                      onClick={() => { setStep(1); }}
                      className="flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors mb-4"
                    >
                      <ArrowLeft size={16} /> Back to upload
                    </button>
                    <h2 className="text-2xl font-bold mb-2 text-center">Choose your style</h2>
                    <p className="text-[var(--color-text-secondary)] text-center mb-6">
                      Pick a preset or upload a reference video
                    </p>
                    {upload.uploadResult && (
                      <div className="mb-4">
                        <UploadZone
                          result={upload.uploadResult}
                          onReset={() => {
                            upload.reset();
                            setStep(1);
                            setJobId(null);
                          }}
                        />
                      </div>
                    )}
                    <StylePicker
                      jobId={jobId}
                      onStartGrade={hasGraded ? handleRegrade : handleStartGrade}
                      onReferenceUploaded={() => {}}
                    />
                  </div>
                )}

                {step === 3 && (
                  <div>
                    {!isProcessing && job.status !== 'queued' && (
                      <button
                        onClick={() => { job.stopPolling(); setStep(2); }}
                        className="flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors mb-4"
                      >
                        <ArrowLeft size={16} /> Back to style selection
                      </button>
                    )}
                    {(isProcessing || job.status === 'queued') && (
                      <>
                        <h2 className="text-2xl font-bold mb-2 text-center">Grading in progress</h2>
                        <ProcessingView
                          progress={job.progress}
                          currentStep={job.currentStep}
                          elapsed={job.elapsedSeconds}
                          estimated={job.estimatedRemaining}
                        />
                      </>
                    )}

                    {isFailed && (
                      <ProcessingView
                        error={job.currentStep || 'An unexpected error occurred'}
                        onRetry={() => setStep(2)}
                      />
                    )}

                    {isCompleted && (
                      <>
                        <h2 className="text-2xl font-bold mb-2 text-center">Your video is ready</h2>
                        <p className="text-[var(--color-text-secondary)] text-center mb-6">
                          Compare the before and after, then download your graded video
                        </p>
                        <div className="space-y-6">
                          {/* Smart Grade Analysis Card */}
                          {job.smartGradeInfo && (
                            <div className="rounded-xl border border-[var(--color-primary)]/20 bg-gradient-to-br from-[var(--color-primary)]/5 to-[var(--color-secondary)]/5 p-5 space-y-4">
                              <div className="flex items-center gap-2 text-sm font-medium">
                                <Brain size={16} className="text-[var(--color-primary)]" />
                                Smart Grade Analysis
                              </div>
                              <p className="text-sm text-[var(--color-text-secondary)]">
                                {job.smartGradeInfo.description}
                              </p>
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <div className="p-2.5 rounded-lg bg-[var(--color-surface)] border border-white/5">
                                  <div className="flex items-center gap-1.5 mb-1">
                                    <Music size={12} className="text-[var(--color-secondary)]" />
                                    <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">Audio Mood</span>
                                  </div>
                                  <p className="text-sm font-medium capitalize">{job.smartGradeInfo.audio_mood}</p>
                                </div>
                                <div className="p-2.5 rounded-lg bg-[var(--color-surface)] border border-white/5">
                                  <div className="flex items-center gap-1.5 mb-1">
                                    <Eye size={12} className="text-[var(--color-secondary)]" />
                                    <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">Scene</span>
                                  </div>
                                  <p className="text-sm font-medium capitalize">{job.smartGradeInfo.visual_scene?.replace(/_/g, ' ')}</p>
                                </div>
                                <div className="p-2.5 rounded-lg bg-[var(--color-surface)] border border-white/5">
                                  <div className="flex items-center gap-1.5 mb-1">
                                    <Palette size={12} className="text-[var(--color-secondary)]" />
                                    <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">Preset</span>
                                  </div>
                                  <p className="text-sm font-medium capitalize">{job.smartGradeInfo.preset_applied?.replace(/_/g, ' ')}</p>
                                </div>
                                <div className="p-2.5 rounded-lg bg-[var(--color-surface)] border border-white/5">
                                  <div className="flex items-center gap-1.5 mb-1">
                                    <User size={12} className="text-[var(--color-secondary)]" />
                                    <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">Faces</span>
                                  </div>
                                  <p className="text-sm font-medium">{job.smartGradeInfo.has_faces ? 'Detected' : 'None'}</p>
                                </div>
                              </div>
                              {job.smartGradeInfo.mood_tags?.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {job.smartGradeInfo.mood_tags.slice(0, 8).map((tag) => (
                                    <span
                                      key={tag}
                                      className="px-2 py-0.5 rounded-full text-[10px] bg-white/5 text-[var(--color-text-secondary)] border border-white/5"
                                    >
                                      {tag.replace(/_/g, ' ')}
                                    </span>
                                  ))}
                                </div>
                              )}
                              <button
                                onClick={handleTryDifferentPreset}
                                className="text-sm text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors"
                              >
                                Not happy? Try a different preset →
                              </button>
                            </div>
                          )}
                          <PreviewCompare comparisonUrl={job.result?.comparison_url} />
                          <DownloadPanel
                            jobId={jobId}
                            result={job.result}
                            onReset={handleReset}
                          />
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </section>

      {/* Feedback popup */}
      {shouldShowFeedback && (
        <FeedbackPopup
          jobId={jobId}
          onClose={() => setShowFeedback(true)}
        />
      )}
    </div>
  );
}
