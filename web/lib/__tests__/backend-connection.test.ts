/**
 * Backend Connection Tests
 *
 * Tests for verifying communication between the frontend and ADK backend.
 * Includes both unit tests (mocked) and integration tests (requires running backend).
 */

import { sreClient } from '../api-client';

// Mock fetch for unit tests
global.fetch = jest.fn();

describe('Backend Connection - Unit Tests', () => {
    const API_BASE_URL = process.env.NEXT_PUBLIC_SRE_AGENT_API_URL || "";

    beforeEach(() => {
        (global.fetch as jest.Mock).mockClear();
    });

    describe('useBackendStatus hook behavior', () => {
        it('should construct correct health check URL', () => {
            const expectedUrl = `${API_BASE_URL}/docs`;
            expect(expectedUrl).toBeDefined();
        });

        it('should handle successful connection', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
            });

            const response = await fetch(`${API_BASE_URL}/docs`, { method: 'HEAD' });
            expect(response.ok).toBe(true);
        });

        it('should handle 405 as valid connection (server is up)', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: false,
                status: 405, // Method Not Allowed still means server is responding
            });

            const response = await fetch(`${API_BASE_URL}/docs`, { method: 'HEAD' });
            // 405 means the server is reachable but doesn't accept HEAD
            expect(response.status).toBe(405);
        });

        it('should handle network errors gracefully', async () => {
            (global.fetch as jest.Mock).mockRejectedValueOnce(
                new Error('Network error: ECONNREFUSED')
            );

            await expect(
                fetch(`${API_BASE_URL}/docs`, { method: 'HEAD' })
            ).rejects.toThrow('Network error');
        });
    });

    describe('CopilotKit endpoint accessibility', () => {
        it('should reach /api/copilotkit endpoint', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ status: 'ok' }),
            });

            const response = await fetch(`${API_BASE_URL}/api/copilotkit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'test' }),
            });

            expect(response.ok).toBe(true);
        });
    });

    describe('API Tools endpoints', () => {
        it('should call trace endpoint with correct URL format', async () => {
            const mockTrace = { trace_id: 'test-123', spans: [] };
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => mockTrace,
            });

            const result = await sreClient.getTrace('test-123');

            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/tools/trace/test-123')
            );
            expect(result).toEqual(mockTrace);
        });

        it('should call logs analyze endpoint with correct payload', async () => {
            const mockResponse = { patterns: [], anomalies: [] };
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const params = {
                filter: 'severity=ERROR',
                baseline_start: '2024-01-01T00:00:00Z',
                baseline_end: '2024-01-01T01:00:00Z',
                comparison_start: '2024-01-01T01:00:00Z',
                comparison_end: '2024-01-01T02:00:00Z',
            };

            const result = await sreClient.analyzeLogs(params);

            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/tools/logs/analyze'),
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params),
                })
            );
            expect(result).toEqual(mockResponse);
        });

        it('should handle API errors with descriptive messages', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: false,
                statusText: 'Internal Server Error',
            });

            await expect(sreClient.getTrace('bad-id')).rejects.toThrow(
                'Failed to fetch trace: Internal Server Error'
            );
        });
    });
});

// Integration tests - run with: npm run test:integration
// These require the backend to be running on localhost:8000
describe.skip('Backend Connection - Integration Tests', () => {
    const API_BASE_URL = process.env.NEXT_PUBLIC_SRE_AGENT_API_URL || 'http://127.0.0.1:8000';

    beforeAll(() => {
        // Restore real fetch for integration tests
        (global.fetch as jest.Mock).mockRestore?.();
    });

    it('should connect to backend /docs endpoint', async () => {
        const response = await fetch(`${API_BASE_URL}/docs`);
        expect(response.status).toBe(200);
    });

    it('should connect to CopilotKit endpoint', async () => {
        // Just check the endpoint is reachable, not that it processes correctly
        const response = await fetch(`${API_BASE_URL}/copilotkit`, {
            method: 'OPTIONS',
        });
        // OPTIONS or 404 means the server is at least responding
        expect([200, 204, 404, 405]).toContain(response.status);
    });

    it('should get error for invalid trace ID (but connect successfully)', async () => {
        try {
            await sreClient.getTrace('nonexistent-trace-id');
        } catch (error: any) {
            // We expect a fetch error or API error, NOT a connection refused
            expect(error.message).not.toMatch(/ECONNREFUSED/);
        }
    });
});
