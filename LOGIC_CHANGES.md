# GateSeal Logic Changes: Removal of `is_used` Flag

## Summary

Simplified GateSeal logic by removing the redundant `is_used` boolean flag and implementing immediate expiry after seal activation.

## Motivation

The `is_used` flag was redundant because:
1. GateSeal is conceptually a one-time panic button
2. After activation, it should be immediately unavailable for reuse
3. This can be achieved by setting `expiry_timestamp = block.timestamp` after use
4. All checks can use `is_expired()` instead of separate `is_used` checks

## Changes Made

### Contract Changes (`contracts/GateSeal.vy`)

1. **Removed `is_used` storage variable**
   ```vyper
   # REMOVED:
   is_used: public(bool)
   ```

2. **Updated constructor - removed is_used initialization**
   ```vyper
   # REMOVED:
   self.is_used = False
   ```

3. **Updated `seal()` function**
   ```vyper
   # BEFORE:
   assert not self.is_used, "gate seal already used"
   self.is_used = True
   
   # AFTER:
   assert block.timestamp < self.expiry_timestamp, "gate seal expired"
   # Expire immediately after use - this is a one-time panic button
   self.expiry_timestamp = block.timestamp
   ```

4. **Updated `get_seal_info()` return type**
   ```vyper
   # BEFORE: returned 9 values including is_used
   # AFTER: returns 8 values without is_used
   ```

### Test Changes (`tests/test_gate_seal.py`)

1. **Updated parameter checks**
   ```python
   # BEFORE:
   assert info[8] == False  # is_used
   
   # AFTER:
   assert gate_seal.is_expired() == False  # not expired initially
   ```

2. **Updated post-seal checks**
   ```python
   # BEFORE:
   assert gate_seal.is_used() == True
   
   # AFTER:
   assert gate_seal.is_expired() == True
   ```

3. **Updated reuse attempt tests**
   ```python
   # BEFORE:
   with pytest.raises(ContractLogicError, match="gate seal already used"):
   
   # AFTER:
   with pytest.raises(ContractLogicError, match="gate seal expired"):
   ```

4. **Added comprehensive test for immediate expiry**
   - `test_gate_seal_expires_immediately_after_use()`
   - Verifies expiry timestamp changes from future to current time
   - Confirms both seal reuse and prolongation are blocked after use

## Benefits

1. **Simplified Logic**: One expiry mechanism instead of two separate states
2. **Clearer Semantics**: "Expired" is more intuitive than "Used" for a time-based contract
3. **Reduced Gas**: Saves storage slot and operations
4. **Consistent Behavior**: All time-based restrictions use same expiry mechanism

## Backward Compatibility

⚠️ **Breaking Changes:**
- `get_seal_info()` now returns 8 values instead of 9
- `is_used()` public getter is no longer available
- Error messages changed from "gate seal already used" to "gate seal expired"

## Testing

The new logic maintains all security properties while simplifying the implementation:

1. ✅ GateSeal can only be used once (enforced by immediate expiry)
2. ✅ GateSeal cannot be used after natural expiry  
3. ✅ GateSeal cannot be prolonged after use
4. ✅ All original functionality preserved with cleaner logic

## Verification

Run the updated test suite to verify the changes:

```bash
ape test tests/test_gate_seal.py::test_gate_seal_expires_immediately_after_use
ape test tests/test_gate_seal.py::test_seal_success_with_valid_sealables  
ape test tests/test_gate_seal.py::test_seal_fails_if_already_used
```

The logic change is complete and maintains all security guarantees while improving code clarity.