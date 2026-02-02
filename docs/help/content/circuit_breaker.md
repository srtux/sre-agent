### Self-Preservation
When GCP APIs or backend services are down, AutoSRE prevents "Retry Storms" using a Circuit Breaker.
- **State: OPEN**: No requests sent to the failing service.
- **State: HALF-OPEN**: Tests a single request to see if it's healthy.
- **State: CLOSED**: Normal operation.

This protects your API quota and prevents cascading failures during global outages.
