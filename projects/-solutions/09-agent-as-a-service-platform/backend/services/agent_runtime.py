"""Agent runtime service — manages Docker containers for deployed agents."""
import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models.agent import Agent, AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class InvocationResult:
    a2a_task_id: str | None
    output: str
    metadata: dict[str, Any]


class AgentRuntime:
    """Wraps Docker to deploy / undeploy / invoke agents.

    In production this would talk to Kubernetes or LangGraph Platform.
    For local dev it talks directly to the Docker socket.
    """

    def __init__(self) -> None:
        self._docker_client = None
        try:
            import docker  # type: ignore

            self._docker_client = docker.from_env()
        except Exception as e:  # noqa: BLE001
            logger.warning("Docker client not available: %s", e)

    # -----------------------------------------------------------------
    # Deploy / undeploy
    # -----------------------------------------------------------------
    async def deploy(
        self, agent_id: uuid.UUID, docker_image: str, db: Session
    ) -> None:
        """Pull the image, start a container, and register it.

        Falls back to a "mock deploy" (just marks RUNNING with a stub URL)
        if Docker isn't available.
        """
        # Update status
        agent = db.scalar(select(Agent).where(Agent.id == agent_id))
        if not agent:
            return
        agent.status = AgentStatus.DEPLOYING
        db.commit()

        try:
            if self._docker_client is None:
                # Mock mode — pretend we deployed
                base_url = f"http://agent-runtime:{settings.agent_runtime_port_start}"
                agent.base_url = base_url
                agent.status = AgentStatus.RUNNING
                agent.container_port = settings.agent_runtime_port_start
                db.commit()
                logger.info("Mock-deployed agent %s to %s", agent_id, base_url)
                return

            # Real Docker mode
            port = settings.agent_runtime_port_start + (hash(str(agent_id)) % 100)
            container = self._docker_client.containers.run(
                docker_image,
                detach=True,
                network=settings.docker_network,
                name=f"a2a-agent-{agent.slug}",
                ports={"8080/tcp": port},
                environment={
                    "AGENT_ID": str(agent_id),
                    "AGENT_NAME": agent.name,
                },
                restart_policy={"Name": "unless-stopped"},
            )
            agent.container_id = container.id
            agent.container_port = port
            agent.base_url = f"http://a2a-agent-{agent.slug}:8080"
            agent.status = AgentStatus.RUNNING
            db.commit()
            logger.info("Deployed agent %s (container %s)", agent_id, container.id[:12])

        except Exception as e:  # noqa: BLE001
            logger.exception("Deployment failed for agent %s", agent_id)
            agent.status = AgentStatus.FAILED
            agent.agent_card = {**agent.agent_card, "deploy_error": str(e)}
            db.commit()

    async def undeploy(self, agent: Agent, db: Session) -> None:
        """Stop and remove the agent's container."""
        if not agent.container_id or self._docker_client is None:
            agent.status = AgentStatus.UNDEPLOYED
            db.commit()
            return

        try:
            container = self._docker_client.containers.get(agent.container_id)
            container.stop(timeout=10)
            container.remove()
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not remove container: %s", e)
        finally:
            agent.status = AgentStatus.UNDEPLOYED
            agent.container_id = None
            db.commit()

    # -----------------------------------------------------------------
    # Invoke
    # -----------------------------------------------------------------
    async def invoke(
        self,
        agent: Agent,
        message: str,
        skill_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> InvocationResult:
        """Invoke an agent via the A2A protocol (JSON-RPC over HTTP)."""
        if not agent.base_url:
            raise RuntimeError("Agent has no base_url")

        # A2A v0.3 — JSON-RPC "tasks/send" method
        task_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "sessionId": metadata.get("session_id") if metadata else None,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
                "metadata": metadata or {},
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{agent.base_url.rstrip('/')}/",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract text from the response
        result = data.get("result", {})
        artifacts = result.get("artifacts", [])
        messages = result.get("messages", [])

        output_parts: list[str] = []
        for msg in messages:
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    if part.get("type") == "text":
                        output_parts.append(part.get("text", ""))
        for art in artifacts:
            for part in art.get("parts", []):
                if part.get("type") == "text":
                    output_parts.append(part.get("text", ""))

        output = "\n".join(output_parts) or "(no output)"

        return InvocationResult(
            a2a_task_id=task_id,
            output=output,
            metadata={"raw_response": data},
        )


# Singleton
agent_runtime = AgentRuntime()
