from typing import Annotated, Literal

from pydantic import Field, model_validator

from dtd_api.contracts import Contract

Cell = Annotated[str, Field(max_length=128)]
Count = Annotated[int, Field(ge=0, le=100000, strict=True)]


class TablePreview(Contract):
    name: Cell
    columns: list[Cell] = Field(min_length=1, max_length=64)
    row_count: Count
    missing: list[Count] = Field(min_length=1, max_length=64)
    preview: list[list[Cell | None]] = Field(max_length=5)

    @model_validator(mode="after")
    def shape(self) -> "TablePreview":
        if len(self.missing) != len(self.columns) or any(n > self.row_count for n in self.missing):
            raise ValueError("Invalid missing counts")
        if len(self.preview) != min(5, self.row_count):
            raise ValueError("Invalid preview length")
        if any(len(row) != len(self.columns) for row in self.preview):
            raise ValueError("Invalid preview width")
        return self


class InspectionReport(Contract):
    schema_version: Literal["1"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    format: Literal["csv", "sqlite"]
    status: Literal["ready", "rejected"]
    tables: list[TablePreview] = Field(max_length=10)
    warnings: list[Annotated[str, Field(max_length=100)]] = Field(max_length=10)
    delimiter: Literal[",", ";", "\t", "|"] | None
    error: Annotated[str, Field(pattern=r"^[A-Z0-9_]{1,80}$")] | None

    @model_validator(mode="after")
    def consistency(self) -> "InspectionReport":
        if self.status == "ready" and (not self.tables or self.error is not None):
            raise ValueError("Invalid ready report")
        if self.status == "rejected" and (self.tables or self.error is None):
            raise ValueError("Invalid rejection report")
        if self.status == "ready" and self.format == "csv" and len(self.tables) != 1:
            raise ValueError("CSV requires one table")
        return self


class TopValue(Contract):
    value: Cell
    count: Count


class ColumnProfile(Contract):
    name: Cell
    distinct: Count
    numeric_count: Count
    nonnumeric_count: Count
    numeric_min: Cell | None
    numeric_max: Cell | None
    top_values: list[TopValue] = Field(max_length=5)


class ProfileTable(TablePreview):
    profile: list[ColumnProfile] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def profile_shape(self) -> "ProfileTable":
        if len(self.profile) != len(self.columns):
            raise ValueError("Profile width mismatch")
        for index, column in enumerate(self.profile):
            if column.name != self.columns[index]:
                raise ValueError("Profile name mismatch")
            if (
                column.numeric_count + column.nonnumeric_count + self.missing[index]
                != self.row_count
            ):
                raise ValueError("Profile count mismatch")
            if column.distinct > self.row_count - self.missing[index]:
                raise ValueError("Profile distinct mismatch")
            if any(value.count > self.row_count for value in column.top_values):
                raise ValueError("Profile top count mismatch")
        return self


class ProfileReport(Contract):
    schema_version: Literal["1"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    format: Literal["csv", "sqlite"]
    status: Literal["ready", "rejected"]
    tables: list[ProfileTable] = Field(max_length=1)
    warnings: list[Annotated[str, Field(max_length=100)]] = Field(max_length=10)
    delimiter: Literal[",", ";", "\t", "|"] | None
    error: Annotated[str, Field(pattern=r"^[A-Z0-9_]{1,80}$")] | None

    @model_validator(mode="after")
    def consistency(self) -> "ProfileReport":
        if self.status == "ready" and (len(self.tables) != 1 or self.error):
            raise ValueError("Invalid ready profile")
        if self.status == "rejected" and (self.tables or not self.error):
            raise ValueError("Invalid rejected profile")
        return self
