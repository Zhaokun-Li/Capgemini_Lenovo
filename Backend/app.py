import os
import json
import threading
import re
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import Counter
from urllib.parse import quote_plus
from sqlalchemy import func, case

import certifi
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import LONGTEXT

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)

CORS(app)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "https://capgemini-lenovo-two.vercel.app"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "4000"))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "lenovo_insight")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{MYSQL_USER}:"
    f"{quote_plus(MYSQL_PASSWORD)}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/"
    f"{MYSQL_DATABASE}?charset=utf8mb4"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "connect_args": {
        "ssl": {
            "ca": certifi.where()
        }
    }
}

db = SQLAlchemy(app)

class ProductReview(db.Model):
    __tablename__ = "product_review"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    data_index = db.Column(
        db.BigInteger,
        unique=True,
        nullable=False,
        index=True
    )

    username = db.Column(
        db.String(100)
    )

    computer_config = db.Column(
        db.String(500)
    )

    review_content = db.Column(
        LONGTEXT,
        nullable=False
    )

    helpful_count = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    repeat_purchase = db.Column(
        db.String(20)
    )

    rating = db.Column(
        db.Numeric(3, 1)
    )

    memory = db.Column(
        db.String(50)
    )

    disk = db.Column(
        db.String(50)
    )

    review_date = db.Column(
        db.Date,
        index=True
    )

    product_series = db.Column(
        db.String(100),
        index=True
    )

    review_length = db.Column(
        db.Integer
    )

    review_month = db.Column(
        db.String(30)
    )

    tokenized_content = db.Column(
        LONGTEXT
    )

    filtered_content = db.Column(
        LONGTEXT
    )

    sentiment_score = db.Column(
        db.Float
    )

    keywords = db.Column(
        db.Text
    )

    sentiment_label = db.Column(
        db.String(20),
        index=True
    )

    model_prediction = db.Column(db.Integer)
    model_label = db.Column(db.String(20), index=True)
    negative_probability = db.Column(db.Float)
    original_label = db.Column(db.String(20))
    issue_type = db.Column(db.String(100), index=True)
    risk_level = db.Column(db.String(20), index=True)

    tfidf_vector = db.Column(
        LONGTEXT
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now,
        nullable=False
    )

    def to_dict(
        self,
        include_analysis=False
    ):
        result = {
            "id": self.id,
            "data_index": self.data_index,
            "username": self.username,
            "computer_config":
                self.computer_config,
            "review_content":
                self.review_content,
            "helpful_count":
                self.helpful_count,
            "repeat_purchase":
                self.repeat_purchase,
            "rating": (
                float(self.rating)
                if self.rating is not None
                else None
            ),
            "memory": self.memory,
            "disk": self.disk,
            "review_date": (
                self.review_date.isoformat()
                if self.review_date
                else None
            ),
            "product_series":
                self.product_series,
            "review_length":
                self.review_length,
            "review_month":
                self.review_month,
            "sentiment_score":
                self.sentiment_score,
            "keywords": self.keywords,
            "sentiment_label":
                self.sentiment_label,
            "model_prediction": self.model_prediction,
            "model_label": self.model_label,
            "negative_probability": self.negative_probability,
            "original_label": self.original_label,
            "issue_type": self.issue_type,
            "risk_level": self.risk_level,
        }

        if include_analysis:
            result.update(
                {
                    "tokenized_content":
                        self.tokenized_content,
                    "filtered_content":
                        self.filtered_content,
                    "tfidf_vector":
                        self.tfidf_vector,
                }
            )

        return result


ANALYSIS_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "analysis",
    "analysis_cache.json",
)
_analysis_cache_lock = threading.RLock()
_analysis_cache = None


def empty_analysis():
    return {
        "overview": {
            "total": 0,
            "positive_count": 0,
            "negative_count": 0,
            "negative_rate": 0,
            "average_rating": 0,
            "high_risk_count": 0,
            "hidden_negative_count": 0,
        },
        "sentiment": [],
        "rating_distribution": [
            {"rating": rating, "count": 0}
            for rating in range(1, 6)
        ],
        "product": [],
        "product_rating_distribution": [],
        "memory": [],
        "storage": [],
        "trend": [],
        "positive_keywords": [],
        "negative_keywords": [],
        "issues": [],
        "issue_by_product": [],
        "confusion_matrix": {
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
            "accuracy": 0,
        },
        "risks": [],
        "trend_dashboard": {
            "summary": {},
            "sentiment": [],
            "trend": [],
            "products": [],
            "issues": [],
            "risk_trend": [],
            "product_negative": [],
            "rating_alignment": [],
            "hot_reviews": [],
        },
    }


def database_dataframe():
    rows = ProductReview.query.order_by(ProductReview.id.asc()).all()
    return rows, pd.DataFrame([
        {
            "data_index": row.data_index,
            "用户名": row.username or "",
            "电脑配置": row.computer_config or "",
            "评论内容": row.review_content or "",
            "有用数": row.helpful_count or 0,
            "重复购买情况": row.repeat_purchase or "否",
            "评分": float(row.rating) if row.rating is not None else 0,
            "内存": row.memory or "未知",
            "硬盘": row.disk or "未知",
            "date": row.review_date,
            "产品系列": row.product_series or "其他",
            "评论长度": row.review_length or 0,
            "月份": row.review_month or "",
            "评论分词": row.tokenized_content or "",
            "评论分词_去停用词": row.filtered_content or "",
            "情感分数": row.sentiment_score,
            "评论关键词": row.keywords or "",
            "情感标签": row.sentiment_label or "",
            "TFIDF向量": row.tfidf_vector or "",
        }
        for row in rows
    ])


def build_trend_dashboard(data):
    if data.empty:
        return empty_analysis()["trend_dashboard"]
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["sentiment"] = frame["模型标签"].map({"好评": "正面", "差评": "负面"}).fillna("中性")
    valid = frame.dropna(subset=["date"]).copy()
    daily = []
    if not valid.empty:
        daily_frame = (
            valid.assign(day=valid["date"].dt.strftime("%Y-%m-%d"))
            .groupby(["day", "sentiment"], observed=False)
            .size()
            .unstack(fill_value=0)
        )
        daily = [
            {
                "date": str(index),
                "positive": int(row.get("正面", 0)),
                "neutral": int(row.get("中性", 0)),
                "negative": int(row.get("负面", 0)),
            }
            for index, row in daily_frame.iterrows()
        ]
    sentiment_counts = frame["sentiment"].value_counts()
    total = int(len(frame))
    sentiment = [
        {
            "label": label,
            "count": int(count),
            "percentage": round(int(count) * 100 / total, 2) if total else 0,
        }
        for label, count in sentiment_counts.items()
    ]
    products = []
    for name, group in frame.groupby("产品系列", observed=False):
        products.append({
            "name": str(name),
            "mentions": int(len(group)),
            "positive": int((group["sentiment"] == "正面").sum()),
            "negative": int((group["sentiment"] == "负面").sum()),
        })
    products.sort(key=lambda item: item["mentions"], reverse=True)
    issues = (
        frame.loc[frame["模型标签"] == "差评", "问题类型"]
        .value_counts()
        .rename_axis("name")
        .reset_index(name="count")
        .to_dict("records")
    )
    risk_trend = []
    if not valid.empty:
        risk_frame = (
            valid.assign(month=valid["date"].dt.strftime("%Y-%m"))
            .groupby(["month", "风险等级"], observed=False)
            .size()
            .unstack(fill_value=0)
        )
        risk_trend = [
            {
                "month": str(index),
                "high": int(row.get("高风险", 0)),
                "medium": int(row.get("中风险", 0)),
                "low": int(row.get("低风险", 0)),
            }
            for index, row in risk_frame.iterrows()
        ]
    product_negative = [
        {
            "name": item["name"],
            "negative_rate": round(item["negative"] * 100 / item["mentions"], 2)
            if item["mentions"] else 0,
        }
        for item in products
    ]
    alignment = [
        {
            "name": name,
            "count": int(count),
        }
        for name, count in {
            "高分好评": ((frame["评分"] >= 4) & (frame["模型标签"] == "好评")).sum(),
            "高分差评": ((frame["评分"] >= 4) & (frame["模型标签"] == "差评")).sum(),
            "低分差评": ((frame["评分"] < 4) & (frame["模型标签"] == "差评")).sum(),
            "低分好评": ((frame["评分"] < 4) & (frame["模型标签"] == "好评")).sum(),
        }.items()
    ]
    hot_reviews = (
        frame.sort_values(["差评概率", "有用数"], ascending=[False, False])
        .head(10)[["评论内容", "评分", "产品系列", "差评概率", "风险等级", "问题类型"]]
        .fillna("")
        .to_dict("records")
    )
    return {
        "summary": {"total": total, "period_total": total},
        "sentiment": sentiment,
        "trend": daily,
        "products": products[:8],
        "issues": issues,
        "risk_trend": risk_trend,
        "product_negative": product_negative[:8],
        "rating_alignment": alignment,
        "hot_reviews": hot_reviews,
    }


def save_analysis_cache(analysis, row_count):
    global _analysis_cache
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "row_count": row_count,
        "data": analysis,
    }
    os.makedirs(os.path.dirname(ANALYSIS_CACHE_PATH), exist_ok=True)
    temporary_path = f"{ANALYSIS_CACHE_PATH}.tmp"

    def json_default(value):
        if hasattr(value, "item"):
            return value.item()
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        raise TypeError(f"无法写入缓存的数据类型：{type(value).__name__}")

    with open(temporary_path, "w", encoding="utf-8") as cache_file:
        json.dump(payload, cache_file, ensure_ascii=False, allow_nan=False, default=json_default)
    os.replace(temporary_path, ANALYSIS_CACHE_PATH)
    _analysis_cache = payload
    return payload


def refresh_analysis_cache():
    with _analysis_cache_lock:
        rows, raw_data = database_dataframe()
        analysis = empty_analysis()
        if rows:
            predicted = predict_dataframe(raw_data)
            analysis = build_analysis(predicted)
            analysis["trend_dashboard"] = build_trend_dashboard(predicted)
        return save_analysis_cache(analysis, len(rows))


def refresh_analysis_cache_safely():
    try:
        refresh_analysis_cache()
        return True
    except Exception:
        app.logger.exception("重新生成舆情统计缓存失败")
        try:
            row_count = db.session.query(ProductReview.id).count()
            save_analysis_cache(empty_analysis(), row_count)
        except Exception:
            app.logger.exception("清除失效舆情缓存失败")
        return False


def load_analysis_cache():
    global _analysis_cache
    with _analysis_cache_lock:
        if _analysis_cache is not None:
            return _analysis_cache
        try:
            with open(ANALYSIS_CACHE_PATH, "r", encoding="utf-8") as cache_file:
                _analysis_cache = json.load(cache_file)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            _analysis_cache = {
                "generated_at": None,
                "row_count": 0,
                "data": empty_analysis(),
            }
        return _analysis_cache


@app.get("/api/analysis/latest")
def get_database_analysis():
    cached = load_analysis_cache()
    return jsonify({
        "success": True,
        "message": f"已读取缓存中的 {cached.get('row_count', 0)} 条评论统计",
        "generated_at": cached.get("generated_at"),
        "row_count": cached.get("row_count", 0),
        "data": cached.get("data") or empty_analysis(),
    })


def positive_int(
    name,
    default,
    maximum=None
):
    try:
        value = int(
            request.args.get(
                name,
                default
            )
        )

    except (TypeError, ValueError):
        value = default

    value = max(1, value)

    return (
        min(value, maximum)
        if maximum
        else value
    )


def parse_date(value):
    if not value:
        return None

    return date.fromisoformat(value)


def apply_review_filters(query):
    keyword = request.args.get(
        "keyword",
        ""
    ).strip()

    sentiment = request.args.get(
        "sentiment",
        ""
    ).strip()

    product_series = request.args.get(
        "product_series",
        ""
    ).strip()

    memory = request.args.get(
        "memory",
        ""
    ).strip()

    disk = request.args.get(
        "disk",
        ""
    ).strip()

    risk_level = request.args.get("risk_level", "").strip()
    issue_type = request.args.get("issue_type", "").strip()

    min_rating = request.args.get(
        "min_rating",
        ""
    ).strip()

    start_date = parse_date(
        request.args.get(
            "start_date",
            ""
        ).strip()
    )

    end_date = parse_date(
        request.args.get(
            "end_date",
            ""
        ).strip()
    )

    if keyword:
        like_keyword = f"%{keyword}%"

        query = query.filter(
            or_(
                ProductReview
                .review_content
                .like(like_keyword),

                ProductReview
                .keywords
                .like(like_keyword),

                ProductReview
                .computer_config
                .like(like_keyword),

                ProductReview
                .username
                .like(like_keyword),

                ProductReview
                .product_series
                .like(like_keyword)
            )
        )

    if sentiment:
        query = query.filter(
            ProductReview.sentiment_label
            == sentiment
        )

    if product_series:
        query = query.filter(
            ProductReview.product_series
            == product_series
        )

    if memory:
        query = query.filter(
            ProductReview.memory == memory
        )

    if disk:
        query = query.filter(
            ProductReview.disk == disk
        )

    if risk_level:
        query = query.filter(ProductReview.risk_level == risk_level)

    if issue_type:
        query = query.filter(ProductReview.issue_type == issue_type)

    if min_rating:
        query = query.filter(
            ProductReview.rating
            >= float(min_rating)
        )

    if start_date:
        query = query.filter(
            ProductReview.review_date
            >= start_date
        )

    if end_date:
        query = query.filter(
            ProductReview.review_date
            <= end_date
        )

    return query


@app.get("/")
def home():
    return jsonify(
        {
            "code": 200,
            "message": "Flask 后端正在运行"
        }
    )


@app.get("/api/test")
def test_database():
    try:
        db.session.execute(
            text("SELECT 1")
        )

        return jsonify(
            {
                "code": 200,
                "message":
                    "Flask 已成功连接 MySQL 数据库"
            }
        )

    except Exception as error:
        return jsonify(
            {
                "code": 500,
                "message": "数据库连接失败",
                "error": str(error)
            }
        ), 500


@app.get("/api/reviews")
def get_reviews():
    try:
        page = positive_int(
            "page",
            1
        )

        page_size = positive_int(
            "page_size",
            20,
            100
        )

        include_analysis = (
            request.args.get(
                "include_analysis",
                "false"
            ).lower() == "true"
        )

        query = apply_review_filters(
            ProductReview.query
        )

        sort_fields = {
            "date":
                ProductReview.review_date,
            "rating":
                ProductReview.rating,
            "helpful":
                ProductReview.helpful_count,
            "sentiment_score":
                ProductReview.sentiment_score,
            "negative_probability":
                ProductReview.negative_probability,
            "id":
                ProductReview.id,
        }

        sort_by = request.args.get(
            "sort_by",
            "date"
        )

        sort_order = request.args.get(
            "sort_order",
            "desc"
        ).lower()

        sort_column = sort_fields.get(
            sort_by,
            ProductReview.review_date
        )

        order_expression = (
            sort_column.asc()
            if sort_order == "asc"
            else sort_column.desc()
        )

        pagination = query.order_by(
            order_expression,
            ProductReview.id.desc()
        ).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )

        return jsonify(
            {
                "code": 200,
                "message": "查询成功",
                "data": [
                    review.to_dict(
                        include_analysis
                    )
                    for review
                    in pagination.items
                ],
                "pagination": {
                    "page":
                        pagination.page,
                    "page_size":
                        pagination.per_page,
                    "total":
                        pagination.total,
                    "pages":
                        pagination.pages,
                    "has_next":
                        pagination.has_next,
                    "has_prev":
                        pagination.has_prev,
                },
            }
        )

    except ValueError as error:
        return jsonify(
            {
                "code": 400,
                "message":
                    f"查询参数错误：{error}"
            }
        ), 400

    except Exception as error:
        app.logger.exception(
            "查询评论失败"
        )

        return jsonify(
            {
                "code": 500,
                "message": "查询评论失败",
                "error": str(error)
            }
        ), 500


@app.get("/api/reviews/options")
def get_review_options():
    try:
        def distinct_values(column):
            rows = (
                db.session.query(column)
                .filter(
                    column.isnot(None),
                    column != ""
                )
                .distinct()
                .order_by(column)
                .all()
            )

            return [
                row[0]
                for row in rows
            ]

        return jsonify(
            {
                "code": 200,
                "data": {
                    "sentiments":
                        distinct_values(
                            ProductReview
                            .sentiment_label
                        ),
                        "product_series":
                            distinct_values(
                                ProductReview
                                .product_series
                            ),
                        "memory":
                            distinct_values(
                                ProductReview.memory
                            ),
                        "disk":
                            distinct_values(
                                ProductReview.disk
                            ),
                        "risk_levels": distinct_values(ProductReview.risk_level),
                        "issue_types": distinct_values(ProductReview.issue_type),
                    },
                }
            )

    except Exception as error:
            app.logger.exception(
                "查询筛选项失败"
            )

            return jsonify(
                {
                    "code": 500,
                    "message": "筛选项查询失败",
                    "error": str(error),
                }
            ), 500


@app.get("/api/reviews/filter-statistics")
def get_filter_statistics():
    try:
        filtered_query = apply_review_filters(
            db.session.query(ProductReview)
        )

        filtered_subquery = (
            filtered_query
            .with_entities(
                ProductReview.id.label("id"),
                ProductReview.rating.label(
                    "rating"
                ),
                ProductReview.helpful_count.label(
                    "helpful_count"
                ),
                ProductReview.review_length.label(
                    "review_length"
                ),
                ProductReview.sentiment_score.label(
                    "sentiment_score"
                ),
                ProductReview.sentiment_label.label(
                    "sentiment_label"
                ),
                ProductReview.review_date.label(
                    "review_date"
                ),
            )
            .subquery()
        )

        (
            total,
            average_rating,
            helpful_total,
            average_length,
            average_sentiment_score,
            earliest_date,
            latest_date,
        ) = (
            db.session.query(
                func.count(
                    filtered_subquery.c.id
                ),
                func.avg(
                    filtered_subquery.c.rating
                ),
                func.sum(
                    filtered_subquery
                    .c.helpful_count
                ),
                func.avg(
                    filtered_subquery
                    .c.review_length
                ),
                func.avg(
                    filtered_subquery
                    .c.sentiment_score
                ),
                func.min(
                    filtered_subquery
                    .c.review_date
                ),
                func.max(
                    filtered_subquery
                    .c.review_date
                ),
            ).one()
        )

        sentiment_rows = (
            db.session.query(
                filtered_subquery
                .c.sentiment_label,
                func.count(
                    filtered_subquery.c.id
                ),
            )
            .filter(
                filtered_subquery
                .c.sentiment_label
                .isnot(None),
                filtered_subquery
                .c.sentiment_label != "",
            )
            .group_by(
                filtered_subquery
                .c.sentiment_label
            )
            .all()
        )

        sentiment_counts = {
            label: int(count)
            for label, count
            in sentiment_rows
        }

        total = int(total or 0)

        positive_count = (
            sentiment_counts.get(
                "正面",
                0
            )
        )

        neutral_count = (
            sentiment_counts.get(
                "中性",
                0
            )
        )

        negative_count = (
            sentiment_counts.get(
                "负面",
                0
            )
        )

        return jsonify(
            {
                "code": 200,
                "message": "筛选统计查询成功",
                "data": {
                    "total": total,
                    "average_rating": round(
                        float(
                            average_rating or 0
                        ),
                        2
                    ),
                    "helpful_total": int(
                        helpful_total or 0
                    ),
                    "average_length": round(
                        float(
                            average_length or 0
                        ),
                        1
                    ),
                    "average_sentiment_score":
                        round(
                            float(
                                average_sentiment_score
                                or 0
                            ),
                            4
                        ),
                    "positive_count":
                        positive_count,
                    "neutral_count":
                        neutral_count,
                    "negative_count":
                        negative_count,
                    "positive_rate": (
                        round(
                            positive_count
                            * 100
                            / total,
                            1
                        )
                        if total
                        else 0
                    ),
                    "neutral_rate": (
                        round(
                            neutral_count
                            * 100
                            / total,
                            1
                        )
                        if total
                        else 0
                    ),
                    "negative_rate": (
                        round(
                            negative_count
                            * 100
                            / total,
                            1
                        )
                        if total
                        else 0
                    ),
                    "earliest_date": (
                        earliest_date.isoformat()
                        if earliest_date
                        else None
                    ),
                    "latest_date": (
                        latest_date.isoformat()
                        if latest_date
                        else None
                    ),
                },
            }
        )

    except ValueError as error:
        return jsonify(
            {
                "code": 400,
                "message":
                    f"查询参数错误：{error}",
            }
        ), 400

    except Exception as error:
        app.logger.exception(
            "查询筛选统计失败"
        )

        return jsonify(
            {
                "code": 500,
                "message":
                    "查询筛选统计失败",
                "error": str(error),
            }
        ), 500


@app.get("/api/reviews/dashboard")
def get_review_dashboard():
    cached = load_analysis_cache()
    trend_data = (cached.get("data") or {}).get("trend_dashboard") or empty_analysis()["trend_dashboard"]
    return jsonify({
        "code": 200,
        "message": "趋势缓存读取成功",
        "generated_at": cached.get("generated_at"),
        "data": trend_data,
    })

    try:
        days = positive_int(
            "days",
            7,
            90
        )

        latest_date = (
            db.session.query(
                func.max(
                    ProductReview.review_date
                )
            ).scalar()
        )

        if latest_date is None:
            return jsonify(
                {
                    "code": 200,
                    "message": "暂无看板数据",
                    "data": {
                        "latest_date": None,
                        "period": {
                            "days": days,
                            "start": None,
                            "end": None,
                        },
                        "summary": {
                            "total": 0,
                            "period_total": 0,
                            "period_change": 0,
                            "positive_count": 0,
                            "positive_rate": 0,
                            "latest_count": 0,
                            "latest_change": 0,
                            "negative_count": 0,
                            "period_negative": 0,
                            "negative_change": 0,
                        },
                        "sentiment": [],
                        "trend": [],
                        "products": [],
                        "alerts": [],
                    },
                }
            )

        period_start = (
            latest_date
            - timedelta(
                days=days - 1
            )
        )

        previous_end = (
            period_start
            - timedelta(days=1)
        )

        previous_start = (
            previous_end
            - timedelta(
                days=days - 1
            )
        )

        previous_day = (
            latest_date
            - timedelta(days=1)
        )

        def count_between(
            start_date,
            end_date,
            sentiment_label=None
        ):
            query = db.session.query(
                func.count(
                    ProductReview.id
                )
            ).filter(
                ProductReview.review_date
                >= start_date,
                ProductReview.review_date
                <= end_date
            )

            if sentiment_label:
                query = query.filter(
                    ProductReview
                    .sentiment_label
                    == sentiment_label
                )

            return int(
                query.scalar() or 0
            )

        def change_rate(
            current_value,
            previous_value
        ):
            if previous_value == 0:
                return (
                    100.0
                    if current_value > 0
                    else 0.0
                )

            return round(
                (
                    current_value
                    - previous_value
                )
                * 100
                / previous_value,
                1
            )

        total = int(
            db.session.query(
                func.count(
                    ProductReview.id
                )
            ).scalar() or 0
        )

        positive_count = int(
            db.session.query(
                func.count(
                    ProductReview.id
                )
            )
            .filter(
                ProductReview.sentiment_label
                == "正面"
            )
            .scalar() or 0
        )

        negative_count = int(
            db.session.query(
                func.count(
                    ProductReview.id
                )
            )
            .filter(
                ProductReview.sentiment_label
                == "负面"
            )
            .scalar() or 0
        )

        current_total = count_between(
            period_start,
            latest_date
        )

        previous_total = count_between(
            previous_start,
            previous_end
        )

        current_negative = count_between(
            period_start,
            latest_date,
            "负面"
        )

        previous_negative = count_between(
            previous_start,
            previous_end,
            "负面"
        )

        latest_count = count_between(
            latest_date,
            latest_date
        )

        previous_day_count = count_between(
            previous_day,
            previous_day
        )

        sentiment_rows = (
            db.session.query(
                ProductReview.sentiment_label,
                func.count(
                    ProductReview.id
                )
            )
            .filter(
                ProductReview
                .sentiment_label
                .isnot(None),
                ProductReview
                .sentiment_label != ""
            )
            .group_by(
                ProductReview.sentiment_label
            )
            .all()
        )

        sentiment_counts = {
            label: int(count)
            for label, count
            in sentiment_rows
        }

        date_rows = (
            db.session.query(
                ProductReview.review_date,
                func.sum(
                    case(
                        (
                            ProductReview
                            .sentiment_label
                            == "正面",
                            1
                        ),
                        else_=0
                    )
                ),
                func.sum(
                    case(
                        (
                            ProductReview
                            .sentiment_label
                            == "中性",
                            1
                        ),
                        else_=0
                    )
                ),
                func.sum(
                    case(
                        (
                            ProductReview
                            .sentiment_label
                            == "负面",
                            1
                        ),
                        else_=0
                    )
                ),
            )
            .filter(
                ProductReview.review_date
                >= period_start,
                ProductReview.review_date
                <= latest_date
            )
            .group_by(
                ProductReview.review_date
            )
            .order_by(
                ProductReview.review_date
            )
            .all()
        )

        trend_map = {
            row[0]: {
                "date":
                    row[0].isoformat(),
                "positive":
                    int(row[1] or 0),
                "neutral":
                    int(row[2] or 0),
                "negative":
                    int(row[3] or 0),
            }
            for row in date_rows
        }

        trend = []

        for offset in range(days):
            current_date = (
                period_start
                + timedelta(days=offset)
            )

            trend.append(
                trend_map.get(
                    current_date,
                    {
                        "date":
                            current_date
                            .isoformat(),
                        "positive": 0,
                        "neutral": 0,
                        "negative": 0,
                    },
                )
            )
            product_rows = (
                db.session.query(
                    ProductReview.product_series,
                    func.count(
                        ProductReview.id
                    ).label("mentions"),
                    func.sum(
                        case(
                            (
                                ProductReview
                                .sentiment_label
                                == "正面",
                                1
                            ),
                            else_=0
                        )
                    ).label("positive"),
                    func.sum(
                        case(
                            (
                                ProductReview
                                .review_date
                                .between(
                                    period_start,
                                    latest_date
                                ),
                                1
                            ),
                            else_=0
                        )
                    ).label("current_count"),
                    func.sum(
                        case(
                            (
                                ProductReview
                                .review_date
                                .between(
                                    previous_start,
                                    previous_end
                                ),
                                1
                            ),
                            else_=0
                        )
                    ).label("previous_count"),
                )
                .filter(
                    ProductReview
                    .product_series
                    .isnot(None),
                    ProductReview
                    .product_series != ""
                )
                .group_by(
                    ProductReview.product_series
                )
                .order_by(
                    func.count(
                        ProductReview.id
                    ).desc()
                )
                .limit(6)
                .all()
            )

            products = []

            for row in product_rows:
                mentions = int(
                    row.mentions or 0
                )

                positive_rate = (
                    round(
                        int(row.positive or 0)
                        * 100
                        / mentions,
                        1
                    )
                    if mentions
                    else 0
                )

                trend_rate = change_rate(
                    int(
                        row.current_count or 0
                    ),
                    int(
                        row.previous_count or 0
                    )
                )

                if positive_rate >= 80:
                    status = "口碑优秀"

                elif positive_rate >= 60:
                    status = "表现稳定"

                else:
                    status = "需要关注"

                products.append(
                    {
                        "name":
                            row.product_series,
                        "category":
                            "产品系列",
                        "mentions":
                            mentions,
                        "sentiment":
                            positive_rate,
                        "trend":
                            trend_rate,
                        "status":
                            status,
                    }
                )

            alert_rows = (
                db.session.query(
                    ProductReview.product_series,
                    func.count(
                        ProductReview.id
                    ).label(
                        "negative_count"
                    ),
                    func.avg(
                        ProductReview
                        .sentiment_score
                    ).label("score"),
                )
                .filter(
                    ProductReview.sentiment_label
                    == "负面",
                    ProductReview.review_date
                    >= period_start,
                    ProductReview.review_date
                    <= latest_date,
                    ProductReview
                    .product_series
                    .isnot(None),
                    ProductReview
                    .product_series != ""
                )
                .group_by(
                    ProductReview.product_series
                )
                .order_by(
                    func.count(
                        ProductReview.id
                    ).desc()
                )
                .limit(3)
                .all()
            )

            alerts = [
                {
                    "level": (
                        "high"
                        if index == 0
                        else "medium"
                    ),
                    "title": (
                        f"{row.product_series} "
                        f"出现 "
                        f"{int(row.negative_count)} "
                        f"条负面评价"
                    ),
                    "source": "产品评论",
                    "time": (
                        f"截至 "
                        f"{latest_date.isoformat()}"
                    ),
                    "count": int(
                        row.negative_count
                    ),
                    "sentiment_score": round(
                        float(
                            row.score or 0
                        ),
                        4
                    ),
                }
                for index, row
                in enumerate(alert_rows)
            ]

            sentiment = [
                {
                    "label": label,
                    "count":
                        sentiment_counts.get(
                            label,
                            0
                        ),
                    "percentage": (
                        round(
                            sentiment_counts.get(
                                label,
                                0
                            )
                            * 100
                            / total,
                            1
                        )
                        if total
                        else 0
                    ),
                }
                for label
                in (
                    "正面",
                    "中性",
                    "负面"
                )
            ]

            return jsonify(
                {
                    "code": 200,
                    "message":
                        "看板数据查询成功",
                    "data": {
                        "latest_date":
                            latest_date
                            .isoformat(),
                        "period": {
                            "days": days,
                            "start":
                                period_start
                                .isoformat(),
                            "end":
                                latest_date
                                .isoformat(),
                        },
                        "summary": {
                            "total": total,
                            "period_total":
                                current_total,
                            "period_change":
                                change_rate(
                                    current_total,
                                    previous_total
                                ),
                            "positive_count":
                                positive_count,
                            "positive_rate": (
                                round(
                                    positive_count
                                    * 100
                                    / total,
                                    1
                                )
                                if total
                                else 0
                            ),
                            "latest_count":
                                latest_count,
                            "latest_change":
                                change_rate(
                                    latest_count,
                                    previous_day_count
                                ),
                            "negative_count":
                                negative_count,
                            "period_negative":
                                current_negative,
                            "negative_change":
                                change_rate(
                                    current_negative,
                                    previous_negative
                                ),
                        },
                        "sentiment":
                            sentiment,
                        "trend":
                            trend,
                        "products":
                            products,
                        "alerts":
                            alerts,
                    },
                }
            )

    except Exception as error:
            app.logger.exception(
                "查询看板数据失败"
            )

            return jsonify(
                {
                    "code": 500,
                    "message":
                        "查询看板数据失败",
                    "error": str(error)
                }
            ), 500


@app.get("/api/reviews/statistics")
def get_review_statistics():
        try:
            filtered_query = (
                apply_review_filters(
                    db.session.query(
                        ProductReview
                    )
                )
            )

            filtered_ids = (
                filtered_query
                .with_entities(
                    ProductReview.id
                )
                .subquery()
            )

            base_filter = (
                ProductReview.id.in_(
                    db.select(
                        filtered_ids.c.id
                    )
                )
            )

            (
                total,
                average_rating,
                helpful_total,
                average_length,
                average_negative_probability,
                high_risk_count,
            ) = (
                db.session.query(
                    func.count(
                        ProductReview.id
                    ),
                    func.avg(
                        ProductReview.rating
                    ),
                    func.sum(
                        ProductReview
                        .helpful_count
                    ),
                    func.avg(
                        ProductReview
                        .review_length
                    ),
                    func.avg(ProductReview.negative_probability),
                    func.sum(case((ProductReview.risk_level == "高风险", 1), else_=0)),
                )
                .filter(base_filter)
                .one()
            )

            def grouped_counts(
                column,
                limit=None
            ):
                query = (
                    db.session.query(
                        column.label("name"),
                        func.count(
                            ProductReview.id
                        ).label("count"),
                    )
                    .filter(
                        base_filter,
                        column.isnot(None),
                        column != ""
                    )
                    .group_by(column)
                    .order_by(
                        func.count(
                            ProductReview.id
                        ).desc()
                    )
                )

                if limit:
                    query = query.limit(limit)

                return [
                    {
                        "name":
                            str(row.name),
                        "count":
                            int(row.count)
                    }
                    for row in query.all()
                ]

            rating_rows = (
                db.session.query(
                    ProductReview.rating,
                    func.count(
                        ProductReview.id
                    ),
                )
                .filter(
                    base_filter,
                    ProductReview.rating
                    .isnot(None)
                )
                .group_by(
                    ProductReview.rating
                )
                .order_by(
                    ProductReview.rating
                )
                .all()
            )

            month_rows = (
                db.session.query(
                    ProductReview.review_month,
                    func.count(
                        ProductReview.id
                    ),
                )
                .filter(
                    base_filter,
                    ProductReview
                    .review_month
                    .isnot(None),
                    ProductReview
                    .review_month != ""
                )
                .group_by(
                    ProductReview.review_month
                )
                .order_by(
                    func.min(
                        ProductReview.review_date
                    )
                )
                .all()
            )

            latest_date = (
                db.session.query(
                    func.max(
                        ProductReview.review_date
                    )
                )
                .filter(base_filter)
                .scalar()
            )

            return jsonify(
                {
                    "code": 200,
                    "message":
                        "数据库统计查询成功",
                    "data": {
                        "summary": {
                            "total": int(
                                total or 0
                            ),
                            "average_rating":
                                round(
                                    float(
                                        average_rating
                                        or 0
                                    ),
                                    2
                                ),
                            "helpful_total":
                                int(
                                    helpful_total
                                    or 0
                                ),
                            "average_length":
                                round(
                                    float(
                                        average_length
                                        or 0
                                    ),
                                    1
                                ),
                            "latest_date": (
                                latest_date
                                .isoformat()
                                if latest_date
                                else None
                            ),
                            "average_negative_probability": round(float(average_negative_probability or 0), 4),
                            "high_risk_count": int(high_risk_count or 0),
                        },
                        "sentiment":
                            grouped_counts(
                                ProductReview
                                .sentiment_label
                            ),
                        "rating": [
                            {
                                "name": (
                                    f"{float(value):g}"
                                    f"星"
                                ),
                                "count":
                                    int(count),
                            }
                            for value, count
                            in rating_rows
                        ],
                        "product_series":
                            grouped_counts(
                                ProductReview
                                .product_series,
                                10
                            ),
                        "memory":
                            grouped_counts(
                                ProductReview.memory,
                                10
                            ),
                        "disk":
                            grouped_counts(
                                ProductReview.disk,
                                10
                            ),
                        "monthly": [
                            {
                                "name": month,
                                "count":
                                    int(count)
                            }
                            for month, count
                            in month_rows
                        ],
                        "risk_level": grouped_counts(ProductReview.risk_level),
                        "issue_type": grouped_counts(ProductReview.issue_type, 10),
                    },
                }
            )

        except Exception as error:
            app.logger.exception(
                "查询数据库统计失败"
            )

            return jsonify(
                {
                    "code": 500,
                    "message":
                        "查询数据库统计失败",
                    "error": str(error)
                }
            ), 500


@app.get("/api/reviews/analysis-summary")
def get_analysis_summary():
    cached = load_analysis_cache()
    trend_data = (cached.get("data") or {}).get("trend_dashboard") or empty_analysis()["trend_dashboard"]
    return jsonify({
        "code": 200,
        "message": "分析缓存读取成功",
        "generated_at": cached.get("generated_at"),
        "data": trend_data,
    })

    try:
        query = apply_review_filters(db.session.query(ProductReview))
        rows = query.all()
        total = len(rows)

        keyword_counts = Counter()
        for row in rows:
            for word in re.split(r"[,，、;；\s]+", row.keywords or ""):
                word = word.strip()
                if word and len(word) <= 20:
                    keyword_counts[word] += 1

        def count_field(attribute):
            counts = Counter(
                str(getattr(row, attribute)).strip()
                for row in rows
                if getattr(row, attribute) not in (None, "")
            )
            return [
                {"name": name, "count": count}
                for name, count in counts.most_common()
            ]

        monthly = {}
        for row in rows:
            if not row.review_date:
                continue
            month = row.review_date.strftime("%Y-%m")
            item = monthly.setdefault(
                month,
                {"month": month, "total": 0, "negative": 0, "rating_sum": 0.0, "rating_count": 0}
            )
            item["total"] += 1
            if row.model_label == "差评" or row.sentiment_label == "负面":
                item["negative"] += 1
            if row.rating is not None:
                item["rating_sum"] += float(row.rating)
                item["rating_count"] += 1

        trend = []
        for month in sorted(monthly):
            item = monthly[month]
            trend.append({
                "month": month,
                "total": item["total"],
                "negative": item["negative"],
                "negative_rate": round(item["negative"] * 100 / item["total"], 2),
                "average_rating": round(item["rating_sum"] / item["rating_count"], 2) if item["rating_count"] else 0,
            })

        high_risk = sum(row.risk_level == "高风险" for row in rows)
        negative = sum(row.model_label == "差评" or row.sentiment_label == "负面" for row in rows)
        hidden_negative = sum(
            (row.rating is not None and float(row.rating) >= 4)
            and (row.model_label == "差评" or (row.negative_probability or 0) >= 0.5)
            for row in rows
        )

        hot_reviews = sorted(
            rows,
            key=lambda row: (
                row.risk_level == "高风险",
                row.negative_probability or 0,
                row.helpful_count or 0,
            ),
            reverse=True,
        )[:10]

        return jsonify({
            "code": 200,
            "message": "分析结果查询成功",
            "data": {
                "summary": {
                    "total": total,
                    "negative_count": negative,
                    "negative_rate": round(negative * 100 / total, 2) if total else 0,
                    "high_risk_count": high_risk,
                    "hidden_negative_count": hidden_negative,
                },
                "keywords": [
                    {"name": name, "count": count}
                    for name, count in keyword_counts.most_common(20)
                ],
                "issues": count_field("issue_type"),
                "risk_levels": count_field("risk_level"),
                "model_labels": count_field("model_label"),
                "trend": trend,
                "hot_reviews": [row.to_dict() for row in hot_reviews],
            },
        })
    except (TypeError, ValueError) as error:
        return jsonify({"code": 400, "message": f"查询参数错误：{error}"}), 400
    except Exception as error:
        app.logger.exception("查询分析结果失败")
        return jsonify({"code": 500, "message": "查询分析结果失败", "error": str(error)}), 500


from user_system import register_user_system
from import_data import register_review_management

User = register_user_system(app, db, ProductReview)
register_review_management(app, db, ProductReview, User)


@app.after_request
def refresh_cache_after_data_change(response):
    data_paths = (
        "/api/admin/import",
        "/api/admin/reviews",
    )
    if (
        request.method in {"POST", "PUT", "DELETE"}
        and request.path.startswith(data_paths)
        and 200 <= response.status_code < 300
    ):
        refresh_analysis_cache_safely()
    return response

with app.app_context():
    pass
    cached_data = (load_analysis_cache().get("data") or {})
    if not os.path.exists(ANALYSIS_CACHE_PATH) or "trend_dashboard" not in cached_data:
        refresh_analysis_cache_safely()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )