FROM python:3.11-slim

# Thư mục làm việc gốc của project trong container
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy nguồn ứng dụng vào /code/app để giữ nguyên package name `app`
COPY app/ /code/app

# Tạo thư mục lưu uploads và known_faces (bên trong package `app`)
RUN mkdir -p /code/app/uploads /code/app/known_faces

EXPOSE 8000

# Chạy FastAPI app với module `app.main:app`
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

