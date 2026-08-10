"""
LangGraph Supervisor package.

Implements a LangGraph-style supervisor that orchestrates two A2A agents:

    * **Research Agent** (OpenAI Agents SDK) — for information gathering.
    * **Writer Crew** (CrewAI) — for content production.

The supervisor decomposes a user task into steps, routes each step to
the appropriate agent via A2A, and synthesizes the final result.
"""
