from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ModelConfig(Contract):
    target: str = Field(min_length=1, max_length=200)
    task: Literal["classification", "regression"]
    split: Literal["random", "group", "chronological"] = "random"
    split_column: str | None = Field(default=None, min_length=1, max_length=200)
    exclude_columns: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def check_split(self) -> "ModelConfig":
        if (self.split != "random") != (self.split_column is not None):
            raise ValueError("Group/chronological splits require a split column; random does not")
        if self.target in self.exclude_columns or self.target == self.split_column:
            raise ValueError("Target cannot be excluded or used as the split column")
        if len(self.exclude_columns) != len(set(self.exclude_columns)):
            raise ValueError("Excluded columns must be unique")
        if any(not value.strip() or len(value) > 200 for value in self.exclude_columns):
            raise ValueError("Excluded columns must be nonempty and at most 200 characters")
        return self


class RunCreate(Contract):
    """Future command contract; no run-submission endpoint exists yet."""

    dataset_version_id: UUID
    question: str = Field(default="", max_length=2000)
    model: ModelConfig | None = None
    disclosure_ack_version: str = Field(min_length=1, max_length=40)


class Capabilities(Contract):
    schema_version: Literal["1"] = "1"
    mode: Literal["foundation"] = "foundation"
    uploads_enabled: Literal[False] = False
    execution_enabled: Literal[False] = False
    persistence_enabled: Literal[False] = False
    reason: str = "Execution requires a verified broker, isolation evidence, and authentication."


class Health(Contract):
    status: Literal["ok"] = "ok"
    service: Literal["data-to-dashboard-api"] = "data-to-dashboard-api"


class ErrorDetail(Contract):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str
    retryable: bool = False


class ErrorResponse(Contract):
    error: ErrorDetail
