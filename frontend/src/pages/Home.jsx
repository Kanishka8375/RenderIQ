import { useState, useCallback } from 'react';
import { Upload, Palette, Sparkles, Check } from 'lucide-react';
import UploadZone from '../components/UploadZone';
import StylePicker from '../components/StylePicker';
import ProcessingView from '../components/ProcessingView';
import PreviewCompare from '../components/PreviewCompare';
import DownloadPanel from '../components/DownloadPanel';
import { useUpload } from '../hooks/useUpload';
import { useJob } from '../hooks/useJob';
import { api } from '../api/client';

const STEPS = [
  { id: 1, label: 'Upload', icon: Upload },
  { id: 2, label: 'Style', icon: Palette },
  { id: 3, label: 'Result', icon: Sparkles },
];

export default function Home() {
  const [step, setStep] = useState(1);
  const [jobId, setJobId] = useState(null);
  const upload = useUpload();
  const job = useJob(jobId);

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
      job.startPolling();
    } catch (err) {
      // Handle inline
    }
  }, [job]);

  const handleReset = useCallback(() => {
    upload.reset();
    job.stopPolling();
    setStep(1);
    setJobId(null);
  }, [upload, job]);

  const isProcessing = step === 3 && job.status === 'processing';
  const isCompleted = step === 3 && job.status === 'completed';
  const isFailed = step === 3 && job.status === 'failed';

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
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
            <h2 className="text-2xl font-bold mb-2 text-center">Choose your style</h2>
            <p className="text-[var(--color-text-secondary)] text-center mb-6">
              Pick a preset or upload a reference video
            </p>
            {/* Show uploaded video info */}
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
              onStartGrade={handleStartGrade}
              onReferenceUploaded={() => {}}
            />
          </div>
        )}

        {step === 3 && (
          <div>
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
                  <PreviewCompare
                    comparisonUrl={job.result?.comparison_url}
                  />
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
    </div>
  );
}
