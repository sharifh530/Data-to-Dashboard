import pytest
from dtd_api.contracts import ModelConfig, RunCreate
from pydantic import ValidationError


def test_eda_does_not_infer_target_from_question() -> None:
    command = RunCreate(
        dataset_version_id="d40a5407-adf7-40f9-9707-4c4862de2270",
        question="Predict revenue",
        disclosure_ack_version="v1",
    )
    assert command.model is None


@pytest.mark.parametrize("split", ["group", "chronological"])
def test_nonrandom_split_requires_column(split: str) -> None:
    with pytest.raises(ValidationError):
        ModelConfig(target="revenue", task="regression", split=split)


@pytest.mark.parametrize(
    "patch",
    [
        {"target": " "},
        {"task": "forecasting"},
        {"exclude_columns": ["revenue"]},
        {"split_column": "date"},
        {"exclude_columns": ["id", "id"]},
        {"source": "arbitrary code"},
        {"exclude_columns": [" "]},
    ],
)
def test_invalid_model_configuration_is_rejected(patch: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ModelConfig.model_validate({"target": "revenue", "task": "regression", **patch})


def test_valid_group_split() -> None:
    value = ModelConfig(target="revenue", task="regression", split="group", split_column="customer")
    assert value.split_column == "customer"
