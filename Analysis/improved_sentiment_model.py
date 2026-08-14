from pathlib import Path
import json
import re
import time
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    cross_validate,
    train_test_split,
)
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

warnings.filterwarnings("ignore", category=UserWarning)

RANDOM_STATE = 42
DATA_PATH = Path("data_03.csv")
OUTPUT_DIR = Path("model_output")
TEXT_COLUMN = "评论内容"
RATING_COLUMN = "评分"
MODEL_VERSION = "2.0.0"
MIN_REQUIRED_PRECISION = 0.25

INVALID_PATTERNS = [
    r"^\s*$",
    r"^此用户未.*填写评价内容[。！!]?$",
    r"^用户未填写评价内容[。！!]?$",
    r"^默认好评[。！!]?$",
    r"^系统默认好评[。！!]?$",
    r"^[\W_]+$",
]


def read_dataset(path):
    encodings = ["utf-8-sig", "utf-8", "gbk"]
    last_error = None

    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError(f"无法识别文件编码：{last_error}")


def normalize_text(text):
    if pd.isna(text):
        return ""

    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(.)\1{5,}", r"\1\1\1", text)
    return text


def is_invalid_text(text):
    normalized = normalize_text(text)
    return any(re.fullmatch(pattern, normalized) for pattern in INVALID_PATTERNS)


def prepare_dataset(dataframe):
    required_columns = {TEXT_COLUMN, RATING_COLUMN}
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(f"缺少必要字段：{sorted(missing_columns)}")

    data = dataframe.copy()
    data[RATING_COLUMN] = pd.to_numeric(data[RATING_COLUMN], errors="coerce")
    data["标准评论"] = data[TEXT_COLUMN].apply(normalize_text)
    data["无效文本"] = data[TEXT_COLUMN].apply(is_invalid_text)

    before_count = len(data)
    data = data.dropna(subset=[RATING_COLUMN])
    data = data[data[RATING_COLUMN].between(1, 5)]
    data = data[~data["无效文本"]]
    data = data.drop_duplicates(subset=["标准评论", RATING_COLUMN])
    data = data.reset_index(drop=True)

    data["风险标签"] = (data[RATING_COLUMN] <= 3).astype(int)
    removed_count = before_count - len(data)

    print(f"原始样本：{before_count}")
    print(f"有效样本：{len(data)}")
    print(f"删除无效、重复或评分异常样本：{removed_count}")
    print(data["风险标签"].value_counts().rename(index={0: "正常", 1: "风险"}))

    if data["风险标签"].value_counts().min() < 10:
        raise ValueError("风险样本少于10条，无法进行相对可靠的分层训练和评估")

    return data


def build_candidates():
    vectorizer = {
        "tfidf": TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            min_df=2,
            max_df=0.98,
            max_features=30000,
            sublinear_tf=True,
        )
    }

    return {
        "LogisticRegression": Pipeline([
            *vectorizer.items(),
            ("classifier", LogisticRegression(
                class_weight="balanced",
                C=2.0,
                max_iter=2000,
                random_state=RANDOM_STATE,
            )),
        ]),
        "ComplementNB": Pipeline([
            *vectorizer.items(),
            ("classifier", ComplementNB(alpha=0.5)),
        ]),
        "LinearSVC-Calibrated": Pipeline([
            *vectorizer.items(),
            ("classifier", CalibratedClassifierCV(
                estimator=LinearSVC(
                    class_weight="balanced",
                    C=1.0,
                    random_state=RANDOM_STATE,
                ),
                method="sigmoid",
                cv=3,
            )),
        ]),
    }


def compare_models(models, texts, labels):
    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    scoring = {
        "pr_auc": "average_precision",
        "risk_recall": "recall",
        "risk_precision": "precision",
        "macro_f1": "f1_macro",
    }
    rows = []

    for name, model in models.items():
        started_at = time.time()
        scores = cross_validate(
            model,
            texts,
            labels,
            cv=cv,
            scoring=scoring,
            n_jobs=-1,
            error_score="raise",
        )

        rows.append({
            "模型": name,
            "PR-AUC均值": scores["test_pr_auc"].mean(),
            "PR-AUC标准差": scores["test_pr_auc"].std(),
            "风险召回率均值": scores["test_risk_recall"].mean(),
            "风险精确率均值": scores["test_risk_precision"].mean(),
            "Macro-F1均值": scores["test_macro_f1"].mean(),
            "交叉验证耗时": time.time() - started_at,
        })

    results = pd.DataFrame(rows).sort_values(
        ["PR-AUC均值", "风险召回率均值"],
        ascending=False,
    ).reset_index(drop=True)
    return results, cv


def choose_threshold(labels, probabilities, min_precision):
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    candidates = []

    for index, threshold in enumerate(thresholds):
        if precision[index] >= min_precision:
            candidates.append((
                recall[index],
                precision[index],
                threshold,
            ))

    if candidates:
        recall_value, precision_value, threshold = max(
            candidates,
            key=lambda item: (item[0], item[1]),
        )
    else:
        f1_values = (
            2 * precision[:-1] * recall[:-1]
            / np.maximum(precision[:-1] + recall[:-1], 1e-12)
        )
        best_index = int(np.nanargmax(f1_values))
        threshold = thresholds[best_index]
        precision_value = precision[best_index]
        recall_value = recall[best_index]

    return float(threshold), float(precision_value), float(recall_value)


def evaluate(model, threshold, texts, labels):
    probabilities = model.predict_proba(texts)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    metrics = {
        "accuracy": accuracy_score(labels, predictions),
        "macro_f1": f1_score(labels, predictions, average="macro"),
        "risk_recall": recall_score(labels, predictions),
        "risk_precision": precision_score(labels, predictions, zero_division=0),
        "pr_auc": average_precision_score(labels, probabilities),
    }

    print("\n最终独立测试集指标")
    for name, value in metrics.items():
        print(f"{name}: {value:.4f}")

    print("\n分类报告")
    print(classification_report(
        labels,
        predictions,
        target_names=["正常评论", "风险评论"],
        digits=4,
        zero_division=0,
    ))

    matrix = confusion_matrix(labels, predictions)
    return metrics, matrix, probabilities, predictions


def save_confusion_matrix(matrix, output_path):
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["预测正常", "预测风险"],
        yticklabels=["实际正常", "实际风险"],
    )
    plt.title("改进模型：独立测试集混淆矩阵")
    plt.xlabel("预测标签")
    plt.ylabel("真实标签")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close()


def save_artifact(model, threshold, metrics, model_name, output_path):
    artifact = {
        "pipeline": model,
        "threshold": threshold,
        "model_name": model_name,
        "model_version": MODEL_VERSION,
        "positive_label": 1,
        "label_meaning": {
            0: "正常评论",
            1: "风险评论",
        },
        "task_definition": "预测评论是否对应1至3星低分风险，不等同于人工情感三分类",
        "invalid_patterns": INVALID_PATTERNS,
        "test_metrics": metrics,
    }
    joblib.dump(artifact, output_path)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_data = read_dataset(DATA_PATH)
    data = prepare_dataset(raw_data)

    development_data, test_data = train_test_split(
        data,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=data["风险标签"],
    )

    x_development = development_data["标准评论"]
    y_development = development_data["风险标签"]
    x_test = test_data["标准评论"]
    y_test = test_data["风险标签"]

    models = build_candidates()
    comparison, cv = compare_models(
        models,
        x_development,
        y_development,
    )
    comparison.to_csv(
        OUTPUT_DIR / "model_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print("\n交叉验证模型比较")
    print(comparison.round(4).to_string(index=False))

    best_model_name = comparison.iloc[0]["模型"]
    best_model = models[best_model_name]

    development_probabilities = cross_val_predict(
        best_model,
        x_development,
        y_development,
        cv=cv,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]

    threshold, validation_precision, validation_recall = choose_threshold(
        y_development,
        development_probabilities,
        MIN_REQUIRED_PRECISION,
    )

    print(f"\n选中模型：{best_model_name}")
    print(f"阈值：{threshold:.4f}")
    print(f"交叉验证阈值精确率：{validation_precision:.4f}")
    print(f"交叉验证阈值召回率：{validation_recall:.4f}")

    best_model.fit(x_development, y_development)
    metrics, matrix, probabilities, predictions = evaluate(
        best_model,
        threshold,
        x_test,
        y_test,
    )

    save_confusion_matrix(
        matrix,
        OUTPUT_DIR / "test_confusion_matrix.png",
    )
    save_artifact(
        best_model,
        threshold,
        metrics,
        best_model_name,
        OUTPUT_DIR / "sentiment_risk_model.joblib",
    )

    test_results = test_data.copy()
    test_results["风险概率"] = probabilities
    test_results["模型预测"] = predictions
    test_results["预测名称"] = test_results["模型预测"].map({
        0: "正常评论",
        1: "疑似风险，待复核",
    })
    test_results.to_excel(
        OUTPUT_DIR / "test_predictions.xlsx",
        index=False,
    )

    metadata = {
        "model_version": MODEL_VERSION,
        "model_name": best_model_name,
        "threshold": threshold,
        "development_samples": len(development_data),
        "test_samples": len(test_data),
        "risk_samples_in_test": int(y_test.sum()),
        "metrics": metrics,
    }
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n已生成")
    print(OUTPUT_DIR / "sentiment_risk_model.joblib")
    print(OUTPUT_DIR / "model_comparison.csv")
    print(OUTPUT_DIR / "test_predictions.xlsx")
    print(OUTPUT_DIR / "test_confusion_matrix.png")
    print(OUTPUT_DIR / "metadata.json")


if __name__ == "__main__":
    main()
