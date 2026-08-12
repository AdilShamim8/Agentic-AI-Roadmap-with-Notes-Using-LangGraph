"""Agent package.

Provides `BaseAgent` (the contract) and a registry of sample agents, one
per pattern. Plug in your own agent by subclassing `BaseAgent`.
"""

from eval.agents.base import BaseAgent
from eval.schemas import AgentOutput, Trajectory, TrajectoryStep, ToolCall
from eval.agents.sample_agents import (
    ReActSampleAgent,
    PlanExecuteSampleAgent,
    SupervisorSampleAgent,
    SwarmSampleAgent,
    MapReduceSampleAgent,
)

__all__ = [
    "BaseAgent",
    "AgentOutput",
    "Trajectory",
    "TrajectoryStep",
    "ToolCall",
    "ReActSampleAgent",
    "PlanExecuteSampleAgent",
    "SupervisorSampleAgent",
    "SwarmSampleAgent",
    "MapReduceSampleAgent",
]
