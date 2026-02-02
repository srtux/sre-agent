### SLO & Error Budgets
We follow Google SRE standards using Multi-Window Burn Rate.
- **Fast Burn**: Consuming budget at a rate that will exhaust it in hours (Critical).
- **Slow Burn**: Chronic consumption that threatens the month's budget.

### Example Workflow:
1. "Show me the burn rate for `Payments service`."
2. Agent shows a card with current 1h vs 6h burn.
3. If burn > 14.4, it recommends immediate triage.
