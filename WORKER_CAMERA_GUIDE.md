# 📹 Hướng Dẫn Sử Dụng Camera Trên Máy Worker

Hướng dẫn chi tiết cách mở và sử dụng camera để nhận diện khách hàng trên máy worker.

## 🎯 Mục Đích

Mỗi máy worker đại diện cho một chi nhánh. Camera trên máy worker sẽ:
- Tự động nhận diện khách hàng khi họ đến
- Tự động tạo khách hàng mới nếu chưa có trong hệ thống
- Hiển thị menu thanh toán với combo món thường mua
- Lưu lịch sử đơn hàng vào database

## 🚀 Các Bước Thực Hiện

### Bước 1: Đảm Bảo Máy Chủ Chính Đang Chạy

Trên máy chủ chính, kiểm tra web service đang chạy:

```bash
# Trên máy chủ chính
docker compose ps web
# Phải thấy: faceid-web  Up ...
```

### Bước 2: Kiểm Tra Kết Nối Từ Máy Worker

Trên máy worker, kiểm tra có thể truy cập web server:

```bash
# Thay ${HOST_IP} bằng IP máy chủ chính (ví dụ: 192.168.1.7)
curl http://${HOST_IP}:8000

# Hoặc mở trình duyệt và truy cập:
# http://${HOST_IP}:8000
```

### Bước 3: Mở Trang Camera

1. **Mở trình duyệt web** (Chrome, Firefox, Edge) trên máy worker
2. **Truy cập URL**: `http://${HOST_IP}:8000/camera`
   - Ví dụ: `http://192.168.1.7:8000/camera`
3. Trang camera sẽ hiển thị với:
   - Dropdown để chọn chi nhánh
   - Nút "Bắt Đầu" để khởi động camera
   - Nút "Dừng" để dừng camera
   - Khu vực hiển thị video từ camera
   - Khu vực hiển thị kết quả nhận diện

### Bước 4: Chọn Chi Nhánh

1. **Chọn chi nhánh** từ dropdown menu
   - Phải chọn đúng chi nhánh của máy worker này
   - Chi nhánh phải đã được tạo trên máy chủ chính
   - Xem danh sách chi nhánh tại: `http://${HOST_IP}:8000` → Tab "Quản Lý Chi Nhánh"

### Bước 5: Cho Phép Truy Cập Camera

1. **Click nút "Bắt Đầu"**
2. Trình duyệt sẽ hỏi quyền truy cập camera
3. **Chọn "Cho phép"** hoặc "Allow"
4. Camera sẽ bắt đầu streaming

### Bước 6: Sử Dụng

- Camera sẽ tự động chụp ảnh định kỳ (mặc định mỗi 2 giây)
- Hệ thống sẽ tự động nhận diện khuôn mặt
- **Nếu nhận diện được**: Hiển thị thông tin khách hàng và menu thanh toán
- **Nếu không nhận diện được**: Tự động tạo khách hàng mới và hiển thị menu thanh toán

## ⚠️ Lưu Ý Quan Trọng

### 1. Camera Chỉ Hoạt Động Trên HTTPS hoặc Localhost

**Vấn đề:**
- Trình duyệt hiện đại chỉ cho phép truy cập camera trên:
  - `https://` (HTTPS)
  - `http://localhost` hoặc `http://127.0.0.1`
- Nếu truy cập qua IP (ví dụ: `http://192.168.1.7:8000`), một số trình duyệt có thể chặn camera

**Giải pháp:**

#### Giải pháp 1: Sử dụng localhost (nếu máy worker = máy chủ)
```bash
# Nếu máy worker và máy chủ là cùng một máy
http://localhost:8000/camera
```

#### Giải pháp 2: Cấu hình HTTPS
Cài đặt SSL certificate và cấu hình HTTPS cho web server.

#### Giải pháp 3: Sử dụng ngrok (nhanh nhất cho development)
```bash
# Trên máy chủ chính
# Cài đặt ngrok: https://ngrok.com/download
ngrok http 8000

# Ngrok sẽ tạo URL HTTPS, ví dụ: https://abc123.ngrok.io
# Sử dụng URL này trên máy worker:
# https://abc123.ngrok.io/camera
```

#### Giải pháp 4: Cấu hình Chrome Flags (chỉ cho development)
```bash
# Chạy Chrome với flag cho phép camera trên HTTP
google-chrome --unsafely-treat-insecure-origin-as-secure=http://192.168.1.7:8000
```

### 2. Chọn Đúng Chi Nhánh

- Phải chọn đúng chi nhánh của máy worker này
- Chi nhánh phải đã được tạo trên máy chủ chính
- Nếu không có chi nhánh, tạo mới tại: `http://${HOST_IP}:8000` → Tab "Quản Lý Chi Nhánh"

### 3. Camera Đang Được Sử Dụng

- Đảm bảo camera không đang được sử dụng bởi ứng dụng khác
- Kiểm tra: `lsof | grep video` (Linux) hoặc Task Manager (Windows)

## 🐛 Troubleshooting

### Camera không hiển thị

1. **Kiểm tra quyền camera:**
   - Xem biểu tượng camera trên thanh địa chỉ trình duyệt
   - Click vào biểu tượng và cho phép truy cập

2. **Kiểm tra camera có hoạt động không:**
   ```bash
   # Linux
   ls -la /dev/video*
   v4l2-ctl --list-devices
   ```

3. **Kiểm tra console trình duyệt:**
   - Nhấn F12 để mở Developer Tools
   - Xem tab Console để tìm lỗi

### Lỗi "Cannot read properties of undefined (reading 'getUserMedia')"

- Xem hướng dẫn trong [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) phần "Lỗi Camera không hoạt động"
- Đảm bảo truy cập qua HTTPS hoặc localhost

### Không nhận diện được khách hàng

1. **Kiểm tra ánh sáng:** Đảm bảo đủ ánh sáng
2. **Kiểm tra khoảng cách:** Khách hàng phải ở khoảng cách hợp lý
3. **Kiểm tra khách hàng đã đăng ký chưa:** Xem danh sách tại `http://${HOST_IP}:8000` → Tab "Danh Sách Khách Hàng"

### Kết nối bị gián đoạn

1. **Kiểm tra mạng:**
   ```bash
   ping ${HOST_IP}
   curl http://${HOST_IP}:8000
   ```

2. **Kiểm tra firewall:**
   ```bash
   sudo ufw status
   # Đảm bảo port 8000 được mở
   ```

## 📊 Kiểm Tra Hoạt Động

### Xem Logs Nhận Diện

Truy cập: `http://${HOST_IP}:8000` → Tab "Logs"

### Xem Thống Kê

Truy cập: `http://${HOST_IP}:8000` → Tab "Thống Kê"

### Xem Database

Xem hướng dẫn trong [DATABASE_GUIDE.md](./DATABASE_GUIDE.md)

## ✅ Checklist

Trước khi sử dụng camera trên máy worker:

- [ ] Máy chủ chính đang chạy và web service hoạt động
- [ ] Có thể truy cập `http://${HOST_IP}:8000` từ máy worker
- [ ] Đã tạo chi nhánh trên máy chủ chính
- [ ] Đã chọn đúng chi nhánh trong dropdown
- [ ] Camera đã được cho phép truy cập
- [ ] Camera không đang được sử dụng bởi ứng dụng khác
- [ ] Đủ ánh sáng và điều kiện để nhận diện

## 📞 Hỗ Trợ

Nếu vẫn gặp vấn đề:
1. Xem [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Kiểm tra logs: `docker compose logs web` (trên máy chủ chính)
3. Kiểm tra console trình duyệt (F12)

