#!/bin/bash
# Railway Setup Script - Installs Playwright browsers after pip install

set -e

echo "🎭 Installing Playwright browsers for Railway deployment..."

# Set Playwright browsers path
export PLAYWRIGHT_BROWSERS_PATH=/tmp/ms-playwright

# Install Playwright browsers (Chromium only for efficiency)
echo "📦 Installing Chromium browser..."
playwright install chromium

# Try to install system dependencies (may fail but that's okay if nixpacks handles it)
echo "🔧 Installing system dependencies..."
playwright install-deps chromium || echo "⚠️ System deps install skipped (handled by nixpacks)"

echo "✅ Playwright setup complete"
echo "📁 Browsers installed at: $PLAYWRIGHT_BROWSERS_PATH"
