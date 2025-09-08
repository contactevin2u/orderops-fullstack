#!/bin/bash
echo "🔥 EMERGENCY DEPLOYMENT: Force stamp and upgrade"

cd backend

echo "Step 1: Show current migration state"
alembic heads

echo "Step 2: Force stamp to our target revision"
alembic stamp 20250908_final_convergence

echo "Step 3: Verify single head"
alembic heads

echo "Step 4: Upgrade to head (should work now)"
alembic upgrade head

echo "✅ Deployment complete"