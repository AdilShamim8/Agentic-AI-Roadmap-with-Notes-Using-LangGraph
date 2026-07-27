# Incident response runbook

Use this template for every production incident. Copy it, fill it in, and post it in the incident channel.

## 1. Stop the bleeding (5 minutes)

The first goal is to stop user impact. Do not diagnose yet.

- Is the agent returning errors? Roll back to the previous version: `kubectl rollout undo deployment/langgraph-agent`
- Is the agent returning bad answers? Disable the agent and return a fallback: set `AGENT_ENABLED=false` and restart
- Is the agent slow? Scale up: `kubectl scale deployment/langgraph-agent --replicas=10`
- Is the agent costing too much? Disable expensive tools: set `EXPENSIVE_TOOLS_ENABLED=false` and restart

## 2. Diagnose (15 minutes)

Once user impact is stopped, diagnose the cause.

- Open LangSmith. Filter traces by the last 30 minutes. Sort by error or by long latency.
- Read 5 failing traces. What do they have in common?
  - Same tool failing? Check the tool's API status.
  - Same LLM error? Check the LLM provider's status page.
  - Same user input pattern? It might be a prompt injection or an edge case.
- Check the dashboards: latency, cost, error rate, tool-call distribution. When did the regression start? What changed around that time?

## 3. Fix (variable)

The fix depends on the diagnosis.

- LLM provider outage: wait it out; switch to a backup provider if you have one.
- Tool API outage: disable the tool, fall back to a different tool or a human.
- Prompt regression: roll back the prompt, re-run the eval, ship a fix.
- Model update regression: pin the model version, re-run the eval, ship a fix.

## 4. Post-mortem (within 48 hours)

Write a post-mortem. Use the template below.

```markdown
# Post-mortem: [incident title]

Date: YYYY-MM-DD
Severity: SEV1 (user-facing outage) / SEV2 (degraded) / SEV3 (minor)
Duration: X hours Y minutes

## Summary
One paragraph: what happened, who was affected, how it was resolved.

## Timeline
- HH:MM - alert fired
- HH:MM - on-call engaged
- HH:MM - bleeding stopped (rollback/scale-up/disable)
- HH:MM - root cause identified
- HH:MM - fix shipped
- HH:MM - incident closed

## Root cause
What caused the incident. Be specific. Name the component, the change, the failure mode.

## What went well
What worked in the response. Be specific.

## What went wrong
What did not work. Be specific. Include detection time, diagnosis time, fix time.

## Action items
- [ ] Action 1 (owner, due date)
- [ ] Action 2 (owner, due date)
- [ ] Action 3 (owner, due date)
```

## 5. Ship the action items

Action items from the post-mortem are tracked as issues and shipped within the agreed timeline. An incident without shipped action items will repeat.
