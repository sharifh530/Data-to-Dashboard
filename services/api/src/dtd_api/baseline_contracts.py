"""Contracts for baseline modeling provenance."""

from typing import Any, Literal

from pydantic import Field, model_validator

from dtd_api.contracts import Contract


class FeatureInfo(Contract):
    """Information about a column evaluated for feature selection."""

    name: str = Field(max_length=128)
    dtype: str = Field(max_length=32)
    role: Literal["numeric", "categorical", "excluded"]
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "FeatureInfo":
        if self.role == "excluded" and not self.exclusion_reason:
            raise ValueError("Excluded feature must have a reason")
        if self.role != "excluded" and self.exclusion_reason:
            raise ValueError("Included feature cannot have an exclusion reason")
        return self


class SplitInfo(Contract):
    """Information about the train/test split."""

    train_rows: int = Field(ge=0)
    test_rows: int = Field(ge=0)
    seed: int
    strategy: Literal["stratified", "random"]
    test_fraction: float = Field(ge=0.0, le=1.0)


class ModelMetrics(Contract):
    """Metrics and parameters for a single fitted model."""

    model_name: str = Field(max_length=64)
    # Classification metrics
    accuracy: float | None = None
    macro_f1: float | None = None
    roc_auc: float | None = None
    # Regression metrics
    mae: float | None = None
    rmse: float | None = None
    r2: float | None = None

    parameters: dict[str, Any] = Field(default_factory=dict)
    fit_time_seconds: float = Field(ge=0.0)


class BaselineComparison(Contract):
    """Comparison between candidate and reference baseline."""

    candidate_better: bool
    better_model: str = Field(max_length=64)
    reason: str


class BaselineReport(Contract):
    """Complete provenance report produced by the baseline execution."""

    schema_version: Literal["1"] = "1"
    status: Literal["ready", "skipped", "failed"]
    input_sha256: str = Field(max_length=64)
    task_type: Literal["classification", "regression"] | None = None
    target_column: str | None = None

    features: list[FeatureInfo] = Field(default_factory=list)
    split: SplitInfo | None = None
    reference: ModelMetrics | None = None
    candidate: ModelMetrics | None = None
    comparison: BaselineComparison | None = None

    confusion_matrix: list[list[int]] | None = None
    skip_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None

    @model_validator(mode="after")
    def consistency(self) -> "BaselineReport":
        if self.status == "ready":
            if not self.reference or not self.candidate or not self.comparison or not self.split:
                raise ValueError("Ready report must include models and split info")
            if self.skip_reason:
                raise ValueError("Ready report cannot have a skip reason")
        elif self.status == "skipped":
            if not self.skip_reason:
                raise ValueError("Skipped report must have a skip reason")
        elif self.status == "failed":
            if not self.error:
                raise ValueError("Failed report must have an error")
        return self
