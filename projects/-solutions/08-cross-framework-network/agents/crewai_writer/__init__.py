"""
CrewAI Writer Crew — A2A server.

This module wraps a CrewAI-style crew as an A2A server.  The crew
handles **writing** tasks and is composed of three specialized agents:

    1. **Content Strategist** — plans the structure and angle.
    2. **Writer** — drafts the content based on the strategy.
    3. **Editor** — reviews, polishes, and finalizes.

The crew processes tasks sequentially (strategize → write → edit),
mirroring the real CrewAI ``Crew(process=Process.sequential)`` pattern.
"""

from agents.crewai_writer.crew import WriterCrew, create_writer_crew
from agents.crewai_writer.server import (
    WriterCrewExecutor,
    create_server,
    get_agent_card,
)

__all__ = [
    "WriterCrew",
    "create_writer_crew",
    "WriterCrewExecutor",
    "create_server",
    "get_agent_card",
]
