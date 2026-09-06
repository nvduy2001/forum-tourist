# Forum Tourist

Website quản lý diễn đàn đánh giá và chia sẻ trải nghiệm về địa điểm/dịch vụ (Django).

Chi tiết ngữ cảnh dự án: xem [`CLAUDE.md`](CLAUDE.md).

## Yêu cầu

- Python 3.12+
- PostgreSQL 14+ (khuyến nghị) — có thể bỏ qua, dự án tự fallback sang SQLite nếu chưa cấu hình
- Git

## 1. Tải code và tạo môi trường ảo

```powershell
git clone https://github.com/nvduy2001/forum-tourist.git
cd forum-tourist

python -m venv .venv
.venv\Scripts\activate
```

## 2. Cài thư viện

```powershell
pip install -r requirements.txt
```

## 3. Cài đặt & kết nối PostgreSQL

Nếu máy chưa có PostgreSQL, tải và cài tại **https://www.postgresql.org/download/windows/** (khi cài, nhớ mật khẩu bạn đặt cho user `postgres`). Bỏ qua Stack Builder khi nó hiện lên sau khi cài xong, không cần dùng.

Mở **pgAdmin 4** (cài kèm theo PostgreSQL):

1. Kết nối vào server **PostgreSQL** (nhập mật khẩu user `postgres` đã đặt lúc cài).
2. Chuột phải **Login/Group Roles** → **Create** → **Login/Group Role...**
   - Tab **General**: Name = `forumtourist`
   - Tab **Definition**: Password = `forumtourist`
   - Tab **Privileges**: bật **Can login?** = Yes, bật **Can create databases?** = Yes (cần để chạy test)
   - **Save**
3. Chuột phải **Databases** → **Create** → **Database...**
   - Database = `forumtourist`, Owner = `forumtourist`
   - **Save**

## 4. Cấu hình biến môi trường

Copy file mẫu và chỉnh lại nếu cần:

```powershell
copy .env.example .env
```

Mặc định `.env.example` đã trỏ `DATABASE_URL` vào đúng database/user vừa tạo ở bước 3
(`postgres://forumtourist:forumtourist@localhost:5432/forumtourist`). Nếu bạn đặt tên
user/password/database khác thì sửa lại giá trị này cho khớp.

Các biến đáng chú ý khác trong `.env`:

| Biến | Ý nghĩa |
|---|---|
| `SECRET_KEY` | Đổi sang chuỗi ngẫu nhiên khi deploy thật, dev không bắt buộc |
| `DEBUG` | `True` khi dev |
| `CELERY_TASK_ALWAYS_EAGER` | `True` = tác vụ nền (gửi email, đóng mission...) chạy đồng bộ ngay trong request, không cần Redis/Celery worker thật. Đặt `False` khi đã deploy Celery worker + Redis thật |
| `EMAIL_BACKEND` | Mặc định in email ra terminal (console backend) thay vì gửi thật |
| `GOOGLE_OAUTH_CLIENT_ID` / `SECRET` | Để trống thì đăng nhập Google không dùng được, đăng nhập email/password vẫn hoạt động bình thường |

## 5. Khởi tạo database

```powershell
python manage.py migrate
```

## 6. Tạo tài khoản quản trị

```powershell
python manage.py createsuperuser
```

## 7. Chạy server

```powershell
python manage.py runserver
```

Mở trình duyệt:

- Trang chính: **http://127.0.0.1:8000/places/**
- Trang quản trị: **http://127.0.0.1:8000/admin/**

## Chạy test

```powershell
python manage.py test
```

## Ghi chú

- Không có Redis/Celery worker thật thì để nguyên `CELERY_TASK_ALWAYS_EAGER=True` trong `.env` —
  toàn bộ tính năng (thông báo email, tự đóng seasonal mission...) vẫn hoạt động đúng, chỉ chạy
  đồng bộ thay vì chạy nền thật.
- Ảnh đại diện/ảnh bìa user, ảnh địa điểm, media đính kèm review được lưu vào thư mục `media/`
  (tự tạo khi upload, không commit vào git).
- Đăng nhập Google OAuth cần tạo OAuth Client ID trên Google Cloud Console và điền vào
  `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` trong `.env`.
