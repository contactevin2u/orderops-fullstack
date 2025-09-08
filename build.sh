#!/bin/bash
set -e

echo "🔥 CUSTOM BUILD SCRIPT: Fix migration mess and deploy"

# Navigate to backend
cd backend

echo "📋 Current migration heads:"
alembic heads || echo "Failed to show heads (expected)"

echo "🎯 Force stamp to target revision..."
alembic stamp 20250908_final_convergence

echo "📋 Heads after stamp:"
alembic heads

echo "🚀 Upgrade to head..."
alembic upgrade head

echo "✅ Migration fix complete!"