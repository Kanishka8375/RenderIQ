import { useState, useCallback } from 'react';
import { api } from '../api/client';

const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];
const MAX_SIZE_MB = 500;

export function useUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

  const validateFile = useCallback((file) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported format. Please upload ${ALLOWED_EXTENSIONS.join(', ')}.`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File too large. Maximum size is ${MAX_SIZE_MB}MB.`;
    }
    return null;
  }, []);

  const uploadRaw = useCallback(async (file) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return null;
    }

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const result = await api.uploadRaw(file, setProgress);
      setUploadResult(result);
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setUploading(false);
    }
  }, [validateFile]);

  const reset = useCallback(() => {
    setUploading(false);
    setProgress(0);
    setUploadResult(null);
    setError(null);
  }, []);

  return { uploading, progress, uploadResult, error, uploadRaw, reset, validateFile };
}
