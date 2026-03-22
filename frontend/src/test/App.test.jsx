import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from '../App';

// Mock fetch for presets
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ presets: [] }),
  })
);

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(document.getElementById('root') || document.body).toBeTruthy();
  });

  it('shows the RenderIQ header', () => {
    render(<App />);
    expect(screen.getByText('Render')).toBeInTheDocument();
    expect(screen.getByText('IQ')).toBeInTheDocument();
  });

  it('shows upload zone on initial load', () => {
    render(<App />);
    expect(screen.getByText('Drop your video here')).toBeInTheDocument();
  });

  it('shows accepted formats in upload zone', () => {
    render(<App />);
    expect(screen.getByText(/MP4, MOV, AVI, MKV, WebM/)).toBeInTheDocument();
  });

  it('shows step indicators', () => {
    render(<App />);
    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('Style')).toBeInTheDocument();
    expect(screen.getByText('Result')).toBeInTheDocument();
  });
});
