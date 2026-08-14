import argparse
import os
from datetime import datetime
from functools import wraps
from getpass import getpass
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import jwt
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from sqlalchemy import create_engine, inspect, text
from sqlalchemy import or_


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "Data" / "Processed"

load_dotenv(BACKEND_DIR / ".env")

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "lenovo_insight")
TABLE_NAME = "product_review"

COLUMN_MAPPING = {
    "data_index": "data_index",
    "用户名": "username",
    "电脑配置": "computer_config",
    "评论内容": "review_content",
    "有用数": "helpful_count",
    "重复购买情况": "repeat_purchase",
    "评分": "rating",
    "内存": "memory",
    "硬盘": "disk",
    "date": "review_date",
    "产品系列": "product_series",
    "评论长度": "review_length",
    "月份": "review_month",
    "评论分词": "tokenized_content",
    "评论分词_去停用词": "filtered_content",
    "情感分数": "sentiment_score",
    "评论关键词": "keywords",
    "情感标签": "sentiment_label",
    "模型预测值": "model_prediction",
    "模型标签": "model_label",
    "差评概率": "negative_probability",
    "原始标签": "original_label",
    "问题类型": "issue_type",
    "风险等级": "risk_level",
    "TFIDF向量": "tfidf_vector",
}

TARGET_COLUMNS = list(COLUMN_MAPPING.values())

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS product_review (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    data_index BIGINT NOT NULL,
    username VARCHAR(100),
    computer_config VARCHAR(500),
    review_content LONGTEXT NOT NULL,
    helpful_count INT NOT NULL DEFAULT 0,
    repeat_purchase VARCHAR(20),
    rating DECIMAL(3, 1),
    memory VARCHAR(50),
    disk VARCHAR(50),
    review_date DATE,
    product_series VARCHAR(100),
    review_length INT,
    review_month VARCHAR(30),
    tokenized_content LONGTEXT,
    filtered_content LONGTEXT,
    sentiment_score DOUBLE,
    keywords TEXT,
    sentiment_label VARCHAR(20),
    model_prediction TINYINT,
    model_label VARCHAR(20),
    negative_probability DOUBLE,
    original_label VARCHAR(20),
    issue_type VARCHAR(100),
    risk_level VARCHAR(20),
    tfidf_vector LONGTEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_product_review_data_index (data_index),
    INDEX idx_product_review_date (review_date),
    INDEX idx_product_review_sentiment (sentiment_label),
    INDEX idx_product_review_risk (risk_level),
    INDEX idx_product_review_issue (issue_type),
    INDEX idx_product_review_series (product_series),
    INDEX idx_product_review_rating (rating)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

ANALYSIS_COLUMNS = {
    "model_prediction": "TINYINT",
    "model_label": "VARCHAR(20)",
    "negative_probability": "DOUBLE",
    "original_label": "VARCHAR(20)",
    "issue_type": "VARCHAR(100)",
    "risk_level": "VARCHAR(20)",
}


def register_review_management(app, db, ProductReview, User):
    reviews_api = Blueprint("review_management", __name__)
    secret_key = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")

    def response(code, message, data=None, status=200):
        payload = {"code": code, "message": message}
        if data is not None:
            payload["data"] = data
        return jsonify(payload), status

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            authorization = request.headers.get("Authorization", "")
            if not authorization.startswith("Bearer "):
                return response(401, "请先登录", status=401)
            try:
                token = authorization.split(" ", 1)[1]
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                user = db.session.get(User, int(payload["sub"]))
            except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
                return response(401, "登录状态无效或已过期", status=401)
            if not user or user.status != "active":
                return response(403, "账号不存在或已被禁用", status=403)
            if user.role != "admin":
                return response(403, "无管理员权限", status=403)
            return view(*args, **kwargs)
        return wrapped

    def apply_review_data(review, body, creating=False):
        if creating or "data_index" in body:
            review.data_index = int(body.get("data_index"))
        if creating or "review_content" in body:
            content = str(body.get("review_content", "")).strip()
            if not content:
                raise ValueError("评论内容不能为空")
            review.review_content = content

        text_fields = (
            "username", "computer_config", "repeat_purchase", "memory", "disk",
            "product_series", "review_month", "keywords", "sentiment_label",
        )
        for field in text_fields:
            if field in body:
                value = str(body.get(field, "")).strip()
                setattr(review, field, value or None)

        integer_fields = ("helpful_count", "review_length")
        for field in integer_fields:
            if field in body:
                value = body.get(field)
                setattr(review, field, int(value) if value not in (None, "") else None)

        float_fields = ("rating", "sentiment_score")
        for field in float_fields:
            if field in body:
                value = body.get(field)
                setattr(review, field, float(value) if value not in (None, "") else None)

        if "review_date" in body:
            value = str(body.get("review_date", "")).strip()
            review.review_date = datetime.strptime(value, "%Y-%m-%d").date() if value else None

        review.review_length = review.review_length or len(review.review_content or "")

    @reviews_api.get("/api/admin/reviews")
    @admin_required
    def list_admin_reviews():
        page = max(request.args.get("page", 1, type=int), 1)
        page_size = min(max(request.args.get("page_size", 10, type=int), 1), 100)
        keyword = request.args.get("keyword", "").strip()
        query = ProductReview.query
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(or_(
                ProductReview.username.like(pattern),
                ProductReview.review_content.like(pattern),
                ProductReview.product_series.like(pattern),
            ))
        pagination = query.order_by(ProductReview.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        return response(200, "查询成功", {
            "items": [item.to_dict() for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "page_size": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        })

    @reviews_api.post("/api/admin/reviews")
    @admin_required
    def create_admin_review():
        body = request.get_json(silent=True) or {}
        try:
            data_index = int(body.get("data_index"))
            if ProductReview.query.filter_by(data_index=data_index).first():
                return response(409, "data_index 已存在", status=409)
            review = ProductReview()
            apply_review_data(review, body, creating=True)
            db.session.add(review)
            db.session.commit()
            return response(201, "评论已新增", {"item": review.to_dict()}, 201)
        except (TypeError, ValueError) as error:
            db.session.rollback()
            return response(400, str(error) or "数据格式错误", status=400)
        except Exception as error:
            db.session.rollback()
            app.logger.exception("新增评论失败")
            return response(500, f"新增评论失败：{error}", status=500)

    @reviews_api.put("/api/admin/reviews/<int:review_id>")
    @admin_required
    def update_admin_review(review_id):
        review = db.session.get(ProductReview, review_id)
        if not review:
            return response(404, "评论不存在", status=404)
        body = request.get_json(silent=True) or {}
        try:
            if "data_index" in body:
                data_index = int(body["data_index"])
                duplicate = ProductReview.query.filter(
                    ProductReview.data_index == data_index,
                    ProductReview.id != review_id,
                ).first()
                if duplicate:
                    return response(409, "data_index 已存在", status=409)
            apply_review_data(review, body)
            db.session.commit()
            return response(200, "评论已更新", {"item": review.to_dict()})
        except (TypeError, ValueError) as error:
            db.session.rollback()
            return response(400, str(error) or "数据格式错误", status=400)
        except Exception as error:
            db.session.rollback()
            app.logger.exception("更新评论失败")
            return response(500, f"更新评论失败：{error}", status=500)

    @reviews_api.delete("/api/admin/reviews/<int:review_id>")
    @admin_required
    def delete_admin_review(review_id):
        review = db.session.get(ProductReview, review_id)
        if not review:
            return response(404, "评论不存在", status=404)
        db.session.delete(review)
        db.session.commit()
        return response(200, "评论已删除")

    @reviews_api.delete("/api/admin/reviews")
    @admin_required
    def clear_admin_reviews():
        body = request.get_json(silent=True) or {}
        if body.get("confirmation") != "CLEAR_ALL_REVIEWS":
            return response(400, "清空确认信息不正确", status=400)
        deleted = db.session.query(ProductReview).delete(synchronize_session=False)
        db.session.commit()
        return response(200, "数据库已清空", {"deleted": deleted})

    app.register_blueprint(reviews_api)


def ensure_analysis_columns(connection):
    existing = {
        column["name"]
        for column in inspect(connection).get_columns(TABLE_NAME)
    }
    for name, sql_type in ANALYSIS_COLUMNS.items():
        if name not in existing:
            connection.execute(
                text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {name} {sql_type}")
            )


def parse_args():
    parser = argparse.ArgumentParser(description="将分析后的评论数据导入 MySQL")
    parser.add_argument(
        "file",
        nargs="?",
        help="CSV/Excel 文件路径；不填写时自动读取 Data/Processed 中最新的文件",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="导入前清空 product_review 表（谨慎使用）",
    )
    return parser.parse_args()


def resolve_input_file(file_argument):
    if file_argument:
        file_path = Path(file_argument).expanduser()
        if not file_path.is_absolute():
            file_path = (PROJECT_ROOT / file_path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"文件不存在：{file_path}")
        return file_path

    if not DEFAULT_DATA_DIR.exists():
        raise FileNotFoundError(f"数据目录不存在：{DEFAULT_DATA_DIR}")

    candidates = [
        path
        for path in DEFAULT_DATA_DIR.iterdir()
        if path.suffix.lower() in {".csv", ".xlsx", ".xls"}
        and not path.name.startswith("~$")
    ]
    if not candidates:
        raise FileNotFoundError(f"目录中没有 CSV/Excel 文件：{DEFAULT_DATA_DIR}")

    return max(candidates, key=lambda path: path.stat().st_mtime)


def read_data(file_path):
    if file_path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)

    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            data = pd.read_csv(
                file_path,
                encoding=encoding,
                low_memory=False,
            )
            print(f"CSV 编码：{encoding}")
            return data
        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError(f"无法识别 CSV 编码：{last_error}")


def clean_data(data):
    data = data.copy()
    data.columns = [str(column).strip() for column in data.columns]

    optional_analysis_columns = {
        "模型预测值": None,
        "模型标签": "",
        "差评概率": None,
        "原始标签": "",
        "问题类型": "",
        "风险等级": "",
    }
    for column, default in optional_analysis_columns.items():
        if column not in data.columns:
            data[column] = default

    if "月份" not in data.columns:
        if "date" in data.columns:
            dates = pd.to_datetime(data["date"], errors="coerce")
            data["月份"] = dates.dt.strftime("%Y-%m").fillna("")
        else:
            data["月份"] = ""

    if "TFIDF向量" not in data.columns:
        data["TFIDF向量"] = ""

    missing = [
        source_name
        for source_name in COLUMN_MAPPING
        if source_name not in data.columns
    ]
    if missing:
        raise ValueError(f"数据文件缺少字段：{', '.join(missing)}")

    data = data.rename(columns=COLUMN_MAPPING)
    data = data[TARGET_COLUMNS].copy()

    text_columns = [
        "username",
        "computer_config",
        "review_content",
        "repeat_purchase",
        "memory",
        "disk",
        "product_series",
        "review_month",
        "tokenized_content",
        "filtered_content",
        "keywords",
        "sentiment_label",
        "model_label",
        "original_label",
        "issue_type",
        "risk_level",
        "tfidf_vector",
    ]
    for column in text_columns:
        data[column] = data[column].fillna("").astype(str).str.strip()

    data["data_index"] = pd.to_numeric(data["data_index"], errors="coerce")
    data["helpful_count"] = (
        pd.to_numeric(data["helpful_count"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )
    data["rating"] = pd.to_numeric(data["rating"], errors="coerce")
    data["review_length"] = pd.to_numeric(
        data["review_length"], errors="coerce"
    ).astype("Int64")
    data["sentiment_score"] = pd.to_numeric(
        data["sentiment_score"], errors="coerce"
    )
    data["model_prediction"] = pd.to_numeric(
        data["model_prediction"], errors="coerce"
    ).astype("Int64")
    data["negative_probability"] = pd.to_numeric(
        data["negative_probability"], errors="coerce"
    ).clip(lower=0, upper=1)
    data["review_date"] = pd.to_datetime(
        data["review_date"], errors="coerce"
    ).dt.date

    data = data[
        data["data_index"].notna() & data["review_content"].ne("")
    ].copy()
    data["data_index"] = data["data_index"].astype("int64")

    data = data.drop_duplicates(subset=["data_index"], keep="last")
    data = data.where(pd.notna(data), None)
    return data


def make_engine():
    password = os.getenv("MYSQL_PASSWORD")
    if password is None:
        password = getpass("请输入 MySQL 密码：")

    database_url = (
        f"mysql+pymysql://{MYSQL_USER}:{quote_plus(password)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    return create_engine(database_url, pool_pre_ping=True)


def main():
    args = parse_args()
    input_file = resolve_input_file(args.file)
    print(f"正在读取：{input_file}")

    raw_data = read_data(input_file)
    print(f"原始数据：{len(raw_data)} 行")

    cleaned_data = clean_data(raw_data)
    print(f"清洗后数据：{len(cleaned_data)} 行")

    engine = make_engine()
    with engine.begin() as connection:
        connection.execute(text(CREATE_TABLE_SQL))
        ensure_analysis_columns(connection)

        if args.replace:
            connection.execute(text("TRUNCATE TABLE product_review"))
            print("已清空原表，准备重新导入。")

        existing_indexes = set(
            connection.execute(
                text("SELECT data_index FROM product_review")
            ).scalars()
        )

    new_data = cleaned_data[
        ~cleaned_data["data_index"].isin(existing_indexes)
    ].copy()

    if new_data.empty:
        print("没有需要新增的数据，所有 data_index 均已存在。")
        try:
            from app import app, refresh_analysis_cache_safely
            with app.app_context():
                refresh_analysis_cache_safely()
            print("分析缓存已更新。")
        except Exception as error:
            print(f"分析缓存更新失败：{error}")
        return

    new_data.to_sql(
        name=TABLE_NAME,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=500,
        method="multi",
    )

    print("导入成功！")
    print(f"本次新增：{len(new_data)} 条")
    print(f"已跳过重复：{len(cleaned_data) - len(new_data)} 条")
    print(f"目标表：{MYSQL_DATABASE}.{TABLE_NAME}")

    try:
        from app import app, refresh_analysis_cache_safely
        with app.app_context():
            refresh_analysis_cache_safely()
        print("分析缓存已更新。")
    except Exception as error:
        print(f"数据已导入，但分析缓存更新失败：{error}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"导入失败：{error}")
        raise SystemExit(1)