#!/bin/bash
# Streamlit Dashboard Başlatma Scripti

cd "$(dirname "$0")"

# Virtual environment kontrolü
if [ ! -d "venv" ]; then
    echo "🔧 Virtual environment oluşturuluyor..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install dependencies
echo "📦 Bağımlılıklar yükleniyor..."
pip install -q -r requirements.txt

# Run Streamlit
echo "🚀 Dashboard başlatılıyor..."
echo "📍 http://localhost:8501"
streamlit run app.py --server.port 8501 --server.headless true
