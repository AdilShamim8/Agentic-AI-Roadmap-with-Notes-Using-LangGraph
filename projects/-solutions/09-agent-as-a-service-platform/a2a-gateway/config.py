"""A2A Gateway config."""
import os


class Settings:
    agent_registry_url: str = os.environ.get(
        "AGENT_REGISTRY_URL", "http://backend:8000/internal/agents"
    )
    a2a_gateway_host: str = os.environ.get("A2A_GATEWAY_HOST", "0.0.0.0")
    a2a_gateway_port: int = int(os.environ.get("A2A_GATEWAY_PORT", "8080"))
    public_base_url: str = os.environ.get(
        "NEXT_PUBLIC_A2A_GATEWAY_URL", "http://localhost:8080"
    )


settings = Settings()
