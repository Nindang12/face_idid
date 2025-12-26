#!/bin/bash

# Script để setup môi trường cho Spark Streaming Worker
# Sử dụng: ./setup_spark_worker.sh

echo "🔧 Setting up Spark Streaming Worker environment..."

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.10+"
    exit 1
fi

echo "✅ Python3 found: $(python3 --version)"

# Tạo virtual environment nếu chưa có
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Cài đặt dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To run Spark Streaming Worker:"
echo "   source venv/bin/activate"
echo "   python -m app.spark_streaming"
echo ""
echo "💡 Or use the run script:"
echo "   ./run_spark_streaming.sh"

