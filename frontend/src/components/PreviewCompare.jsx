import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '../api/client';

export default function PreviewCompare({ comparisonUrl, jobId }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [dragging, setDragging] = useState(false);
  const [imageSrc, setImageSrc] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!comparisonUrl || !jobId) return;
    let revoked = false;
    const headers = api.getDownloadHeaders(jobId);
    fetch(comparisonUrl, { headers })
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load comparison');
        return r.blob();
      })
      .then((blob) => {
        if (revoked) return;
        setImageSrc(URL.createObjectURL(blob));
      })
      .catch(() => {
        if (!revoked) setImageSrc(comparisonUrl);
      });
    return () => {
      revoked = true;
      if (imageSrc) URL.revokeObjectURL(imageSrc);
    };
  }, [comparisonUrl, jobId]);

  const getPosition = useCallback((clientX) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return 50;
    const x = clientX - rect.left;
    return Math.max(0, Math.min(100, (x / rect.width) * 100));
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

  if (!comparisonUrl || !imageSrc) return null;

  return (
    <div className="space-y-3">
      <div
        ref={containerRef}
        className="relative rounded-xl overflow-hidden cursor-col-resize select-none border border-white/10"
        onMouseDown={(e) => handleStart(e.clientX)}
        onTouchStart={(e) => handleStart(e.touches[0].clientX)}
      >
        <img
          src={imageSrc}
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
    </div>
  );
}
