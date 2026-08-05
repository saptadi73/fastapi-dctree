import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DecisionTreeColumn(BaseModel):
    name: str
    role: str
    data_type: str
    enabled: bool = True
    categories: list[Any] | None = None


class DecisionTreeTargetTransform(BaseModel):
    type: Literal["numeric_bins"] = "numeric_bins"
    scale: float = 1.0
    thresholds: list[float]
    labels: list[str]


class DecisionTreeTask(BaseModel):
    type: str = "classification"
    target_column: str
    positive_class: str | None = None
    target_transform: DecisionTreeTargetTransform | None = None


class DecisionTreeSplit(BaseModel):
    test_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    random_state: int = 42
    stratify: bool = True


class DecisionTreePreprocessingConfig(BaseModel):
    mode: str = "strict"
    collapse_rare_study_programs: bool = True
    simplify_social_media_platforms: bool = True
    normalize_binary_labels: bool = True
    normalize_duration_buckets: bool = True


class DecisionTreeModelConfig(BaseModel):
    criterion: str = "gini"
    splitter: str = "best"
    max_depth: int | None = 4
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    random_state: int = 42


class DecisionTreeConfig(BaseModel):
    preset: Literal["indonesia", "india"] | None = None
    task: DecisionTreeTask
    columns: list[DecisionTreeColumn]
    preprocessing: DecisionTreePreprocessingConfig = DecisionTreePreprocessingConfig()
    split: DecisionTreeSplit = DecisionTreeSplit()
    model: DecisionTreeModelConfig = DecisionTreeModelConfig()


class ExperimentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_name: str
    status: str
    config_json: dict[str, Any]
    result_json: dict[str, Any]
    created_at: datetime


class ConfusionMatrixValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actual_label: str
    predicted_label: str
    value: int


class ClassMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_label: str
    precision: float
    recall: float
    f1_score: float
    support: int


class FeatureImportanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_name: str
    importance: float
