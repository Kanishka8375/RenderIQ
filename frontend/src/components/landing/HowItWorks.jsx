import { Upload, Palette, Download } from 'lucide-react';

const steps = [
  {
    icon: Upload,
    title: 'Upload Your Video',
    description: 'Drop any video file — MP4, MOV, AVI, MKV, or WebM up to 500MB.',
  },
  {
    icon: Palette,
    title: 'Pick a Style',
    description: 'Choose from 10 cinematic presets or upload a reference video to match.',
  },
  {
    icon: Download,
    title: 'Download Your Video',
    description: 'Get your graded video as MP4 or export a .cube LUT for your editing software.',
  },
];

export default function HowItWorks() {
  return (
    <section className="py-16 sm:py-20">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-center mb-12">
          How It Works
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8">
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={i} className="relative text-center">
                {/* Connector line */}
                {i < steps.length - 1 && (
                  <div className="hidden sm:block absolute top-10 left-[calc(50%+2rem)] right-[calc(-50%+2rem)] h-px bg-gradient-to-r from-[var(--color-primary)]/40 to-[var(--color-primary)]/10" />
                )}

                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[var(--color-primary)]/10 border border-[var(--color-primary)]/20 flex items-center justify-center">
                  <Icon className="text-[var(--color-primary)]" size={28} />
                </div>

                <div className="text-xs font-mono text-[var(--color-primary)] mb-2">
                  STEP {i + 1}
                </div>

                <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
                <p className="text-sm text-[var(--color-text-secondary)] max-w-xs mx-auto">
                  {step.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
