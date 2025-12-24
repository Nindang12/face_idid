# 📊 Hướng Dẫn Xem Dữ Liệu Trong Database

Tài liệu này hướng dẫn các cách xem và quản lý dữ liệu trong PostgreSQL database của hệ thống.

---

## 🔑 Thông Tin Kết Nối

- **Database Type:** PostgreSQL 15
- **Container Name:** `faceid-postgres`
- **Database Name:** `faceid`
- **Username:** `faceid`
- **Password:** `faceid123`
- **Host Port:** `5433` (mapped từ container port 5432)
- **Container Port:** `5432`

---

## 📋 Các Bảng Trong Database

1. **branches** - Thông tin chi nhánh
2. **customers** - Thông tin khách hàng
3. **orders** - Đơn hàng
4. **recognition_logs** - Logs nhận diện khuôn mặt

---

## 🚀 Cách 1: Sử dụng psql trong Container (Khuyên dùng)

### Kết nối vào PostgreSQL:
```bash
docker compose exec postgres psql -U faceid -d faceid
```

### Các lệnh cơ bản:

#### Xem danh sách tables:
```sql
\dt
```

#### Xem cấu trúc bảng:
```sql
\d branches
\d customers
\d orders
\d recognition_logs
```

#### Xem tất cả dữ liệu trong bảng:

**Branches (Chi nhánh):**
```sql
SELECT * FROM branches;
```

**Customers (Khách hàng):**
```sql
SELECT * FROM customers;
```

**Orders (Đơn hàng):**
```sql
SELECT * FROM orders;
```

**Recognition Logs:**
```sql
SELECT * FROM recognition_logs ORDER BY created_at DESC;
```

#### Xem dữ liệu với format đẹp:
```sql
\x  -- Bật expanded display
SELECT * FROM customers LIMIT 5;
\x  -- Tắt expanded display
```

#### Đếm số lượng records:
```sql
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM recognition_logs;
```

#### Thoát khỏi psql:
```sql
\q
```

---

## 🚀 Cách 2: Sử dụng lệnh một dòng (One-liner)

### Xem tất cả customers:
```bash
docker compose exec postgres psql -U faceid -d faceid -c "SELECT * FROM customers;"
```

### Xem customers với format đẹp:
```bash
docker compose exec postgres psql -U faceid -d faceid -c "\x" -c "SELECT * FROM customers LIMIT 5;"
```

### Xem orders:
```bash
docker compose exec postgres psql -U faceid -d faceid -c "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;"
```

### Xem branches:
```bash
docker compose exec postgres psql -U faceid -d faceid -c "SELECT * FROM branches;"
```

### Xem recognition logs:
```bash
docker compose exec postgres psql -U faceid -d faceid -c "SELECT * FROM recognition_logs ORDER BY created_at DESC LIMIT 20;"
```

---

## 🚀 Cách 3: Sử dụng Client Tool (pgAdmin, DBeaver, etc.)

### Kết nối từ máy host:

**Connection Settings:**
- **Host:** `localhost` hoặc `127.0.0.1`
- **Port:** `5433`
- **Database:** `faceid`
- **Username:** `faceid`
- **Password:** `faceid123`

### pgAdmin:
1. Download và cài đặt pgAdmin: https://www.pgadmin.org/
2. Tạo new server:
   - Name: `FaceID Local`
   - Host: `localhost`
   - Port: `5433`
   - Database: `faceid`
   - Username: `faceid`
   - Password: `faceid123`

### DBeaver:
1. Download DBeaver: https://dbeaver.io/
2. Tạo new connection → PostgreSQL
3. Điền thông tin:
   - Host: `localhost`
   - Port: `5433`
   - Database: `faceid`
   - Username: `faceid`
   - Password: `faceid123`

### VS Code Extension (SQLTools):
1. Cài extension "SQLTools" và "SQLTools PostgreSQL/Redshift"
2. Tạo connection với thông tin trên

---

## 📊 Các Query Hữu Ích

### 1. Xem thống kê tổng quan:
```sql
-- Tổng số khách hàng
SELECT COUNT(*) as total_customers FROM customers;

-- Tổng số đơn hàng
SELECT COUNT(*) as total_orders FROM orders;

-- Tổng số chi nhánh
SELECT COUNT(*) as total_branches FROM branches;

-- Tổng số lần nhận diện
SELECT COUNT(*) as total_recognitions FROM recognition_logs;
```

### 2. Xem khách hàng với thông tin chi tiết:
```sql
SELECT 
    id,
    name,
    phone,
    email,
    face_encoding_path,
    created_at,
    is_active
FROM customers
ORDER BY created_at DESC;
```

### 3. Xem đơn hàng với thông tin khách hàng và chi nhánh:
```sql
SELECT 
    o.id,
    o.created_at,
    c.name as customer_name,
    c.phone as customer_phone,
    b.name as branch_name,
    o.items,
    o.total_amount,
    o.status
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN branches b ON o.branch_id = b.id
ORDER BY o.created_at DESC
LIMIT 20;
```

### 4. Xem thống kê đơn hàng theo khách hàng:
```sql
SELECT 
    c.id,
    c.name,
    COUNT(o.id) as total_orders,
    SUM(o.total_amount) as total_spent,
    AVG(o.total_amount) as avg_order_value
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY total_spent DESC;
```

### 5. Xem thống kê đơn hàng theo chi nhánh:
```sql
SELECT 
    b.id,
    b.name,
    COUNT(o.id) as total_orders,
    SUM(o.total_amount) as total_revenue,
    COUNT(DISTINCT o.customer_id) as unique_customers
FROM branches b
LEFT JOIN orders o ON b.id = o.branch_id
GROUP BY b.id, b.name
ORDER BY total_revenue DESC;
```

### 6. Xem logs nhận diện với thông tin chi tiết:
```sql
SELECT 
    rl.id,
    rl.created_at,
    c.name as customer_name,
    b.name as branch_name,
    rl.confidence,
    rl.recognized,
    rl.image_path
FROM recognition_logs rl
LEFT JOIN customers c ON rl.customer_id = c.id
LEFT JOIN branches b ON rl.branch_id = b.id
ORDER BY rl.created_at DESC
LIMIT 50;
```

### 7. Xem khách hàng mới nhất:
```sql
SELECT 
    id,
    name,
    phone,
    email,
    created_at
FROM customers
ORDER BY created_at DESC
LIMIT 10;
```

### 8. Xem đơn hàng của một khách hàng cụ thể:
```sql
-- Thay <customer_id> bằng ID khách hàng
SELECT 
    o.id,
    o.created_at,
    b.name as branch_name,
    o.items,
    o.total_amount,
    o.status
FROM orders o
JOIN branches b ON o.branch_id = b.id
WHERE o.customer_id = <customer_id>
ORDER BY o.created_at DESC;
```

### 9. Xem đơn hàng tại một chi nhánh cụ thể:
```sql
-- Thay <branch_id> bằng ID chi nhánh
SELECT 
    o.id,
    o.created_at,
    c.name as customer_name,
    o.items,
    o.total_amount,
    o.status
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.branch_id = <branch_id>
ORDER BY o.created_at DESC;
```

### 10. Xem tỷ lệ nhận diện thành công:
```sql
SELECT 
    COUNT(*) as total_attempts,
    SUM(CASE WHEN recognized = true THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN recognized = false THEN 1 ELSE 0 END) as failed,
    ROUND(
        100.0 * SUM(CASE WHEN recognized = true THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as success_rate_percent
FROM recognition_logs;
```

---

## 🔍 Tìm Kiếm và Lọc Dữ Liệu

### Tìm khách hàng theo tên:
```sql
SELECT * FROM customers 
WHERE name ILIKE '%tên%';
```

### Tìm khách hàng theo số điện thoại:
```sql
SELECT * FROM customers 
WHERE phone LIKE '%số_điện_thoại%';
```

### Tìm đơn hàng trong khoảng thời gian:
```sql
SELECT * FROM orders 
WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31'
ORDER BY created_at DESC;
```

### Tìm đơn hàng có giá trị lớn hơn:
```sql
SELECT * FROM orders 
WHERE total_amount > 100000
ORDER BY total_amount DESC;
```

---

## 📤 Export Dữ Liệu

### Export ra CSV:
```bash
docker compose exec postgres psql -U faceid -d faceid -c "
COPY (SELECT * FROM customers) TO STDOUT WITH CSV HEADER;
" > customers.csv
```

### Export ra file SQL:
```bash
docker compose exec postgres pg_dump -U faceid -d faceid > backup.sql
```

### Export một bảng cụ thể:
```bash
docker compose exec postgres pg_dump -U faceid -d faceid -t customers > customers_backup.sql
```

---

## 🔧 Quản Lý Database

### Backup database:
```bash
docker compose exec postgres pg_dump -U faceid faceid > faceid_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore database:
```bash
docker compose exec -T postgres psql -U faceid -d faceid < backup.sql
```

### Xóa tất cả dữ liệu (CẨN THẬN!):
```sql
-- Trong psql
TRUNCATE TABLE recognition_logs CASCADE;
TRUNCATE TABLE orders CASCADE;
TRUNCATE TABLE customers CASCADE;
TRUNCATE TABLE branches CASCADE;
```

### Reset database (xóa và tạo lại):
```bash
docker compose down -v  # Xóa volumes
docker compose up -d postgres
# Đợi postgres khởi động
docker compose up -d web  # Web sẽ tự động tạo lại tables
```

---

## 🛠️ Script Tiện Ích

### Tạo file script để xem dữ liệu nhanh:

**File: `view_db.sh`**
```bash
#!/bin/bash

echo "=== DANH SÁCH CHI NHÁNH ==="
docker compose exec postgres psql -U faceid -d faceid -c "SELECT id, name, location FROM branches;"

echo -e "\n=== DANH SÁCH KHÁCH HÀNG (10 người đầu) ==="
docker compose exec postgres psql -U faceid -d faceid -c "SELECT id, name, phone, email FROM customers LIMIT 10;"

echo -e "\n=== TỔNG SỐ ĐƠN HÀNG ==="
docker compose exec postgres psql -U faceid -d faceid -c "SELECT COUNT(*) as total FROM orders;"

echo -e "\n=== ĐƠN HÀNG GẦN NHẤT (5 đơn) ==="
docker compose exec postgres psql -U faceid -d faceid -c "SELECT id, customer_id, branch_id, total_amount, created_at FROM orders ORDER BY created_at DESC LIMIT 5;"

echo -e "\n=== LOGS NHẬN DIỆN GẦN NHẤT (10 logs) ==="
docker compose exec postgres psql -U faceid -d faceid -c "SELECT id, customer_id, branch_id, recognized, confidence, created_at FROM recognition_logs ORDER BY created_at DESC LIMIT 10;"
```

**Sử dụng:**
```bash
chmod +x view_db.sh
./view_db.sh
```

---

## 📝 Lưu Ý

1. **Port:** Nhớ sử dụng port `5433` khi kết nối từ máy host (không phải 5432)
2. **Password:** Mặc định là `faceid123`, có thể thay đổi trong file `.env`
3. **Backup:** Luôn backup trước khi xóa hoặc sửa dữ liệu quan trọng
4. **Permissions:** Đảm bảo container đang chạy trước khi kết nối

---

## 🆘 Troubleshooting

### Không kết nối được:
```bash
# Kiểm tra container có đang chạy không
docker compose ps postgres

# Kiểm tra logs
docker compose logs postgres

# Kiểm tra port
netstat -tulpn | grep 5433
```

### Lỗi authentication:
- Kiểm tra username/password trong `.env`
- Đảm bảo đã restart container sau khi thay đổi `.env`

### Lỗi "database does not exist":
```bash
# Tạo database (nếu cần)
docker compose exec postgres psql -U faceid -c "CREATE DATABASE faceid;"
```

---

**Chúc bạn sử dụng thành công! 🎉**

