import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '../../api/client';

export default function DemoCompare() {
  const [sliderPos, setSliderPos] = useState(50);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef(null);

  const getPosition = useCallback((clientX) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return 50;
    return Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
  }, []);

  const handleStart = useCallback((clientX) => {
    setDragging(true);
    setSliderPos(getPosition(clientX));
  }, [getPosition]);

  const handleMove = useCallback((clientX) => {
    if (!dragging) return;
    setSliderPos(getPosition(clientX));
  }, [dragging, getPosition]);

  const handleEnd = useCallback(() => setDragging(false), []);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e) => handleMove(e.touches ? e.touches[0].clientX : e.clientX);
    const onEnd = () => handleEnd();
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchmove', onMove, { passive: true });
    window.addEventListener('touchend', onEnd);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onEnd);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
    };
  }, [dragging, handleMove, handleEnd]);

  return (
    <section id="demo" className="py-16 sm:py-20">
      <div className="max-w-4xl mx-auto px-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-center mb-3">
          See the Difference
        </h2>
        <p className="text-[var(--color-text-secondary)] text-center mb-8 max-w-lg mx-auto">
          Drag the slider to compare. This is what AI color grading looks like.
        </p>

        <div
          ref={containerRef}
          className="relative rounded-2xl overflow-hidden cursor-col-resize select-none border border-white/10 shadow-2xl shadow-black/20"
          onMouseDown={(e) => handleStart(e.clientX)}
          onTouchStart={(e) => handleStart(e.touches[0].clientX)}
        >
          <img
            src={api.getPresetPreview('teal_orange')}
            alt="Before and after comparison"
            className="w-full h-auto block"
            draggable={false}
          />

          {/* Slider line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg z-10"
            style={{ left: `${sliderPos}%` }}
          >
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white shadow-lg flex items-center justify-center">
              <div className="flex gap-0.5">
                <div className="w-0.5 h-3 bg-gray-400 rounded-full" />
                <div className="w-0.5 h-3 bg-gray-400 rounded-full" />
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

        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-6">
          This took 30 seconds. No editing skills needed.
        </p>
      </div>
    </section>
  );
}
