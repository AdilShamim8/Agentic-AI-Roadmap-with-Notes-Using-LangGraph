# Governance and safety

Module: 08-production
Chapter: 06-governance-and-safety
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement permissioned tools (RBAC: which users can call which tools)
- Implement audit logs (every tool call logged with input, output, caller, timestamp)
- Implement PII handling (redaction at the boundary, before logging or tracing)
- Reason about compliance frameworks (SOC2, HIPAA, EU AI Act) for agentic systems

## Prerequisites

- [04 Checkpointing and durability](04-checkpointing-and-durability.md)
- [05 Cost optimization](05-cost-optimization.md)

## Conceptual foundation

Governance is the set of controls that make an agent safe to deploy in a regulated environment (finance, healthcare, legal) or in any environment where the agent's actions have real consequences. Without governance, the agent is a liability: it can leak data, take unauthorized actions, and produce audit trails that do not satisfy regulators.

The four pillars of governance:

1. Permissioned tools. Not every user can call every tool. An admin can issue refunds; a regular user cannot. A doctor can access medical records; a receptionist cannot. The implementation: the tool list is filtered by the user's role at agent-creation time (dynamic tool loading, covered in module 03). The tool itself also checks the user's permission before executing, as defense in depth.

2. Audit logs. Every tool call is logged with: the caller (user ID), the timestamp, the tool name, the input arguments, the output, and the success/failure status. The log is append-only (cannot be modified after the fact), retained per the compliance requirement (typically 1-7 years), and queryable for incident investigation.

3. PII handling. Personally identifiable information (PII) must be redacted before it enters logs, traces, or LLM prompts that go to third-party APIs. The implementation: a PII detection layer at the boundary (before logging, before sending to the LLM) that redacts or masks PII. The PII is preserved in the original data store (which is access-controlled) but not in the logs.

4. Compliance frameworks. SOC2 (security controls for SaaS), HIPAA (healthcare data), GDPR/EU AI Act (EU privacy and AI regulation). Each framework has specific requirements; agentic systems must be designed to meet them. The general pattern: design for the strictest framework you might need to comply with, even if you do not need it today.

## Worked example

A governance wrapper around a tool: permission check, audit log, PII redaction. Full code in [`examples/governance_demo.py`](../examples/governance_demo.py).

```python
import logging
import json
from datetime import datetime
from typing import Callable

audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler("audit.log")
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
audit_logger.addHandler(handler)

def governed_tool(tool_func: Callable, required_role: str, pii_fields: list[str]) -> Callable:
    """Wrap a tool with permission check, audit logging, and PII redaction."""
    def wrapper(user_id: str, user_role: str, **kwargs):
        # 1. Permission check
        if user_role != required_role:
            audit_logger.info(json.dumps({
                "event": "permission_denied", "user": user_id, "tool": tool_func.__name__,
                "required_role": required_role, "user_role": user_role, "timestamp": datetime.utcnow().isoformat(),
            }))
            return f"Permission denied. Requires role: {required_role}."

        # 2. Redact PII for logging
        log_args = {k: ("[REDACTED]" if k in pii_fields else v) for k, v in kwargs.items()}

        # 3. Execute
        try:
            result = tool_func(**kwargs)
            audit_logger.info(json.dumps({
                "event": "tool_call", "user": user_id, "tool": tool_func.__name__,
                "args": log_args, "success": True, "timestamp": datetime.utcnow().isoformat(),
            }))
            return result
        except Exception as e:
            audit_logger.info(json.dumps({
                "event": "tool_call", "user": user_id, "tool": tool_func.__name__,
                "args": log_args, "success": False, "error": str(e), "timestamp": datetime.utcnow().isoformat(),
            }))
            return f"Tool failed: {e}"

    return wrapper

# Usage
def issue_refund_impl(order_id: str, amount: float) -> str:
    return f"Refunded ${amount} for {order_id}"

issue_refund = governed_tool(
    issue_refund_impl,
    required_role="admin",
    pii_fields=["order_id"],  # order IDs are considered PII in this example
)

# Admin call: succeeds, logged with redacted order_id
print(issue_refund(user_id="alice", user_role="admin", order_id="ACME-123", amount=50.0))
# Regular user call: denied, logged
print(issue_refund(user_id="bob", user_role="user", order_id="ACME-456", amount=25.0))
```

## Evaluation

Test that: (1) permission denials are logged and the tool is not executed, (2) successful calls are logged with PII redacted, (3) the audit log is append-only (no entries modified or deleted).

## Production notes

In production, the audit log is a critical compliance artifact. It must be: append-only (use a write-once storage like AWS S3 Object Lock or a blockchain-based log), retained per the compliance requirement (HIPAA: 6 years; SOC2: 1-7 years depending on the auditor), and queryable (for incident investigation). The log should be stored separately from the application database, so a database breach does not compromise the audit trail.

The most common production failure: PII leaks into LLM traces. LangSmith traces contain the full prompt and response, including any PII the user sent. The fix: configure LangSmith to redact PII before storing, or do not trace requests with PII (route them to a separate, non-traced deployment).

## Common pitfalls

- Permission checks only at the tool list level. Why: it works when the list is filtered. Fix: also check inside the tool, as defense in depth.
- PII in traces. Why: tracing is "internal." Fix: redact PII before tracing; traces are often stored by third parties.
- Audit logs in the application database. Why: it is convenient. Fix: store audit logs separately, append-only.

## Further reading

- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [EU AI Act](https://artificialintelligenceact.eu/)
- [LangSmith PII redaction](https://docs.smith.langchain.com/observability/tutorials/setup#redact)

## Checklist

- [ ] Implement permissioned tools with role-based access
- [ ] Implement append-only audit logs for every tool call
- [ ] Implement PII redaction at the boundary (before logging and tracing)
- [ ] Reason about which compliance frameworks apply to your agent
