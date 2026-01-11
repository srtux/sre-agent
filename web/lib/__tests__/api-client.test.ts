import { sreClient } from '../api-client';

// Mock the global fetch
global.fetch = jest.fn();

describe('SRE Agent API Client', () => {
  const API_BASE_URL = process.env.NEXT_PUBLIC_SRE_AGENT_API_URL || "";

  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  describe('getTrace', () => {
    it('fetches a trace by ID', async () => {
      const mockTrace = { traceId: '123', spans: [] };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrace,
      });

      const result = await sreClient.getTrace('123');

      expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/tools/trace/123`);
      expect(result).toEqual(mockTrace);
    });

    it('fetches a trace with project ID', async () => {
      const mockTrace = { traceId: '123' };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrace,
      });

      await sreClient.getTrace('123', 'my-project');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('project_id=my-project')
      );
    });

    it('throws error when fetch fails', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(sreClient.getTrace('999')).rejects.toThrow('Failed to fetch trace: Not Found');
    });
  });

  describe('analyzeLogs', () => {
    it('sends analysis request successfully', async () => {
      const mockParams = {
        filter: 'error',
        baseline_start: '2023-01-01',
        baseline_end: '2023-01-02',
        comparison_start: '2023-01-03',
        comparison_end: '2023-01-04'
      };

      const mockResponse = { anomalies: [] };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await sreClient.analyzeLogs(mockParams);

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/tools/logs/analyze`,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockParams),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });
});
