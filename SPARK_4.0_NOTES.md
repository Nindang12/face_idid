# Lưu Ý Cho Spark 4.0.0

## 📦 Package Version

Spark 4.0.0 sử dụng **Scala 2.13**, nên package phải là:
```
org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0
```

## ⚠️ Nếu Package 4.0.0 Không Tồn Tại

Nếu `spark-sql-kafka-0-10_2.13:4.0.0` không tồn tại trên Maven, bạn có thể:

### Option 1: Dùng Version Gần Nhất (Khuyến nghị)
```bash
# Thử dùng version 3.6.0 hoặc 3.5.0 (thường tương thích)
--packages org.apache.spark:spark-sql-kafka-0-10_2.13:3.6.0
```

### Option 2: Build Từ Source
Nếu cần version 4.0.0 chính xác, có thể cần build từ Spark source code.

### Option 3: Kiểm Tra Maven Repository
```bash
# Kiểm tra package có tồn tại không
curl https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.13/
```

## 🔧 Cấu Hình Spark 4.0.0

Spark 4.0.0 có một số thay đổi:

1. **Java Version**: Yêu cầu Java 17 hoặc 21
2. **Scala Version**: 2.13
3. **Python**: 3.9+

### Kiểm Tra Java Version
```bash
java -version
# Phải là Java 17 hoặc 21
```

### Kiểm Tra Spark Version
```bash
$SPARK_HOME/bin/spark-submit --version
# Phải hiển thị Spark 4.0.0
```

## 🚀 Chạy Với Spark 4.0.0

```bash
export SPARK_HOME=/path/to/spark-4.0.0-bin-hadoop3
export SPARK_MASTER=spark://192.168.1.23:7077

$SPARK_HOME/bin/spark-submit \
  --master $SPARK_MASTER \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --conf "spark.sql.streaming.checkpointLocation=/tmp/spark-checkpoint-face-recognition" \
  spark_kafka_stream.py
```

## 🐛 Troubleshooting

### Lỗi: Package không tìm thấy
```
Error: Could not find or load main class org.apache.spark.deploy.SparkSubmit
```

**Giải pháp:**
1. Kiểm tra package version có đúng không
2. Thử dùng version gần nhất (3.6.0)
3. Kiểm tra internet connection (cần download từ Maven)

### Lỗi: Java version không đúng
```
Error: UnsupportedClassVersionError
```

**Giải pháp:**
```bash
# Cài Java 17 hoặc 21
sudo apt install openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

### Lỗi: Scala version mismatch
```
Error: scala.MatchError
```

**Giải pháp:**
- Đảm bảo dùng `_2.13` cho Spark 4.0.0
- Không dùng `_2.12` (cho Spark 3.x)

## 📚 Tài Liệu Tham Khảo

- Spark 4.0.0 Documentation: https://spark.apache.org/docs/4.0.0/
- Spark SQL Kafka Integration: https://spark.apache.org/docs/4.0.0/structured-streaming-kafka-integration.html

