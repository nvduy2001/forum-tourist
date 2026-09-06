# CLAUDE.md — Ngữ cảnh dự án cho Claude Code

## Tổng quan
Website quản lý diễn đàn đánh giá và chia sẻ trải nghiệm về địa điểm/dịch vụ.
Chi tiết đầy đủ: xem `docs/srs.md`, `docs/usecase-detail.md`, `docs/erd.html`.

## Tech stack
- Backend: Django (mô hình MVT, KHÔNG dùng thuật ngữ MVC khi giải thích code)
- Database: PostgreSQL, truy cập qua Django ORM
- Cache & tác vụ nền: Redis + Celery (dùng cho: tự động đóng nhiệm vụ theo mùa khi hết hạn, gửi thông báo)
- Auth: `django-allauth` — đăng nhập email/password + Google OAuth. KHÔNG làm Facebook login, KHÔNG làm OTP qua SMS.
  - Xác thực tài khoản: dùng link xác nhận qua email (built-in của allauth, `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`), KHÔNG cần tự viết OTP số.
- Xác minh chủ địa điểm: KHÔNG yêu cầu upload giấy tờ (CMND/giấy phép kinh doanh). Dùng luồng đơn giản: chủ địa điểm điền form thông tin liên hệ → Admin đối chiếu thủ công với thông tin công khai đã có trên hệ thống → duyệt. Field `PLACES.status` có giá trị `pending_verification` / `verified`.
- Check-in xác thực đánh giá: dùng Geolocation API của trình duyệt (navigator.geolocation) + công thức Haversine so khoảng cách với tọa độ địa điểm (ngưỡng ~200-300m). Yêu cầu deploy HTTPS.

## Cấu trúc Django app (mỗi app = 1 nhóm chức năng trong SRS)
| App | Model chính | Actor liên quan |
|---|---|---|
| `accounts` | User (kế thừa AbstractUser) | User + Admin |
| `places` | Place | User (xem/tìm/thêm), Business owner (sửa), Admin (duyệt) |
| `reviews` | Review, Comment, CheckIn | User |
| `lists` | List, ListItem | User |
| `forum` | ForumPost | User |
| `gamification` | Badge, UserBadge, SeasonalMission, MissionProgress | User + Admin (tạo nhiệm vụ) |
| `moderation` | Report | Admin |

Chi tiết field từng model: xem sơ đồ ERD trong `docs/erd.html`.

## 2 actor duy nhất
- **User**: người dùng phổ thông. Chủ địa điểm chỉ là User có thêm cờ `is_business_owner=True` và field `owned_place`, KHÔNG phải role/model riêng.
- **Admin**: quản trị viên. Kiểm duyệt viên chỉ là Admin với quyền hẹp hơn (dùng Django permissions/groups, KHÔNG tạo model Role riêng).

## 3 tính năng USP — bắt buộc làm đúng luồng, không đơn giản hóa
1. **Time capsule review**: khi user đang ở trang viết đánh giá cho 1 địa điểm, KHÔNG được query/trả về điểm trung bình và danh sách review khác của địa điểm đó trong cùng response. Chỉ sau khi POST đánh giá thành công mới trả về so sánh điểm cá nhân vs trung bình cộng đồng.
2. **Khám phá địa điểm mới**: `Place.review_count` là field đếm sẵn (denormalized), cập nhật mỗi khi Review được tạo/xóa (dùng Django signal hoặc override save()/delete()). Khi review_count chuyển từ 0 → 1, gắn UserBadge "Người khai phá" cho tác giả review đó. Xử lý race condition bằng `select_for_update()` hoặc unique constraint.
3. **Đại sứ khu vực theo mùa**: Admin tạo SeasonalMission (region, category, required_count, start/end date). User tham gia → tạo MissionProgress. Mỗi Review hợp lệ trong phạm vi mission (đúng region/category, trong thời hạn) → progress_count += 1. Khi đạt required_count → cấp Badge tự động. Dùng Celery beat task để tự đóng mission hết hạn.

## Quy ước code
- Đặt tên biến/hàm bằng tiếng Anh, comment ngắn gọn tiếng Việt cho phần nghiệp vụ đặc thù (đặc biệt 3 phần USP ở trên).
- Ưu tiên Class-Based Views cho các view CRUD chuẩn, function-based view cho các luồng nghiệp vụ đặc biệt (time capsule review, check-in).
- Viết test cho: Haversine check-in, tính review_count, logic cấp huy hiệu "Người khai phá", logic mission progress.

## Thứ tự xây dựng đề xuất (bám sát Giai đoạn 4 kế hoạch)
1. Khởi tạo project Django + cấu hình PostgreSQL, Redis, Celery, allauth (Google only)
2. App `accounts` + `places`: model, migration, admin, CRUD cơ bản, tìm kiếm/lọc
3. App `reviews`: model Review/Comment, luồng Time capsule review, check-in GPS
4. App `lists`, `forum`, `gamification`: bao gồm 2 USP còn lại
5. App `moderation`: trang duyệt nội dung, xử lý báo cáo
6. Viết test cho các phần nghiệp vụ đặc thù ở mục "Quy ước code"
7. Giao diện: dựng template theo `docs/wireframe.html` cho từng màn hình tương ứng

## Không làm (đã quyết định loại khỏi phạm vi)
- Facebook login
- OTP qua SMS
- Xác minh doanh nghiệp bằng upload giấy tờ tùy thân/kinh doanh
- Ứng dụng di động native
