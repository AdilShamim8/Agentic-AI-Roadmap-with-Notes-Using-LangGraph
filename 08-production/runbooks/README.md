# Production runbooks

This directory contains runbooks for operating agentic AI systems in production. Each runbook is a step-by-step guide for a specific operational scenario.

## Runbooks

- [Incident response](./incident-template.md) - what to do when the agent is failing in production
- [On-call](./oncall.md) - the on-call rotation, escalation paths, and common incidents

## When to use these runbooks

The agent is failing in production. The dashboard is red. Users are complaining. You need to: (1) stop the bleeding, (2) diagnose the cause, (3) fix it, (4) write a post-mortem. The runbooks walk you through each step.

## The principle

Runbooks exist so that on-call engineers do not have to think during an incident. Every step is written down. Every command is copy-pasteable. Every decision tree is explicit. The runbook is the difference between a 15-minute recovery and a 2-hour recovery.
