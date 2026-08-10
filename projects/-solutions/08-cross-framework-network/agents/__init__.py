"""
Agents package — A2A agent servers built on different frameworks.

Each sub-package wraps a framework-specific agent as an A2A server:

    - ``openai_research``: an OpenAI Agents SDK agent that handles research.
    - ``crewai_writer``:   a CrewAI crew that handles writing.

Both expose the same A2A protocol, demonstrating that the protocol
is truly framework-agnostic.
"""
