#!/bin/bash
# Railway Setup Script - Installs Playwright browsers after pip install

set -e

echo "🎭 Installing Playwright browsers for Railway deployment..."

# Install Playwright browsers (Chromium only for efficiency)
playwright install chromium

# Install system dependencies for Chromium
playwright install-deps chromium || echo "⚠️ Could not install system deps (may need Railway nixpacks config)"

echo "✅ Playwright setup complete"
