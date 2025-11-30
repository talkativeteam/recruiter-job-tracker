#!/bin/bash
# Setup Script for Recruiter ICP Job Tracker

set -e  # Exit on any error

echo "🚀 Setting up Recruiter ICP Job Tracker..."
echo ""

# Check Python version
echo "1️⃣ Checking Python version..."
python3 --version || { echo "❌ Python 3 not found. Please install Python 3.9+"; exit 1; }
echo "✅ Python installed"
echo ""

# Create virtual environment
echo "2️⃣ Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "3️⃣ Activating virtual environment..."
source venv/bin/activate || { echo "❌ Failed to activate venv"; exit 1; }
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "4️⃣ Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Install Playwright
echo "5️⃣ Installing Playwright browsers..."
playwright install chromium
echo "✅ Playwright installed"
echo ""

# Check .env file
echo "6️⃣ Checking environment variables..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.template .env
    echo "⚠️  IMPORTANT: Edit .env and add your API keys!"
    echo ""
    echo "Required API keys:"
    echo "  - OPENAI_API_KEY (get from: https://platform.openai.com/api-keys)"
    echo "  - APIFY_API_KEY (get from: https://console.apify.com/account/integrations)"
    echo "  - EXA_API_KEY (get from: https://exa.ai/)"
    echo "  - SUPABASE_URL (get from: https://supabase.com/dashboard)"
    echo "  - SUPABASE_KEY (get from: https://supabase.com/dashboard)"
    echo ""
    echo "After adding keys, run this script again."
    exit 1
else
    echo "✅ .env file exists"
fi
echo ""

# Validate config
echo "7️⃣ Validating configuration..."
python3 -c "
import sys
sys.path.append('.')
from config.config import validate_config
try:
    validate_config()
    print('✅ Configuration valid')
except ValueError as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
" || {
    echo ""
    echo "⚠️  Configuration validation failed."
    echo "Please check your .env file has all required API keys."
    exit 1
}
echo ""

# Test validation script
echo "8️⃣ Testing validation script..."
python3 execution/validate_input.py \
    --input sample_input.json \
    --output .tmp/test_validated.json || {
    echo "❌ Validation test failed"
    echo "This might be normal if Supabase table isn't created yet."
}
echo ""

echo "✅ Setup complete!"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Go to Supabase SQL Editor: https://supabase.com/dashboard"
echo "2. Run the SQL in: config/supabase_setup.sql"
echo "3. Test your first run:"
echo "   python3 execution/validate_input.py --input sample_input.json --output .tmp/test.json"
echo ""
echo "4. See QUICKSTART.md for complete walkthrough"
echo ""
