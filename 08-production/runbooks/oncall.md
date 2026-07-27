# On-call runbook

## Rotation

- Primary on-call: 1 week shifts, rotating among team members.
- Secondary on-call: 1 week shifts, backing up the primary.
- Escalation: if the primary does not respond within 15 minutes, the secondary is paged. If the secondary does not respond within 15 minutes, the team lead is paged.

## Alerting

Alerts are configured in LangSmith and Prometheus. The on-call is paged for:

- Error rate above 1 percent for 5 minutes.
- p95 latency above 10 seconds for 5 minutes.
- Cost per request above $0.20 for 10 minutes.
- Any SEV1 incident (agent down, data loss, security breach).

Alerts are NOT pages for:

- Individual request failures (these happen; investigate in business hours).
- Slow individual requests (these happen; investigate in business hours).
- Cost spikes under $10 (these are noise).

## Common incidents and quick fixes

### Agent returning errors

1. Check the LangSmith error dashboard. What is the error?
2. If it is an LLM API error (429, 500), the provider is having issues. Wait or switch providers.
3. If it is a tool error, check the tool's API. If the tool is down, disable it.
4. If it is a code error (exception in a node), roll back to the previous version.

### Agent slow

1. Check the latency dashboard. Is it p50 or p95 that is high?
2. If p50 is high, the agent is doing more work than usual. Check the tool-call count dashboard.
3. If p95 is high, a subset of requests is slow. Sample traces to find the pattern.
4. Quick fix: scale up the deployment. Long-term fix: optimize the slow path.

### Agent expensive

1. Check the cost dashboard. Which requests are expensive?
2. If a few requests are very expensive, they are probably looping. Check the recursion limit.
3. If all requests are expensive, the model routing might be broken (everything going to the expensive model). Check the router.
4. Quick fix: lower the token budget. Long-term fix: improve the router or add caching.

### Agent giving bad answers

1. Check the feedback dashboard. Are thumbs-down rates up?
2. Sample 10 bad-answer traces. What do they have in common?
3. If a specific question type is failing, add it to the golden dataset and write a fix.
4. If the regression started after a model update, pin the previous model version.

## After the shift

At the end of your shift:

1. Write a handoff note for the next on-call: any open incidents, any watches (things that look bad but are not yet incidents), any fixes in flight.
2. Triage the previous week's alerts: were they all real? Any that should be silenced or retuned?
3. Update this runbook with anything you learned. The runbook gets better every shift.
