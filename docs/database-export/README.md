# Bản xuất database Aquaponics Platform

Bản xuất cấu trúc từ SQLAlchemy metadata tại mã nguồn commit `91528d492c5905644038ae7c0810e406f03470cb`. Alembic có một head: `0035` (35 revisions). Đây là cấu trúc model hiện tại, không phải bản sao database đang chạy và không khẳng định schema của database đang chạy đã đồng bộ migration.

## Các file

- `aquaponics_schema.sql`: script PostgreSQL tạo 38 bảng, 466 cột, 80 khóa ngoại, 63 index khai báo tường minh và 10 enum; bao gồm identity, server defaults, primary key, unique và check constraints. PostgreSQL có thể tạo thêm index cho primary key/unique constraints.
- `aquaponics_erd.drawio`: mở bằng draw.io / diagrams.net, chọn File → Open From → Device. Các bảng và đường nối có thể chỉnh sửa; mỗi cột có kiểu dữ liệu và tính nullable.
- `aquaponics_erd.mmd`: mã nguồn Mermaid ERD, dùng với trình xem hỗ trợ Mermaid. PK = khóa chính, FK = khóa ngoại, UK = khóa duy nhất một cột. Khóa duy nhất kết hợp và điều kiện index xem chính xác trong SQL. Quan hệ thể hiện theo FK và tính nullable/unique; đường nét đứt dùng thống nhất, không phân loại quan hệ định danh.
- `manifest.json`: số lượng đối tượng và commit nguồn.

## Sử dụng SQL

Chạy trên database PostgreSQL trống đã tạo sẵn:

```bash
psql -X -v ON_ERROR_STOP=1 -d ten_database_trong -f aquaponics_schema.sql
```

Script có transaction, không tạo database, không xóa bảng và không chứa dữ liệu người dùng, telemetry, tài khoản, mật khẩu hay seed catalog. Không bao gồm extension, TimescaleDB hypertable, role, quyền truy cập hoặc `alembic_version`. Các giá trị `default` / `onupdate` phía Python không tự trở thành default hay trigger PostgreSQL.

Đây là script dựng cấu trúc để bàn giao/tham khảo, không phải quy trình triển khai đầy đủ ứng dụng. Database đang có dữ liệu tiếp tục dùng Alembic theo hướng dẫn migration của dự án; không chạy script này để nâng cấp và không tự stamp head từ bản xuất này.

## Kiểm tra

Đã thực thi toàn bộ SQL thành công trên PostgreSQL 16 trong container tạm riêng với database `aquaponics_codex_schema_export`. Đếm lại từ PostgreSQL khớp 38 bảng, 466 cột, 80 khóa ngoại, 10 enum. Đã kiểm tra XML draw.io hợp lệ và đủ 80 đường nối FK. Chưa kiểm tra hiển thị ERD bằng ứng dụng đồ họa, chưa chạy migration upgrade/schema-equivalence với database triển khai. Không thay đổi database hoặc container dịch vụ đang chạy.
