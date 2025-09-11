# Production Database Reset Guide

⚠️ **CRITICAL WARNING: This will DELETE ALL DATA permanently** ⚠️

## Method 1: Python Reset Script (Recommended)

```bash
cd backend
python reset_production_db.py
```

This will:
1. Ask for double confirmation
2. Drop all tables and enums
3. Re-run all migrations
4. Create fresh admin user (admin/admin123)

## Method 2: Render Dashboard (Easiest)

1. Go to your Render dashboard
2. Find your PostgreSQL database service
3. Click "Reset Database" 
4. Confirm the reset
5. Wait for completion
6. Run: `alembic upgrade head` to recreate tables
7. Create admin user manually

## Method 3: Manual SQL Reset

1. Connect to your database
2. Run the commands in `manual_reset.sql`
3. Run: `alembic upgrade head`
4. Create admin user

## Method 4: Environment Variable Reset

If you want to start completely fresh:

1. In Render dashboard, go to your web service
2. Environment Variables
3. Change `DATABASE_URL` to point to a new empty database
4. Deploy the service
5. Run migrations: `alembic upgrade head`

## After Reset

Your database will be completely empty with:
- ✅ Fresh database schema
- ✅ Default admin user: `admin` / `admin123`
- ❌ No orders, drivers, customers, or any other data
- ❌ All previous data permanently lost

## Recovery

**There is NO RECOVERY after this operation.** Make sure you have backups if needed.

## Pre-Reset Checklist

- [ ] Confirmed you want to lose ALL data
- [ ] Notified all users about downtime
- [ ] Have backup if recovery might be needed
- [ ] Double-checked you're targeting the right database
- [ ] Ready to recreate users, drivers, and configuration

## Post-Reset Setup

1. Login with admin/admin123
2. Create your actual admin users
3. Create driver accounts
4. Set up customers and SKUs
5. Configure system settings
6. Test the system end-to-end