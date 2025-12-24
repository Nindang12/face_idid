#!/bin/bash

# Script để kiểm tra trạng thái và dữ liệu trên MinIO

echo "🔍 Kiểm tra cấu hình MinIO..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Lỗi: File .env không tìm thấy. Vui lòng tạo file .env từ .env.example."
    exit 1
fi

if [ -z "$MINIO_ENDPOINT" ]; then
    echo "❌ Lỗi: Biến môi trường MINIO_ENDPOINT chưa được set trong .env."
    exit 1
fi

if [ -z "$MINIO_BUCKET_NAME" ]; then
    echo "❌ Lỗi: Biến môi trường MINIO_BUCKET_NAME chưa được set trong .env."
    exit 1
fi

echo "✅ Cấu hình MinIO:"
echo "   - MINIO_ENDPOINT: $MINIO_ENDPOINT"
echo "   - MINIO_BUCKET_NAME: $MINIO_BUCKET_NAME"
echo "   - MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:-minioadmin}"
echo ""

# Kiểm tra kết nối MinIO bằng Python
echo "📊 Kiểm tra kết nối MinIO..."
python3 << PYTHON_SCRIPT
import sys
from minio import Minio
from minio.error import S3Error

try:
    endpoint = "${MINIO_ENDPOINT}"
    access_key = "${MINIO_ACCESS_KEY:-minioadmin}"
    secret_key = "${MINIO_SECRET_KEY:-minioadmin123}"
    bucket_name = "${MINIO_BUCKET_NAME}"
    
    minio_client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False
    )
    
    # Kiểm tra kết nối bằng cách list buckets
    buckets = minio_client.list_buckets()
    print("✅ MinIO đang hoạt động.")
    print(f"   Số lượng buckets: {len(list(buckets))}")
    
    # Kiểm tra bucket có tồn tại không
    if minio_client.bucket_exists(bucket_name):
        print(f"✅ Bucket '{bucket_name}' tồn tại.")
        
        # Liệt kê objects trong bucket
        objects = list(minio_client.list_objects(bucket_name, recursive=True))
        print(f"   Số lượng objects: {len(objects)}")
        
        if objects:
            print("\n📄 Danh sách objects (10 đầu tiên):")
            for i, obj in enumerate(objects[:10]):
                print(f"   - {obj.object_name} ({obj.size} bytes)")
            if len(objects) > 10:
                print(f"   ... và {len(objects) - 10} objects khác")
    else:
        print(f"⚠️  Bucket '{bucket_name}' KHÔNG tồn tại. Đang tạo...")
        minio_client.make_bucket(bucket_name)
        print(f"✅ Đã tạo bucket '{bucket_name}'.")
    
except S3Error as e:
    print(f"❌ MinIO S3Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Lỗi khi kết nối MinIO: {e}")
    print("   Vui lòng kiểm tra:")
    print("   1. MinIO container đã chạy chưa: docker ps | grep minio")
    print("   2. MinIO endpoint có đúng không: $MINIO_ENDPOINT")
    print("   3. Firewall có chặn port 9000 không")
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Kiểm tra MinIO hoàn tất."
    echo ""
    echo "💡 Truy cập MinIO Console:"
    echo "   http://${MINIO_ENDPOINT%:*}:9001"
    echo "   Username: ${MINIO_ACCESS_KEY:-minioadmin}"
    echo "   Password: ${MINIO_SECRET_KEY:-minioadmin123}"
else
    echo ""
    echo "❌ Kiểm tra MinIO thất bại."
    exit 1
fi

