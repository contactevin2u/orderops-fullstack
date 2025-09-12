# Frontend-Backend Alignment Testing Checklist

## 🎯 Testing Objective

Validate that the frontend admin interface now shows **consistent inventory data** across both views after the comprehensive inventory system unification.

## 🔧 Test Environment Setup

### Prerequisites
1. **Backend server running** with unified inventory patches applied
2. **Frontend development server** with updated API calls  
3. **Test data**: Driver with lorry assignment and some UIDs loaded

### Test Driver Setup
```sql
-- Example test data setup (adjust for your system)
INSERT INTO drivers (name, phone) VALUES ('Test Driver', '+1234567890');
INSERT INTO lorry_assignments (driver_id, lorry_id, assignment_date, status) 
VALUES (2, 'VKE1343', '2025-01-15', 'ASSIGNED');

-- Load some test UIDs into the lorry (via admin or API)
INSERT INTO lorry_stock_transactions (lorry_id, action, uid, driver_id, transaction_date)
VALUES 
  ('VKE1343', 'LOAD', 'UID:SKU006-ADMIN-20250115-001-C1|SKU:6|TYPE:RENTAL', 2, NOW()),
  ('VKE1343', 'LOAD', 'UID:SKU006-ADMIN-20250115-002-C1|SKU:6|TYPE:RENTAL', 2, NOW()),
  ('VKE1343', 'LOAD', 'UID:SKU007-ADMIN-20250115-003-C1|SKU:7|TYPE:NEW', 2, NOW());
```

## ✅ Critical Test Cases

### Test 1: Backend Endpoint Parity
**Objective**: Verify both backend endpoints return identical data

```bash
# Test same driver and date on both endpoints
curl "http://localhost:8000/inventory/lorry/2/stock?date=2025-01-15"
curl "http://localhost:8000/inventory/drivers/2/stock-status?date=2025-01-15"

# Expected: Both should return same total_expected count
```

**✅ PASS Criteria**: 
- Both endpoints return same `total_expected` value
- Both show same number of items/UIDs
- Response structure includes event-sourced data

### Test 2: Frontend Admin Page Consistency  
**Objective**: Verify admin interface shows matching data in both views

**Steps**:
1. Navigate to `/admin/driver-stock`
2. Select test driver (ID: 2) 
3. Select test date (2025-01-15)
4. Compare both data views:
   - **Current Stock View** (left panel)
   - **Lorry Stock View** (right panel)

**✅ PASS Criteria**:
- Both views show **identical item counts**
- Both views display **same UIDs/SKUs**
- No "0 vs non-zero" discrepancies
- Date selector affects both views consistently

### Test 3: Date Scoping Validation
**Objective**: Ensure date parameter affects both views consistently

**Steps**:
1. Load stock data for multiple dates
2. Switch between dates in admin interface
3. Verify both views update together

**✅ PASS Criteria**:
- Changing date updates both current stock and lorry stock views
- No cached/stale data from previous date selections
- Both views show data for selected date only

### Test 4: Upload Workflow Integration
**Objective**: Verify stock count upload uses new backend route and payload

**Steps**:
1. Navigate to "Stock Count" tab in admin interface
2. Enter counted quantities for available SKUs
3. Submit stock count upload
4. Verify response and reconciliation data

**✅ PASS Criteria**:
- Upload succeeds without 404/400 errors
- Response includes reconciliation data (variance calculations)
- Backend receives data in expected format (`as_of_date`, `lines` array)
- Morning verification workflow shows correct expected vs counted

### Test 5: Error Handling & Validation
**Objective**: Verify proper error responses for invalid scenarios

**Steps**:
1. Try accessing stock without date parameter (should gracefully handle)
2. Try accessing non-existent driver data
3. Try invalid date formats

**✅ PASS Criteria**:
- Meaningful error messages displayed to user
- No console errors for expected failure scenarios
- Graceful degradation when backend unavailable

## 🐛 Common Issues & Debugging

### Issue: "Current Stock shows 0, Lorry Stock shows N"
**Cause**: Frontend still calling old endpoints or not passing date
**Fix**: Check network tab - both calls should hit unified routes with date parameter

### Issue: Upload fails with 400/404 error  
**Cause**: Frontend using old payload format or route
**Fix**: Verify request goes to `/inventory/lorry/{driverId}/stock/upload` with `as_of_date` + `lines`

### Issue: Date changes don't affect one of the views
**Cause**: One view not receiving date parameter
**Fix**: Verify both `getDriverStockStatus()` and `getLorryStock()` called with `selectedDate`

### Issue: "UID not in lorry" errors during delivery
**Cause**: Driver trying to deliver UID not actually in their assigned lorry
**Fix**: This is expected behavior - verify UID is properly loaded before delivery

## 📊 Success Metrics

### Consistency Achieved ✅
- [ ] Both admin views show identical counts for same driver/date
- [ ] Backend endpoint responses match each other
- [ ] Frontend date selection affects both views
- [ ] Upload workflow uses unified backend routes

### Performance Maintained ✅  
- [ ] Page load times acceptable (< 2 seconds for stock data)
- [ ] Date switching responsive (< 1 second)
- [ ] Upload operations complete successfully

### User Experience Improved ✅
- [ ] No more conflicting inventory numbers
- [ ] Clear error messages when issues occur  
- [ ] Consistent data across all admin interfaces

## 🚀 Production Readiness

### Pre-Deployment Checklist
- [ ] All test cases pass in staging environment
- [ ] Database migrations applied (if any)
- [ ] Backend unified inventory patches deployed
- [ ] Frontend API alignment patches deployed
- [ ] Operations team trained on new hold management workflow

### Monitoring Points
- [ ] Set up alerting if lorry/stock-status endpoints ever disagree
- [ ] Monitor morning verification completion rates
- [ ] Track driver hold duration and release frequency
- [ ] Watch for 409 errors indicating assignment issues

---

## 🎉 Expected Outcome

After all patches applied, the admin should see:

**Before (Broken)**:
- Current Stock: 0 items
- Lorry Stock: 4 items  
- ❌ Conflicting data causing confusion

**After (Fixed)**:  
- Current Stock: 4 items ✅
- Lorry Stock: 4 items ✅  
- ✅ Consistent event-sourced truth

The two inventory worlds are now one! 🎯