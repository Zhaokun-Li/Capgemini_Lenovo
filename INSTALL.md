# Lenovo Insight 用户系统接入说明

## 已包含的功能

- 普通用户注册
- 用户名或邮箱登录
- JWT 登录认证
- 个人信息查看和修改
- 修改密码
- 管理员查看、搜索、新增、禁用、启用和删除用户
- 管理员修改角色和重置密码
- 前端路由登录保护和管理员权限保护
- MySQL 自动创建 `users` 表

## 1. 安装后端依赖

在 `Backend` 目录执行：

```powershell
pip install PyJWT
```

并在原 `requirements.txt` 末尾加入：

```text
PyJWT
```

## 2. 配置环境变量

在原 `Backend/.env` 中增加：

```env
JWT_SECRET_KEY=请替换为一串足够长的随机字符
JWT_EXPIRES_HOURS=24
```

生产环境禁止使用示例密钥。

## 3. 放置并接入后端文件

把本压缩包的：

```text
Backend/user_system.py
Backend/create_admin.py
```

复制到原项目的 `Backend` 目录。

打开原 `Backend/app.py`，在 `db = SQLAlchemy(app)` 后面不要立即注册；应在所有原模型定义完成后、`with app.app_context():` 前加入：

```python
from user_system import register_user_system

User = register_user_system(app, db)
```

原文件结尾应保持：

```python
from user_system import register_user_system

User = register_user_system(app, db)

with app.app_context():
    db.create_all()
```

这样 Flask 启动时会在当前 MySQL 数据库自动创建 `users` 表。

## 4. 创建第一个管理员

确认 MySQL 已启动且 `.env` 正确，然后在 `Backend` 目录执行：

```powershell
python create_admin.py
```

按提示输入管理员用户名、邮箱和密码。不要再使用前端硬编码的 `admin / 123456`。

## 5. 放置前端文件

将 `Frontend/src` 下的文件复制到原项目 `Frontend/PC/src` 对应目录：

```text
api/auth.js
views/login.vue
views/register.vue
views/profile.vue
views/user_management.vue
router/user-routes.js
```

## 6. 接入原路由

在原 `src/router/index.js` 中导入：

```javascript
import { userRoutes, installUserGuard } from './user-routes'
```

把 `userRoutes` 展开到原 `routes` 数组：

```javascript
const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...userRoutes,
    // 这里继续放原来的 overview、舆情监控、舆情分析等路由
  ]
})

installUserGuard(router)

export default router
```

如果你的 `overview` 等页面位于一个 Layout 子路由中，可把 `profile` 和 `user-management` 放到同一个 `children` 数组，登录与注册仍放在外层。

## 7. 根据角色显示导航

在 Sidebar 或公共布局中：

```vue
<script setup>
import { computed } from 'vue'

const currentUser = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
})
</script>

<template>
  <RouterLink to="/profile">个人中心</RouterLink>
  <RouterLink
    v-if="currentUser?.role === 'admin'"
    to="/user-management"
  >
    用户管理
  </RouterLink>
</template>
```

退出登录：

```javascript
import { logout } from './api/auth'

logout()
router.replace('/login')
```

## 8. 启动测试

后端：

```powershell
cd Backend
python app.py
```

前端：

```powershell
cd Frontend/PC
npm run dev
```

测试顺序：

1. 运行 `create_admin.py` 创建管理员。
2. 在 `/login` 用管理员账号登录。
3. 进入 `/user-management` 新增或管理用户。
4. 在 `/register` 注册普通用户。
5. 普通用户登录后确认无法访问 `/user-management`。
6. 在 `/profile` 修改个人资料和密码。

## 接口清单

| 方法 | 地址 | 权限 |
|---|---|---|
| POST | `/api/auth/register` | 公开 |
| POST | `/api/auth/login` | 公开 |
| GET | `/api/auth/me` | 已登录 |
| PUT | `/api/auth/profile` | 已登录 |
| PUT | `/api/auth/password` | 已登录 |
| GET | `/api/admin/users` | 管理员 |
| POST | `/api/admin/users` | 管理员 |
| PUT | `/api/admin/users/:id` | 管理员 |
| PUT | `/api/admin/users/:id/reset-password` | 管理员 |
| DELETE | `/api/admin/users/:id` | 管理员 |

