import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import axios from 'axios';
import Onboarding from './Onboarding';

vi.mock('axios');
const mockedAxios = vi.mocked(axios, { deep: true });

describe('Onboarding Component', () => {
  const mockOnSetup = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockedAxios.isAxiosError.mockImplementation((e: unknown) => typeof e === 'object' && e !== null && 'isAxiosError' in e && (e as { isAxiosError: boolean }).isAxiosError === true);
  });

  it('completes fast-path setup when everything is verified', async () => {
    mockedAxios.get.mockImplementation(async (url) => {
      if (url.includes('/check_bucket')) return { data: { exists: true, buckets: [{ name: 'projects/123/buckets/traces' }] } };
      if (url.includes('/verify')) return { data: { verified: true } };
      return { data: {} };
    });
    mockedAxios.post.mockResolvedValue({ data: { status: 'success' } });

    render(<Onboarding projectId="test-project" onSetup={mockOnSetup} loading={false} error={null} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Start Automated Setup/i }));
    });

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/graph/setup/schema/create_dataset', expect.any(Object));
    });

    // We should see "Open Agent Graph" button at the end
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /Open Agent Graph/i });
      expect(btn).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Open Agent Graph/i }));
    });
    expect(mockOnSetup).toHaveBeenCalledWith('traces', 'sre-agent');
  });

  it('shows missing bucket prompt when check_bucket returns false', async () => {
    mockedAxios.get.mockImplementation(async (url) => {
      if (url.includes('/check_bucket')) return { data: { exists: false } };
      return { data: {} };
    });

    render(<Onboarding projectId="test-project" onSetup={mockOnSetup} loading={false} error={null} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Start Automated Setup/i }));
    });

    await waitFor(() => {
      expect(screen.getByText(/No Observability Bucket found/i)).toBeInTheDocument();
    });
  });

  it('proceeds through link_dataset if BQ is missing', async () => {
    mockedAxios.get.mockImplementation(async (url) => {
      if (url.includes('/check_bucket')) return { data: { exists: true, buckets: [{ name: 'projects/123/buckets/traces' }] } };
      if (url.includes('/verify')) {
        const error = new Error('Not found') as Error & { response: { status: number }, isAxiosError: boolean };
        error.response = { status: 404 };
        error.isAxiosError = true;
        throw error;
      }
      return { data: {} };
    });

    mockedAxios.post.mockImplementation(async (url) => {
      if (url.includes('/link_dataset')) return { data: { status: 'already_linked' } };
      if (url.includes('/schema/')) return { data: { status: 'success' } };
      return { data: {} };
    });

    render(<Onboarding projectId="test-project" onSetup={mockOnSetup} loading={false} error={null} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Start Automated Setup/i }));
    });

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/graph/setup/link_dataset', expect.objectContaining({
        bucket_id: 'traces'
      }));
    });

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /Open Agent Graph/i });
      expect(btn).toBeInTheDocument();
    });
  });
});
