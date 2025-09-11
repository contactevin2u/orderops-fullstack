-- PRODUCTION DATABASE MANUAL RESET
-- ⚠️  WARNING: This will DELETE ALL DATA ⚠️

-- Step 1: Drop all tables (be careful with order due to foreign keys)
DROP TABLE IF EXISTS ai_verification_logs CASCADE;
DROP TABLE IF EXISTS uid_ledger CASCADE;
DROP TABLE IF EXISTS lorry_stock_verifications CASCADE;
DROP TABLE IF EXISTS driver_holds CASCADE;
DROP TABLE IF EXISTS lorry_assignments CASCADE;
DROP TABLE IF EXISTS stock_transactions CASCADE;
DROP TABLE IF EXISTS lorry_stock CASCADE;
DROP TABLE IF EXISTS driver_devices CASCADE;
DROP TABLE IF EXISTS driver_shifts CASCADE;
DROP TABLE IF EXISTS trip_events CASCADE;
DROP TABLE IF EXISTS order_item_uids CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS commission_entries CASCADE;
DROP TABLE IF EXISTS upsell_records CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS drivers CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS export_runs CASCADE;
DROP TABLE IF EXISTS item CASCADE;
DROP TABLE IF EXISTS sku CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

-- Step 2: Drop custom enum types
DROP TYPE IF EXISTS uidaction CASCADE;
DROP TYPE IF EXISTS ledgerentrysource CASCADE;
DROP TYPE IF EXISTS tripstatus CASCADE;
DROP TYPE IF EXISTS orderstatus CASCADE;
DROP TYPE IF EXISTS paymentstatus CASCADE;
DROP TYPE IF EXISTS commissionstatus CASCADE;

-- Step 3: You would then run: alembic upgrade head
-- Step 4: Create admin user (see Python script above)