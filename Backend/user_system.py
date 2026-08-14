import os
from io import BytesIO
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import pandas as pd
from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash


def register_user_system(app, db, ProductReview=None):
    secret_key = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")
    expires_hours = int(os.getenv("JWT_EXPIRES_HOURS", "24"))

    class User(db.Model):
        __tablename__ = "users"

        id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
        username = db.Column(db.String(50), unique=True, nullable=False, index=True)
        email = db.Column(db.String(120), unique=True, nullable=False, index=True)
        password_hash = db.Column(db.String(255), nullable=False)
        display_name = db.Column(db.String(50), nullable=False)
        phone = db.Column(db.String(30))
        role = db.Column(db.String(20), nullable=False, default="user", index=True)
        status = db.Column(db.String(20), nullable=False, default="active", index=True)
        created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
        updated_at = db.Column(
            db.DateTime,
            nullable=False,
            default=datetime.now,
            onupdate=datetime.now,
        )
        last_login_at = db.Column(db.DateTime)

        def set_password(self, password):
            self.password_hash = generate_password_hash(password)

        def check_password(self, password):
            return check_password_hash(self.password_hash, password)

        def to_dict(self):
            return {
                "id": self.id,
                "username": self.username,
                "email": self.email,
                "display_name": self.display_name,
                "phone": self.phone,
                "role": self.role,
                "status": self.status,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "last_login_at": (
                    self.last_login_at.isoformat() if self.last_login_at else None
                ),
            }

    auth = Blueprint("user_system", __name__, url_prefix="/api")

    def response(code, message, data=None, status=200):
        payload = {"code": code, "message": message}
        if data is not None:
            payload["data"] = data
        return jsonify(payload), status

    def create_token(user):
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": str(user.id),
                "role": user.role,
                "iat": now,
                "exp": now + timedelta(hours=expires_hours),
            },
            secret_key,
            algorithm="HS256",
        )

    def current_user():
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None, response(401, "请先登录", status=401)

        try:
            token = authorization.split(" ", 1)[1]
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            user = db.session.get(User, int(payload["sub"]))
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return None, response(401, "登录状态无效或已过期", status=401)

        if not user or user.status != "active":
            return None, response(403, "账号不存在或已被禁用", status=403)
        return user, None

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user, error = current_user()
            if error:
                return error
            return view(user, *args, **kwargs)

        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user, error = current_user()
            if error:
                return error
            if user.role != "admin":
                return response(403, "无管理员权限", status=403)
            return view(user, *args, **kwargs)

        return wrapped

    def valid_password(password):
        return (
            len(password) >= 8
            and any(char.isalpha() for char in password)
            and any(char.isdigit() for char in password)
        )

    @auth.post("/auth/register")
    def register():
        body = request.get_json(silent=True) or {}
        username = str(body.get("username", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        display_name = str(body.get("display_name", "")).strip() or username

        if not username or not email or not password:
            return response(400, "用户名、邮箱和密码不能为空", status=400)
        if len(username) < 3 or len(username) > 50:
            return response(400, "用户名长度应为 3–50 个字符", status=400)
        if "@" not in email or len(email) > 120:
            return response(400, "邮箱格式不正确", status=400)
        if not valid_password(password):
            return response(400, "密码至少 8 位，且必须包含字母和数字", status=400)
        if User.query.filter(
            or_(User.username == username, User.email == email)
        ).first():
            return response(409, "用户名或邮箱已被使用", status=409)

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            phone=str(body.get("phone", "")).strip() or None,
            role="user",
            status="active",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return response(201, "注册成功", {"user": user.to_dict()}, 201)

    @auth.post("/auth/login")
    def login():
        body = request.get_json(silent=True) or {}
        account = str(body.get("account", "")).strip()
        password = str(body.get("password", ""))
        user = User.query.filter(
            or_(User.username == account, User.email == account.lower())
        ).first()

        if not user or not user.check_password(password):
            return response(401, "用户名、邮箱或密码错误", status=401)
        if user.status != "active":
            return response(403, "账号已被禁用，请联系管理员", status=403)

        user.last_login_at = datetime.now()
        db.session.commit()
        return response(
            200,
            "登录成功",
            {"token": create_token(user), "user": user.to_dict()},
        )

    @auth.get("/auth/me")
    @login_required
    def me(user):
        return response(200, "查询成功", {"user": user.to_dict()})

    @auth.put("/auth/profile")
    @login_required
    def update_profile(user):
        body = request.get_json(silent=True) or {}
        email = str(body.get("email", user.email)).strip().lower()
        display_name = str(body.get("display_name", user.display_name)).strip()
        phone = str(body.get("phone", user.phone or "")).strip() or None

        duplicate = User.query.filter(User.email == email, User.id != user.id).first()
        if duplicate:
            return response(409, "邮箱已被其他用户使用", status=409)
        if not display_name or "@" not in email:
            return response(400, "姓名或邮箱格式不正确", status=400)

        user.email = email
        user.display_name = display_name
        user.phone = phone
        db.session.commit()
        return response(200, "个人信息已更新", {"user": user.to_dict()})

    @auth.put("/auth/password")
    @login_required
    def change_password(user):
        body = request.get_json(silent=True) or {}
        old_password = str(body.get("old_password", ""))
        new_password = str(body.get("new_password", ""))

        if not user.check_password(old_password):
            return response(400, "原密码错误", status=400)
        if not valid_password(new_password):
            return response(400, "新密码至少 8 位，且必须包含字母和数字", status=400)

        user.set_password(new_password)
        db.session.commit()
        return response(200, "密码修改成功，请重新登录")

    @auth.get("/admin/users")
    @admin_required
    def list_users(_admin):
        keyword = request.args.get("keyword", "").strip()
        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
        query = User.query
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    User.username.like(like),
                    User.email.like(like),
                    User.display_name.like(like),
                )
            )
        pagination = query.order_by(User.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        return response(
            200,
            "查询成功",
            {
                "items": [item.to_dict() for item in pagination.items],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": pagination.total,
                    "pages": pagination.pages,
                },
            },
        )

    @auth.post("/admin/users")
    @admin_required
    def create_user(_admin):
        body = request.get_json(silent=True) or {}
        username = str(body.get("username", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        role = body.get("role", "user")
        if role not in {"admin", "user"}:
            return response(400, "角色不正确", status=400)
        if not username or "@" not in email or not valid_password(password):
            return response(400, "用户信息或密码格式不正确", status=400)
        if User.query.filter(or_(User.username == username, User.email == email)).first():
            return response(409, "用户名或邮箱已存在", status=409)

        user = User(
            username=username,
            email=email,
            display_name=str(body.get("display_name", "")).strip() or username,
            phone=str(body.get("phone", "")).strip() or None,
            role=role,
            status="active",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return response(201, "用户创建成功", {"user": user.to_dict()}, 201)

    @auth.put("/admin/users/<int:user_id>")
    @admin_required
    def update_user(admin, user_id):
        user = db.session.get(User, user_id)
        if not user:
            return response(404, "用户不存在", status=404)
        body = request.get_json(silent=True) or {}
        role = body.get("role", user.role)
        status = body.get("status", user.status)
        if role not in {"admin", "user"} or status not in {"active", "disabled"}:
            return response(400, "角色或状态不正确", status=400)
        if user.id == admin.id and (role != "admin" or status != "active"):
            return response(400, "不能取消或禁用当前管理员账号", status=400)
        user.role = role
        user.status = status
        user.display_name = str(body.get("display_name", user.display_name)).strip()
        db.session.commit()
        return response(200, "用户已更新", {"user": user.to_dict()})

    @auth.put("/admin/users/<int:user_id>/reset-password")
    @admin_required
    def reset_password(_admin, user_id):
        user = db.session.get(User, user_id)
        body = request.get_json(silent=True) or {}
        new_password = str(body.get("new_password", ""))
        if not user:
            return response(404, "用户不存在", status=404)
        if not valid_password(new_password):
            return response(400, "密码至少 8 位，且必须包含字母和数字", status=400)
        user.set_password(new_password)
        db.session.commit()
        return response(200, "密码已重置")

    @auth.delete("/admin/users/<int:user_id>")
    @admin_required
    def delete_user(admin, user_id):
        user = db.session.get(User, user_id)
        if not user:
            return response(404, "用户不存在", status=404)
        if user.id == admin.id:
            return response(400, "不能删除当前登录账号", status=400)
        db.session.delete(user)
        db.session.commit()
        return response(200, "用户已删除")

    @auth.post("/admin/import")
    @admin_required
    def import_reviews(_admin):
        if ProductReview is None:
            return response(500, "评论数据模型未配置", status=500)

        uploaded_file = request.files.get("file")
        if uploaded_file is None or not uploaded_file.filename:
            return response(400, "请选择要导入的 CSV 或 Excel 文件", status=400)

        filename = uploaded_file.filename.lower()
        if not filename.endswith((".csv", ".xlsx", ".xls")):
            return response(400, "仅支持 CSV、XLS 和 XLSX 文件", status=400)

        if request.content_length and request.content_length > 50 * 1024 * 1024:
            return response(413, "文件大小不能超过 50 MB", status=413)

        try:
            file_bytes = uploaded_file.read()
            if filename.endswith(".csv"):
                data = None
                last_error = None
                for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
                    try:
                        data = pd.read_csv(
                            BytesIO(file_bytes),
                            encoding=encoding,
                            low_memory=False,
                        )
                        break
                    except UnicodeDecodeError as error:
                        last_error = error
                if data is None:
                    raise ValueError(f"无法识别 CSV 编码：{last_error}")
            else:
                data = pd.read_excel(BytesIO(file_bytes))

            from import_data import clean_data

            total_rows = len(data)
            data.columns = [str(column).strip() for column in data.columns]
            data["data_index"] = range(1, total_rows + 1)
            cleaned_data = clean_data(data)
            valid_rows = len(cleaned_data)
            next_data_index = (
                db.session.query(db.func.max(ProductReview.data_index)).scalar() or 0
            ) + 1
            cleaned_data = cleaned_data.reset_index(drop=True)
            cleaned_data["data_index"] = range(
                next_data_index,
                next_data_index + valid_rows,
            )
            records = cleaned_data.astype(object).where(
                pd.notna(cleaned_data), None
            ).to_dict(
                orient="records"
            )

            if records:
                db.session.bulk_insert_mappings(ProductReview, records)
                db.session.commit()

            imported_rows = len(records)
            skipped_rows = 0
            failed_rows = total_rows - valid_rows
            return jsonify(
                {
                    "code": 200,
                    "message": (
                        f"导入完成：新增 {imported_rows} 条，"
                        f"跳过重复 {skipped_rows} 条"
                    ),
                    "total": total_rows,
                    "success": imported_rows,
                    "failed": failed_rows,
                    "total_rows": total_rows,
                    "imported_rows": imported_rows,
                    "failed_rows": failed_rows,
                    "skipped_rows": skipped_rows,
                }
            )
        except (ValueError, ImportError) as error:
            db.session.rollback()
            return response(400, str(error), status=400)
        except Exception as error:
            db.session.rollback()
            app.logger.exception("管理员导入评论数据失败")
            return response(500, f"导入失败：{error}", status=500)

    app.register_blueprint(auth)
    app.User = User
    return User