"""Response models for process health."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness payload.

    This endpoint does not check MongoDB, S3, or Bedrock. Those readiness
    checks belong to the phases that introduce those dependencies.
    """

    status: Literal["ok"] = "ok"
    service: str = Field(description="Configured application name.")
    environment: str = Field(description="Deployment environment name.")
    version: str = Field(description="Application version.")
