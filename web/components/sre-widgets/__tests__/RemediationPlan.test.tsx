import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import RemediationPlan from '../RemediationPlan';

// Mock Lucide icons
jest.mock('lucide-react', () => ({
  AlertTriangle: () => <div data-testid="icon-alert" />,
  CheckCircle2: () => <div data-testid="icon-check" />,
  ChevronDown: () => <div data-testid="icon-chevron-down" />,
  ChevronRight: () => <div data-testid="icon-chevron-right" />,
  Clock: () => <div data-testid="icon-clock" />,
  Copy: () => <div data-testid="icon-copy" />,
  ExternalLink: () => <div data-testid="icon-external-link" />,
  Play: () => <div data-testid="icon-play" />,
  Shield: () => <div data-testid="icon-shield" />,
  Terminal: () => <div data-testid="icon-terminal" />,
  Zap: () => <div data-testid="icon-zap" />,
  XCircle: () => <div data-testid="icon-x-circle" />,
  Loader2: () => <div data-testid="icon-loader" />,
}));

describe('RemediationPlan', () => {
  const mockData = {
    suggestions: [
      {
        action: 'Increase Memory',
        description: 'Increase memory limit to 2GB',
        risk: 'low',
        effort: 'low',
        steps: ['Go to Cloud Run', 'Edit Service', 'Increase Memory'],
        category: 'performance',
      }
    ],
    quick_wins: [],
    recommended_first_action: {
      action: 'Increase Memory',
      description: 'Increase memory limit to 2GB',
      risk: 'low',
      effort: 'low',
      steps: ['Go to Cloud Run', 'Edit Service', 'Increase Memory'],
      category: 'performance',
    },
    matched_patterns: ['OOM Error'],
    finding_summary: 'Service is running out of memory',
  };

  it('renders the remediation plan', () => {
    // @ts-ignore - simplified mock data
    render(<RemediationPlan data={mockData} />);

    expect(screen.getByText('Remediation Plan')).toBeInTheDocument();
    expect(screen.getByText('Service is running out of memory')).toBeInTheDocument();
    expect(screen.getAllByText('Increase Memory').length).toBeGreaterThan(0);
  });

  it('expands suggestion steps on click', () => {
    // @ts-ignore - simplified mock data
    render(<RemediationPlan data={mockData} />);

    // It should be expanded by default because it's recommended, but let's toggle it
    // It should be expanded by default because it's recommended, but let's toggle it
    const buttons = screen.getAllByText('Increase Memory');
    const button = buttons[0].closest('button');
    if (button) {
      fireEvent.click(button); // Helper to toggle
    }
  });

  it('shows gcloud commands when provided', () => {
    const gcloudCommands = {
      commands: [{ description: 'Update memory', command: 'gcloud run services update ...' }],
      warning: 'Be careful',
    };

    // @ts-ignore - simplified mock data
    render(<RemediationPlan data={mockData} gcloudCommands={gcloudCommands} />);

    expect(screen.getByText('Ready-to-Run Commands')).toBeInTheDocument();
    expect(screen.getByText('gcloud run services update ...')).toBeInTheDocument();
  });
});
