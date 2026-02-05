from pydantic import Field

from app.lib.schema import CamelizedBaseSchema


class HealthCheckResponse(CamelizedBaseSchema):
    status: bool = Field(..., description="Health status of the application")
    timestamp: str = Field(..., description="Timestamp of the health check")
    version: str = Field(..., description="Version of the application")
    service: str = Field(..., description="Name of the service")
    debug: bool = Field(..., description="Debug mode status")


class ReadinessCheckResponse(CamelizedBaseSchema):
    ready: bool = Field(..., description="Readiness status of the application")
    timestamp: str = Field(..., description="Timestamp of the readiness check")


class LivenessCheckResponse(CamelizedBaseSchema):
    alive: bool = Field(..., description="Liveness status of the application")
    timestamp: str = Field(..., description="Timestamp of the liveness check")
