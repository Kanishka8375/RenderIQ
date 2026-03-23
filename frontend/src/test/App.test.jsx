import { render, screen, fireEvent } from '@testing-library/react';
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

  it('shows hero headline on landing page', () => {
    render(<App />);
    expect(screen.getByText(/Cinematic/)).toBeInTheDocument();
    expect(screen.getByText(/in Seconds/)).toBeInTheDocument();
  });

  it('shows How It Works section', () => {
    render(<App />);
    expect(screen.getByText('How It Works')).toBeInTheDocument();
    expect(screen.getAllByText('Upload Your Video').length).toBeGreaterThan(0);
    expect(screen.getByText('Pick a Style')).toBeInTheDocument();
    expect(screen.getByText('Download Your Video')).toBeInTheDocument();
  });

  it('shows CTA buttons', () => {
    render(<App />);
    const tryButtons = screen.getAllByText(/Try It Free/);
    expect(tryButtons.length).toBeGreaterThan(0);
  });

  it('shows tool section after clicking CTA', () => {
    render(<App />);
    const ctaButton = screen.getAllByText(/Try It Free/)[0];
    fireEvent.click(ctaButton);
    expect(screen.getByText('Upload your video')).toBeInTheDocument();
  });

  it('shows footer with credits', () => {
    render(<App />);
    expect(screen.getByText(/Built by Kanishka/)).toBeInTheDocument();
    expect(screen.getByText(/2026 RenderIQ/)).toBeInTheDocument();
  });
});
