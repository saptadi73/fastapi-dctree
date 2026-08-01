from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder
from sklearn.tree import DecisionTreeClassifier, export_text

from app.modules.experiments.schemas import DecisionTreeConfig


def train_decision_tree(dataframe: pd.DataFrame, config: DecisionTreeConfig) -> dict[str, Any]:
    target_column = config.task.target_column
    enabled_columns = [col for col in config.columns if col.enabled]
    feature_columns = [col.name for col in enabled_columns if col.role == "feature"]

    if target_column not in dataframe.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")
    if not feature_columns:
        raise ValueError("At least one feature column must be enabled.")

    X = dataframe[feature_columns].copy()
    y = dataframe[target_column].copy()

    numeric_columns = [col.name for col in enabled_columns if col.role == "feature" and col.data_type == "numeric"]
    categorical_columns = [
        col.name for col in enabled_columns if col.role == "feature" and col.data_type == "categorical"
    ]
    ordinal_columns = [col for col in enabled_columns if col.role == "feature" and col.data_type == "ordinal"]

    transformers = []
    if numeric_columns:
        transformers.append(
            ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_columns)
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical_columns,
            )
        )
    if ordinal_columns:
        transformers.append(
            (
                "ordinal",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OrdinalEncoder(
                                categories=[col.categories for col in ordinal_columns],
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                            ),
                        ),
                    ]
                ),
                [col.name for col in ordinal_columns],
            )
        )

    if not transformers:
        raise ValueError("No supported feature transformers could be built from the config.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=config.split.test_size,
        random_state=config.split.random_state,
        stratify=y if config.split.stratify else None,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", ColumnTransformer(transformers=transformers, remainder="drop")),
            (
                "model",
                DecisionTreeClassifier(
                    criterion=config.model.criterion,
                    splitter=config.model.splitter,
                    max_depth=config.model.max_depth,
                    min_samples_split=config.model.min_samples_split,
                    min_samples_leaf=config.model.min_samples_leaf,
                    random_state=config.model.random_state,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    labels = sorted([str(label) for label in y.dropna().unique().tolist()])
    matrix = confusion_matrix(y_test, predictions, labels=labels)
    precision, recall, f1_score, support = precision_recall_fscore_support(
        y_test,
        predictions,
        labels=labels,
        zero_division=0,
    )
    weighted_precision, weighted_recall, weighted_f1_score, _ = precision_recall_fscore_support(
        y_test,
        predictions,
        average="weighted",
        zero_division=0,
    )

    model = pipeline.named_steps["model"]
    preprocessor = pipeline.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out().tolist()
    importance_rows = [
        {"feature": feature_name, "importance": float(importance)}
        for feature_name, importance in zip(feature_names, model.feature_importances_, strict=False)
    ]
    tree_nodes = _extract_tree_nodes(model, labels, feature_names)

    class_metrics = []
    for label, prec, rec, f1_value, supp in zip(labels, precision, recall, f1_score, support, strict=False):
        class_metrics.append(
            {
                "class_label": label,
                "precision": float(prec),
                "recall": float(rec),
                "f1_score": float(f1_value),
                "support": int(supp),
            }
        )

    return {
        "dataset_split": {
            "training_rows": int(len(X_train)),
            "testing_rows": int(len(X_test)),
            "test_size": config.split.test_size,
            "stratified": config.split.stratify,
            "random_state": config.split.random_state,
        },
        "preprocessing_summary": {
            "target_column": target_column,
            "preprocessing_config": config.preprocessing.model_dump(),
            "numeric_features": numeric_columns,
            "categorical_features": categorical_columns,
            "ordinal_features": [col.name for col in ordinal_columns],
            "feature_count_before_encoding": len(feature_columns),
            "feature_count_after_encoding": len(feature_names),
            "transformed_feature_names": feature_names,
            "imputation": {
                "numeric": "median" if numeric_columns else None,
                "categorical": "most_frequent" if categorical_columns or ordinal_columns else None,
            },
            "encoding": {
                "categorical": "one_hot" if categorical_columns else None,
                "ordinal": "ordinal" if ordinal_columns else None,
            },
        },
        "confusion_matrix": {
            "labels": labels,
            "values": matrix.tolist(),
            "orientation": {"rows": "actual", "columns": "predicted"},
        },
        "metrics": {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision": float(weighted_precision),
            "recall": float(weighted_recall),
            "f1_score": float(weighted_f1_score),
        },
        "class_metrics": class_metrics,
        "classification_report": classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
        "feature_importance": importance_rows,
        "tree_visualization": {
            "nodes": tree_nodes,
            "edges": _build_tree_edges(tree_nodes),
            "root_node_id": 0,
        },
        "tree_rules_text": export_text(model, feature_names=feature_names),
    }


def _extract_tree_nodes(
    model: DecisionTreeClassifier,
    labels: list[str],
    feature_names: list[str],
) -> list[dict[str, Any]]:
    tree = model.tree_
    node_depths = tree.compute_node_depths()
    nodes: list[dict[str, Any]] = []

    for node_id in range(tree.node_count):
        left_child = int(tree.children_left[node_id])
        right_child = int(tree.children_right[node_id])
        is_leaf = left_child == right_child
        class_values = tree.value[node_id][0]
        class_counts = {
            label: int(class_values[index])
            for index, label in enumerate(labels)
        }
        predicted_class_index = int(class_values.argmax())

        node: dict[str, Any] = {
            "node_id": node_id,
            "depth": int(node_depths[node_id]),
            "is_leaf": is_leaf,
            "samples": int(tree.n_node_samples[node_id]),
            "weighted_samples": float(tree.weighted_n_node_samples[node_id]),
            "impurity": float(tree.impurity[node_id]),
            "predicted_class": labels[predicted_class_index],
            "class_counts": class_counts,
            "left_child_id": None if is_leaf else left_child,
            "right_child_id": None if is_leaf else right_child,
        }

        if not is_leaf:
            feature_index = int(tree.feature[node_id])
            node.update(
                {
                    "feature_name": feature_names[feature_index],
                    "operator": "<=",
                    "threshold": float(tree.threshold[node_id]),
                }
            )

        nodes.append(node)

    parent_by_child: dict[int, int] = {}
    for node in nodes:
        if node["left_child_id"] is not None:
            parent_by_child[node["left_child_id"]] = node["node_id"]
        if node["right_child_id"] is not None:
            parent_by_child[node["right_child_id"]] = node["node_id"]

    for node in nodes:
        node["parent_node_id"] = parent_by_child.get(node["node_id"])

    return nodes


def _build_tree_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for node in nodes:
        if node["left_child_id"] is not None:
            edges.append(
                {
                    "source": node["node_id"],
                    "target": node["left_child_id"],
                    "branch": "left",
                    "condition": "true",
                }
            )
        if node["right_child_id"] is not None:
            edges.append(
                {
                    "source": node["node_id"],
                    "target": node["right_child_id"],
                    "branch": "right",
                    "condition": "false",
                }
            )
    return edges
