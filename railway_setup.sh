#!/bin/bash
# Railway Setup Script - GUARANTEED Playwright browser installation

set -e

echo "🎭 Installing Playwright browsers for Railway deployment..."

# Set Playwright browsers path (writable on Railway)
export PLAYWRIGHT_BROWSERS_PATH=/tmp/ms-playwright

# Ensure directory exists
mkdir -p $PLAYWRIGHT_BROWSERS_PATH

# Install Playwright browsers with retry logic
echo "📦 Installing Chromium browser..."
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if playwright install chromium; then
        echo "✅ Chromium installed successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⚠️ Attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying..."
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ CRITICAL: Failed to install Chromium after $MAX_RETRIES attempts"
    exit 1
fi

# Verify installation
if [ -d "$PLAYWRIGHT_BROWSERS_PATH/chromium-1097" ] || playwright install chromium --dry-run 2>&1 | grep -q "is already installed"; then
    echo "✅ Playwright setup complete"
    echo "📁 Browsers installed at: $PLAYWRIGHT_BROWSERS_PATH"
else
    echo "❌ CRITICAL: Browser installation verification failed"
    exit 1
fi
