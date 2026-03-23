const API_BASE = import.meta.env.VITE_API_URL || '';

export const api = {
  uploadRaw: (file, onProgress) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || 'Upload failed'));
          } catch {
            reject(new Error(`Upload failed (${xhr.status})`));
          }
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error')));
      xhr.open('POST', `${API_BASE}/api/upload/raw`);
      xhr.send(formData);
    });
  },

  uploadReference: (jobId, file) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('job_id', jobId);
      formData.append('file', file);

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || 'Upload failed'));
          } catch {
            reject(new Error(`Upload failed (${xhr.status})`));
          }
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error')));
      xhr.open('POST', `${API_BASE}/api/upload/reference`);
      xhr.send(formData);
    });
  },

  getPresets: () =>
    fetch(`${API_BASE}/api/presets`).then((r) => {
      if (!r.ok) throw new Error('Failed to load presets');
      return r.json();
    }),

  getPresetPreview: (name) =>
    `${API_BASE}/api/presets/${name}/preview`,

  startGrade: (config) =>
    fetch(`${API_BASE}/api/grade/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    }).then((r) => {
      if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Grade failed'); });
      return r.json();
    }),

  getStatus: (jobId) =>
    fetch(`${API_BASE}/api/grade/status/${jobId}`).then((r) => {
      if (!r.ok) throw new Error('Status check failed');
      return r.json();
    }),

  getDownloadUrl: (jobId, type) =>
    `${API_BASE}/api/download/${jobId}/${type}`,

  submitFeedback: (jobId, rating, comment = '') =>
    fetch(`${API_BASE}/api/admin/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, rating, comment }),
    }).then((r) => r.json()),
};
