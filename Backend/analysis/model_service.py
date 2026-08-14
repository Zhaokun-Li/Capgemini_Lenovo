from pathlib import Path
from collections import Counter
import re

import joblib
import jieba
import jieba.analyse
import numpy as np
import pandas as pd
from scipy import sparse
from snownlp import SnowNLP

MODEL_PATH = Path(__file__).resolve().parent / "xgb_sentiment_bundle.joblib"
EXPECTED_BUNDLE_VERSION = "lenovo-opinion-xgb-v2"
_bundle = None

REQUIRED_COLUMNS = ["电脑配置", "评论内容", "有用数", "重复购买情况", "评分", "内存", "硬盘"]
STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "也", "很",
    "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "款", "自己", "这", "那", "里",
    "后", "么", "之", "过", "与", "她", "他", "它", "京东", "购物", "下单", "收到货", "快递", "物流",
    "包装", "客服", "售后", "价格", "笔记本", "电脑", "笔记本电脑", "感觉", "觉得", "认为", "总体",
    "目前", "暂时", "东西", "宝贝", "商品", "物品", "这个", "那个", "联想", "不错",
}

ISSUE_RULES = {
    "性能卡顿": ["卡顿", "很慢", "死机", "蓝屏", "掉帧", "延迟", "性能差", "不流畅"],
    "散热噪音": ["发热", "烫", "温度高", "风扇", "噪音", "异响", "散热"],
    "屏幕显示": ["黑屏", "花屏", "漏光", "坏点", "屏幕", "色差", "闪屏"],
    "续航电池": ["续航", "耗电", "电池", "掉电", "充电", "电量"],
    "质量故障": ["故障", "损坏", "开裂", "失灵", "坏了", "质量", "做工"],
    "售后服务": ["售后", "客服", "退货", "退款", "维修", "换货", "服务差"],
    "物流包装": ["物流", "快递", "配送", "包装", "破损", "到货"],
    "价格促销": ["价格", "降价", "优惠", "贵", "保价", "活动", "性价比低"],
    "系统软件": ["系统", "软件", "驱动", "更新", "兼容", "安装", "预装"],
}


def load_bundle():
    global _bundle
    if _bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"未找到新模型文件：{MODEL_PATH}")
        _bundle = joblib.load(MODEL_PATH)
        required = {
            "model", "tfidf_vectorizer", "product_encoder", "memory_encoder",
            "repurchase_encoder", "disk_mapping", "feature_columns",
        }
        missing = sorted(required - set(_bundle))
        if missing:
            raise ValueError("模型包不完整，缺少：" + "、".join(missing))
        if _bundle.get("bundle_version") != EXPECTED_BUNDLE_VERSION:
            raise ValueError(
                "当前不是新版网站模型包，请运行新 Notebook 最后的‘导出网站自动分析模型包’单元"
            )
    return _bundle


def extract_product_series(config):
    config = str(config)
    if "Y7000" in config:
        return "Y7000游戏本"
    if "R7000" in config:
        return "R7000游戏本"
    if "标压酷睿" in config or "酷睿版" in config:
        return "酷睿版"
    if "标压锐龙" in config or "锐龙版" in config:
        return "锐龙版"
    return "其他"


def clean_text(text):
    text = "" if pd.isna(text) else str(text).strip()
    return re.sub(r"\s+", " ", text)


def get_sentiment(text):
    try:
        return float(SnowNLP(text).sentiments)
    except Exception:
        return 0.5


def tokenize(text):
    return " ".join(word.strip() for word in jieba.lcut(text) if word.strip() and word.strip() not in STOPWORDS)


def safe_label_transform(encoder, series):
    classes = set(map(str, encoder.classes_))
    fallback = str(encoder.classes_[0])
    values = [str(value) if str(value) in classes else fallback for value in series.fillna(fallback)]
    return encoder.transform(values)


def preprocess_dataframe(raw_df):
    bundle = load_bundle()
    df = raw_df.copy()
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("导入文件缺少字段：" + "、".join(missing))

    df["评论内容"] = df["评论内容"].apply(clean_text)
    df = df[df["评论内容"] != ""].copy()
    df["评分"] = pd.to_numeric(df["评分"], errors="coerce")
    df["有用数"] = pd.to_numeric(df["有用数"], errors="coerce").fillna(0)
    date_source = "date" if "date" in df.columns else "评论日期" if "评论日期" in df.columns else None
    df["date"] = pd.to_datetime(df[date_source], errors="coerce") if date_source else pd.NaT
    if "产品系列" not in df.columns:
        df["产品系列"] = df["电脑配置"].apply(extract_product_series)
    df["内存"] = df["内存"].replace("UNK", "16G").fillna("16G").astype(str)
    df["硬盘"] = df["硬盘"].replace("UNK", "1T").fillna("1T").astype(str)
    df["重复购买情况"] = df["重复购买情况"].fillna("未知").astype(str)
    df["评论长度"] = df["评论内容"].str.len()
    df["情感分数"] = df["评论内容"].apply(get_sentiment)
    df["评论分词_去停用词"] = df["评论内容"].apply(tokenize)
    df["评论关键词"] = df["评论内容"].apply(
        lambda text: " ".join(jieba.analyse.extract_tags(text, topK=5, allowPOS=("n", "a")))
    )

    tfidf = bundle["tfidf_vectorizer"].transform(df["评论分词_去停用词"])
    product_encoder = bundle["product_encoder"]
    known_products = set(map(str, product_encoder.categories_[0]))
    fallback_product = str(product_encoder.categories_[0][0])
    product_values = df[["产品系列"]].astype(str)
    product_values["产品系列"] = product_values["产品系列"].apply(
        lambda value: value if value in known_products else fallback_product
    )
    product_ohe = product_encoder.transform(product_values)
    if sparse.issparse(product_ohe):
        product_ohe = product_ohe.toarray()
    memory_values = safe_label_transform(bundle["memory_encoder"], df["内存"]).reshape(-1, 1)
    repurchase_values = safe_label_transform(bundle["repurchase_encoder"], df["重复购买情况"]).reshape(-1, 1)
    disk_mapping = bundle["disk_mapping"]
    disk_values = df["硬盘"].map(disk_mapping).fillna(next(iter(disk_mapping.values()))).to_numpy().reshape(-1, 1)
    structured = np.hstack([
        product_ohe,
        memory_values,
        disk_values,
        repurchase_values,
        df[["评论长度", "情感分数"]].to_numpy(dtype=float),
    ])
    features = sparse.hstack([tfidf, sparse.csr_matrix(structured)]).tocsr()
    expected_features = len(bundle["feature_columns"])
    if features.shape[1] != expected_features:
        raise ValueError(f"模型特征数量不一致：当前 {features.shape[1]}，模型要求 {expected_features}")
    return df.reset_index(drop=True), features


def predict_dataframe(raw_df):
    bundle = load_bundle()
    df, features = preprocess_dataframe(raw_df)
    model = bundle["model"]
    prediction = model.predict(features, validate_features=False)
    probability_good = model.predict_proba(features, validate_features=False)[:, 1]
    df["模型预测值"] = prediction.astype(int)
    df["模型标签"] = np.where(prediction == 0, "差评", "好评")
    df["差评概率"] = (1 - probability_good).round(4)
    df["原始标签"] = np.where(df["评分"] <= 3, 0, 1)
    def detect_issue(text):
        content = str(text)
        matched = [name for name, words in ISSUE_RULES.items() if any(word in content for word in words)]
        return matched[0] if matched else "其他问题"

    df["问题类型"] = df["评论内容"].apply(detect_issue)
    df.loc[df["模型预测值"] == 1, "问题类型"] = "正常评价"
    df["高分低评"] = ((df["原始标签"] == 1) & (df["模型预测值"] == 0)).astype(int)
    df["风险等级"] = pd.cut(df["差评概率"], bins=[-0.01, 0.35, 0.65, 1.0], labels=["低风险", "中风险", "高风险"]).astype(str)
    return df


def build_analysis(df):
    total = int(len(df))
    negative_count = int((df["模型标签"] == "差评").sum())
    positive_count = int((df["模型标签"] == "好评").sum())
    high_risk_count = int((df["风险等级"] == "高风险").sum())
    hidden_negative_count = int(df.get("高分低评", pd.Series(dtype=int)).sum())

    overview = {
        "total": total,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "negative_rate": round(negative_count / total * 100, 2) if total else 0,
        "average_rating": round(float(df["评分"].mean()), 2) if total else 0,
        "high_risk_count": high_risk_count,
        "hidden_negative_count": hidden_negative_count,
    }

    sentiment = (
        df["模型标签"]
        .value_counts()
        .rename_axis("label")
        .reset_index(name="value")
        .to_dict("records")
    )

    rating_distribution = [
        {"rating": rating, "count": int((df["评分"] == rating).sum())}
        for rating in range(1, 6)
    ]

    product = (
        df.groupby("产品系列", observed=False)
        .agg(
            评论数=("评论内容", "size"),
            平均评分=("评分", "mean"),
            模型差评数=("模型标签", lambda values: (values == "差评").sum()),
        )
        .reset_index()
    )
    product["差评率"] = (product["模型差评数"] / product["评论数"] * 100).round(2)
    product["平均评分"] = product["平均评分"].round(2)

    product_rating = (
        df.assign(评分=df["评分"].round().clip(1, 5))
        .groupby(["产品系列", "评分"], observed=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[1, 2, 3, 4, 5], fill_value=0)
    )
    product_rating_distribution = [
        {
            "product_series": str(index),
            **{f"rating_{rating}": int(row.get(rating, 0)) for rating in range(1, 6)},
        }
        for index, row in product_rating.iterrows()
    ]

    memory = (
        df.groupby("内存", observed=False)
        .agg(
            评论数=("评论内容", "size"),
            模型差评数=("模型标签", lambda values: (values == "差评").sum()),
        )
        .reset_index()
    )
    memory["差评率"] = (memory["模型差评数"] / memory["评论数"] * 100).round(2)

    storage = (
        df.groupby("硬盘", observed=False)
        .agg(
            评论数=("评论内容", "size"),
            模型差评数=("模型标签", lambda values: (values == "差评").sum()),
        )
        .reset_index()
    )
    storage["差评率"] = (storage["模型差评数"] / storage["评论数"] * 100).round(2)

    valid_dates = df.dropna(subset=["date"]).copy()
    if valid_dates.empty:
        trend = []
    else:
        valid_dates["月份"] = valid_dates["date"].dt.to_period("M").astype(str)
        trend_df = (
            valid_dates.groupby("月份")
            .agg(
                评论数=("评论内容", "size"),
                差评数=("模型标签", lambda values: (values == "差评").sum()),
                平均评分=("评分", "mean"),
            )
            .reset_index()
        )
        trend_df["差评率"] = (trend_df["差评数"] / trend_df["评论数"] * 100).round(2)
        trend_df["平均评分"] = trend_df["平均评分"].round(2)
        trend = trend_df.to_dict("records")

    def collect_keywords(label):
        words = []
        for text in df.loc[df["模型标签"] == label, "评论分词_去停用词"].dropna():
            words.extend(word for word in str(text).split() if len(word) > 1)
        return [{"word": word, "count": count} for word, count in Counter(words).most_common(10)]

    positive_keywords = collect_keywords("好评")
    negative_keywords = collect_keywords("差评")

    negative_df = df[df["模型标签"] == "差评"].copy()
    issues = (
        negative_df["问题类型"]
        .value_counts()
        .rename_axis("name")
        .reset_index(name="count")
        .head(10)
    )

    issue_by_product_df = (
        negative_df.groupby(["产品系列", "问题类型"], observed=False)
        .size()
        .reset_index(name="count")
    )
    issue_by_product = issue_by_product_df.to_dict("records")

    confusion = {
        "tn": int(((df["原始标签"] == 0) & (df["模型预测值"] == 0)).sum()),
        "fp": int(((df["原始标签"] == 0) & (df["模型预测值"] == 1)).sum()),
        "fn": int(((df["原始标签"] == 1) & (df["模型预测值"] == 0)).sum()),
        "tp": int(((df["原始标签"] == 1) & (df["模型预测值"] == 1)).sum()),
    }
    confusion["accuracy"] = round(
        (confusion["tn"] + confusion["tp"]) / total * 100, 2
    ) if total else 0

    risks = (
        df[df["模型标签"] == "差评"]
        .sort_values(["差评概率", "有用数"], ascending=[False, False])
        .head(50)[
            [
                "评论内容", "评分", "产品系列", "内存", "硬盘", "差评概率",
                "风险等级", "问题类型", "评论关键词",
            ]
        ]
        .fillna("")
        .to_dict("records")
    )

    return {
        "overview": overview,
        "sentiment": sentiment,
        "rating_distribution": rating_distribution,
        "product": product.to_dict("records"),
        "product_rating_distribution": product_rating_distribution,
        "memory": memory.to_dict("records"),
        "storage": storage.to_dict("records"),
        "trend": trend,
        "positive_keywords": positive_keywords,
        "negative_keywords": negative_keywords,
        "issues": issues.to_dict("records"),
        "issue_by_product": issue_by_product,
        "confusion_matrix": confusion,
        "risks": risks,
    }