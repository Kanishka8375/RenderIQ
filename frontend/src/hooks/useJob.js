import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

export function useJob(jobId) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const startPolling = useCallback(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const data = await api.getStatus(jobId);
        setStatus(data);
        setError(null);

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch (err) {
        setError(err.message);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
  }, [jobId]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return {
    status: status?.status,
    progress: status?.progress || 0,
    currentStep: status?.current_step || '',
    result: status?.result,
    elapsedSeconds: status?.elapsed_seconds || 0,
    estimatedRemaining: status?.estimated_remaining,
    queuePosition: status?.queue_position,
    error,
    startPolling,
    stopPolling,
  };
}
