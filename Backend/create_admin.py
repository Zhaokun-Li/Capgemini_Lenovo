import getpass

from app import User, app, db


with app.app_context():
    username = input("管理员用户名: ").strip()
    email = input("管理员邮箱: ").strip().lower()
    display_name = input("显示名称（可留空）: ").strip() or username
    password = getpass.getpass("管理员密码（至少8位，包含字母和数字）: ")

    if User.query.filter_by(username=username).first():
        raise SystemExit("用户名已存在")
    if User.query.filter_by(email=email).first():
        raise SystemExit("邮箱已存在")
    if len(password) < 8 or not any(c.isalpha() for c in password) or not any(
        c.isdigit() for c in password
    ):
        raise SystemExit("密码不符合要求")

    user = User(
        username=username,
        email=email,
        display_name=display_name,
        role="admin",
        status="active",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"管理员 {username} 创建成功")

