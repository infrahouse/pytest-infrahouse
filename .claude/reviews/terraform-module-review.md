# pytest-infrahouse PR Changes Review

**Last Updated:** 2025-12-05

---

## Executive Summary

This PR introduces a utility function `wait_for_instance_refresh()` to handle AWS Auto Scaling Group instance refresh operations in pytest-infrahouse tests. The changes are **primarily Python code** (not Terraform), adding infrastructure testing support for ASG instance refresh scenarios.

**Overall Assessment:** ✅ **APPROVED with Minor Recommendations**

The implementation is well-designed, follows Python best practices, includes proper error handling, and adds valuable testing capabilities. The changes are focused, non-breaking, and improve the robustness of infrastructure tests that involve ASG instance refreshes.

---

## Summary of Changes

### Files Modified

1. **`src/pytest_infrahouse/__init__.py`**
   - Changed file mode from 644 to 755 (executable)
   - Added logging import
   - Added shared constants: `LOG` and `DEFAULT_PROGRESS_INTERVAL`
   - Moved constants from terraform.py to __init__.py for shared access

2. **`src/pytest_infrahouse/terraform.py`**
   - Changed file mode from 644 to 755 (executable)
   - Imported shared constants from __init__.py
   - Removed duplicate LOG and DEFAULT_PROGRESS_INTERVAL definitions

3. **`src/pytest_infrahouse/utils.py`** (NEW FILE)
   - Created new utility module
   - Added `wait_for_instance_refresh()` function
   - Comprehensive error handling and logging
   - Timeout and polling mechanism for ASG instance refreshes

### Key Changes by Category

**Refactoring:**
- Moved `LOG` and `DEFAULT_PROGRESS_INTERVAL` from terraform.py to __init__.py for shared access across modules
- No breaking changes to existing functionality

**New Functionality:**
- `wait_for_instance_refresh()` utility function for monitoring ASG instance refresh operations
- Supports timeout configuration (default 3600 seconds)
- Supports poll interval configuration (default 10 seconds)
- Detects and reports failed refreshes
- Provides detailed progress logging with percentage completion

**Error Handling:**
- TimeoutError for refresh operations that exceed timeout
- RuntimeError for failed/cancelled refreshes or missing ASGs
- Proper ClientError handling for AWS API errors
- Comprehensive error messages with context

---

## Security Assessment

### ✅ Security Strengths

1. **No Credential Exposure:**
   - No hardcoded credentials or secrets
   - Uses boto3 client passed as parameter (follows dependency injection)
   - No sensitive data logged

2. **Proper AWS Client Usage:**
   - Uses boto3 autoscaling client passed as parameter
   - No direct credential handling in the utility function
   - Follows the established pattern from other fixtures

3. **Input Validation:**
   - Uses type hints for parameters
   - Validates timeout and poll_interval as integers
   - Proper parameter validation through Python typing

4. **Error Information Disclosure:**
   - Error messages provide useful debugging context
   - No exposure of sensitive infrastructure details beyond what AWS API returns
   - Appropriate use of `exc_info=True` for stack traces

### ⚠️ Security Considerations

1. **File Permissions Change (Low Risk):**
   - Files changed to executable (mode 755)
   - **Impact:** Minimal - Python files don't need to be executable
   - **Recommendation:** Revert to 644 unless there's a specific requirement

2. **ASG Name Injection (Low Risk):**
   - `asg_name` parameter could theoretically be used maliciously
   - **Mitigation:** AWS API validates ASG names, boto3 handles escaping
   - **Impact:** Minimal in testing context

### 🔒 Security Best Practices Followed

- ✅ No secrets in code
- ✅ Proper exception handling
- ✅ Uses AWS SDK (boto3) securely
- ✅ Follows least privilege principle (relies on caller's AWS permissions)
- ✅ No SQL injection or command injection vectors
- ✅ Appropriate logging levels (INFO for progress, ERROR for failures)

---

## Functionality and Correctness Assessment

### ✅ Code Quality Strengths

1. **Well-Documented Function:**
   ```python
   """
   Wait for any in-progress ASG instance refreshes to complete.

   :param asg_name: Name of the Auto Scaling Group
   :param autoscaling_client: boto3 autoscaling client
   :param timeout: Maximum time to wait in seconds (default 3600 = 1 hour)
   :param poll_interval: How often to poll in seconds (default 10)
   :raises TimeoutError: If timeout is reached with pending refreshes
   :raises RuntimeError: If any refresh fails or ASG is not found
   :raises Exception: On unexpected errors
   """
   ```
   - Clear parameter descriptions
   - Documents all exception types
   - Follows RST docstring format (per CODING_STANDARD.md)

2. **Comprehensive Status Handling:**
   ```python
   failed_states = ["Failed", "Cancelled", "RollbackSuccessful"]
   in_progress = [
       ir for ir in instance_refreshes
       if ir["Status"] in ["Pending", "InProgress", "Cancelling", "RollbackInProgress"]
   ]
   ```
   - Covers all AWS instance refresh states
   - Proper distinction between terminal states and transient states

3. **Intelligent Logging:**
   - Logs only status changes (avoids log spam)
   - Uses `seen_statuses` dict to track per-refresh status
   - Provides visual separators with `"=" * 80` for readability
   - Includes percentage completion in logs

4. **Robust Error Handling:**
   - Specific handling for `ValidationError` (ASG not found)
   - Generic ClientError handling with retry logic
   - Broad exception catching with re-raise for unexpected errors
   - Detailed error messages with context

5. **Proper Cleanup:**
   - Always logs closing separator line
   - Returns cleanly when no refreshes found
   - Provides detailed timeout information

### ⚠️ Minor Issues

1. **Missing Newline at End of File:**
   ```
   169→    raise TimeoutError(error_msg)
   170→\ No newline at end of file
   ```
   - **Impact:** Minimal, but violates POSIX standard
   - **Recommendation:** Add newline at end of utils.py

2. **File Mode Changes:**
   - Python files changed to executable (755)
   - **Impact:** Cosmetic, no functional impact
   - **Recommendation:** Revert to 644 (standard Python file permissions)

3. **Potential Infinite Loop on Unexpected Status:**
   - If AWS returns an unexpected status not in `failed_states` or `in_progress` filters
   - **Impact:** Low - would hit timeout eventually
   - **Recommendation:** Consider adding explicit handling for unknown statuses

### ✅ Correctness Verification

1. **Timeout Mechanism:** ✅ Correct
   ```python
   start_time = time.time()
   while time.time() - start_time < timeout:
   ```

2. **Polling Logic:** ✅ Correct
   ```python
   time.sleep(poll_interval)
   ```

3. **State Transitions:** ✅ Correct
   - Properly handles Pending → InProgress → Completed
   - Detects failures at any stage
   - Handles cancellations and rollbacks

4. **AWS API Usage:** ✅ Correct
   ```python
   response = autoscaling_client.describe_instance_refreshes(
       AutoScalingGroupName=asg_name, MaxRecords=10
   )
   ```
   - Uses proper boto3 method
   - Limits to 10 most recent refreshes (reasonable)

---

## Terraform Best Practices Evaluation

### N/A - This PR is Python Code, Not Terraform

This PR **does not modify any Terraform code**. The changes are purely Python utility functions for testing infrastructure. Therefore, Terraform-specific best practices are not applicable.

However, the changes **support Terraform testing workflows** by:
- Enabling tests to wait for ASG instance refreshes before proceeding
- Improving test reliability for Terraform-managed ASGs
- Following the established pytest-infrahouse pattern for infrastructure testing

---

## Compliance with InfraHouse Standards

### ✅ Adheres to CODING_STANDARD.md

1. **RST Docstrings:** ✅
   - Function uses RST-style docstrings with `:param:` and `:raises:`
   - Matches the style in other modules

2. **Python Dependency Pinning:** ✅ N/A
   - No new dependencies added
   - Uses existing boto3 and built-in time module

3. **Import Organization:** ✅
   ```python
   import time
   from . import DEFAULT_PROGRESS_INTERVAL, LOG
   ```
   - Follows PEP 8 import ordering

### ✅ Adheres to Project Patterns

1. **Logging Pattern:** ✅
   - Uses shared `LOG` instance from __init__.py
   - Consistent with terraform.py logging pattern

2. **Error Handling:** ✅
   - Follows the pattern established in plugin.py and terraform.py
   - Provides detailed error messages

3. **Type Hints:** ✅
   ```python
   def wait_for_instance_refresh(
       asg_name: str,
       autoscaling_client,
       timeout: int = 3600,
       poll_interval: int = DEFAULT_PROGRESS_INTERVAL,
   ) -> None:
   ```
   - Uses Python type hints consistently

### ⚠️ Minor Deviations

1. **Missing Type Hint for autoscaling_client:**
   - Could use `from mypy_boto3_autoscaling import AutoScalingClient`
   - **Impact:** Low - typing is optional for boto3 clients
   - **Recommendation:** Consider adding for better IDE support

---

## Detailed Code Review

### `src/pytest_infrahouse/__init__.py`

**Changes:**
```python
+import logging
+
 from .terraform import terraform_apply

 __version__ = "0.21.0"
+
+# Shared constants
+LOG = logging.getLogger(__name__)
+DEFAULT_PROGRESS_INTERVAL = 10
```

**Analysis:**
- ✅ Proper module-level organization
- ✅ Centralizes shared constants
- ✅ Uses `__name__` for logger (follows Python best practices)
- ⚠️ File mode changed to 755 (unnecessary for Python modules)

**Recommendation:**
- Revert file mode to 644
- Consider documenting the shared constants with inline comments

---

### `src/pytest_infrahouse/terraform.py`

**Changes:**
```python
+from . import DEFAULT_PROGRESS_INTERVAL, LOG
+
 DEFAULT_OPEN_ENCODING = "utf8"
 DEFAULT_ENCODING = DEFAULT_OPEN_ENCODING
-DEFAULT_PROGRESS_INTERVAL = 10
-LOG = logging.getLogger()
```

**Analysis:**
- ✅ Imports shared constants from __init__.py
- ✅ Reduces code duplication
- ✅ No functional changes to existing code
- ⚠️ File mode changed to 755 (unnecessary)

**Recommendation:**
- Revert file mode to 644

---

### `src/pytest_infrahouse/utils.py` (NEW FILE)

**Comprehensive Function Analysis:**

#### Function Signature
```python
def wait_for_instance_refresh(
    asg_name: str,
    autoscaling_client,
    timeout: int = 3600,
    poll_interval: int = DEFAULT_PROGRESS_INTERVAL,
) -> None:
```

**Strengths:**
- ✅ Clear, descriptive name
- ✅ Type hints for parameters
- ✅ Sensible defaults (1 hour timeout, 10s polling)
- ✅ Returns None (side-effect function)

**Potential Improvements:**
- Consider adding type hint for `autoscaling_client`
- Consider making timeout required (explicit is better than implicit)

#### Initialization and Logging
```python
LOG.info("=" * 80)
LOG.info("Checking for in-progress ASG instance refreshes for %s", asg_name)
LOG.info("=" * 80)

start_time = time.time()
seen_statuses = {}  # Track per refresh_id to avoid duplicate logs
```

**Strengths:**
- ✅ Clear visual separation in logs
- ✅ Tracks start time for timeout calculation
- ✅ Uses dict to avoid duplicate log messages
- ✅ Includes ASG name in log for context

#### Main Loop Structure
```python
while time.time() - start_time < timeout:
    try:
        response = autoscaling_client.describe_instance_refreshes(
            AutoScalingGroupName=asg_name, MaxRecords=10
        )
```

**Strengths:**
- ✅ Proper timeout mechanism
- ✅ Limits to 10 most recent refreshes (avoids processing huge lists)
- ✅ Try-except for AWS API errors

**Potential Improvements:**
- Consider making MaxRecords configurable (edge case: more than 10 concurrent refreshes)

#### Failed Refresh Detection
```python
failed_states = ["Failed", "Cancelled", "RollbackSuccessful"]
failed = [
    ir for ir in instance_refreshes if ir["Status"] in failed_states
]
if failed:
    failed_details = [
        f"{ir['InstanceRefreshId']}: {ir['Status']} - {ir.get('StatusReason', 'No reason provided')}"
        for ir in failed
    ]
    error_msg = (
        f"Instance refresh failed for ASG '{asg_name}'. "
        f"Failed refreshes: {'; '.join(failed_details)}"
    )
    LOG.error(error_msg)
    LOG.info("=" * 80)
    raise RuntimeError(error_msg)
```

**Strengths:**
- ✅ Comprehensive failed state detection
- ✅ Includes "RollbackSuccessful" as failure (good judgement call)
- ✅ Provides detailed failure information
- ✅ Uses `.get('StatusReason', ...)` to handle missing field
- ✅ Raises RuntimeError with context

**Correctness:**
- ✅ AWS instance refresh states: Pending, InProgress, Successful, Failed, Cancelling, Cancelled, RollbackInProgress, RollbackFailed, RollbackSuccessful
- ✅ Correctly identifies terminal failure states

#### In-Progress Refresh Detection
```python
in_progress = [
    ir
    for ir in instance_refreshes
    if ir["Status"]
    in ["Pending", "InProgress", "Cancelling", "RollbackInProgress"]
]

if not in_progress:
    if seen_statuses:
        LOG.info("All instance refreshes completed successfully")
    else:
        LOG.info("No in-progress instance refreshes found")
    LOG.info("=" * 80)
    return
```

**Strengths:**
- ✅ Correct identification of in-progress states
- ✅ Differentiates between "no refreshes" and "refreshes completed"
- ✅ Clean exit when done

**Potential Improvements:**
- Consider detecting "Successful" state explicitly to confirm completion vs. no refreshes

#### Progress Logging
```python
for refresh in in_progress:
    refresh_id = refresh["InstanceRefreshId"]
    status = refresh["Status"]
    percentage = refresh.get("PercentageComplete", 0)
    status_msg = f"{status} ({percentage}% complete)"

    if seen_statuses.get(refresh_id) != status_msg:
        LOG.info("Instance refresh %s: %s", refresh_id, status_msg)
        seen_statuses[refresh_id] = status_msg
```

**Strengths:**
- ✅ Avoids log spam by tracking seen statuses
- ✅ Includes percentage completion
- ✅ Per-refresh tracking (handles multiple concurrent refreshes)
- ✅ Uses `.get('PercentageComplete', 0)` for missing field

#### Error Handling: ValidationError
```python
except autoscaling_client.exceptions.ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "")
    if error_code == "ValidationError":
        error_msg = f"ASG '{asg_name}' not found"
        LOG.error(error_msg)
        LOG.info("=" * 80)
        raise RuntimeError(error_msg) from e
    LOG.warning("AWS API error: %s - retrying...", e)
    time.sleep(poll_interval)
```

**Strengths:**
- ✅ Specific handling for ValidationError (ASG not found)
- ✅ Raises RuntimeError with context
- ✅ Uses `raise ... from e` for exception chaining
- ✅ Retries on other AWS errors
- ✅ Sleeps before retry to avoid API throttling

**Potential Improvements:**
- Consider handling throttling errors explicitly (e.g., exponential backoff)

#### Error Handling: Unexpected Exceptions
```python
except Exception as e:
    LOG.error(
        "Unexpected error waiting for instance refresh: %s", e, exc_info=True
    )
    raise
```

**Strengths:**
- ✅ Catches unexpected errors
- ✅ Logs with stack trace (`exc_info=True`)
- ✅ Re-raises to propagate error

#### Timeout Handling
```python
# Timeout occurred - gather details about pending refreshes
try:
    response = autoscaling_client.describe_instance_refreshes(
        AutoScalingGroupName=asg_name, MaxRecords=10
    )
    instance_refreshes = response.get("InstanceRefreshes", [])
    in_progress = [
        ir
        for ir in instance_refreshes
        if ir["Status"]
        in ["Pending", "InProgress", "Cancelling", "RollbackInProgress"]
    ]
    pending_details = [
        f"{ir['InstanceRefreshId']}: {ir['Status']} ({ir.get('PercentageComplete', 0)}% complete)"
        for ir in in_progress
    ]
except Exception:
    pending_details = ["Unable to retrieve pending refresh details"]

elapsed = time.time() - start_time
error_msg = (
    f"Timeout after {elapsed:.1f} seconds waiting for instance refresh on ASG '{asg_name}'. "
    f"Pending refreshes: {'; '.join(pending_details) if pending_details else 'None'}"
)
LOG.error(error_msg)
LOG.info("=" * 80)
raise TimeoutError(error_msg)
```

**Strengths:**
- ✅ Makes final API call to get timeout state
- ✅ Provides detailed timeout information
- ✅ Handles API errors gracefully during timeout reporting
- ✅ Includes elapsed time in error message
- ✅ Raises TimeoutError (appropriate exception type)

**Potential Improvements:**
- Consider using `logging.exception()` instead of catching Exception silently

---

## Recommendations for Improvement

### Critical Issues
**None identified** ✅

### Important Improvements

1. **Add Newline at End of File:**
   ```python
   # In utils.py, line 170
   raise TimeoutError(error_msg)
   # ← Add newline here
   ```

2. **Revert File Permissions:**
   ```bash
   chmod 644 src/pytest_infrahouse/__init__.py
   chmod 644 src/pytest_infrahouse/terraform.py
   chmod 644 src/pytest_infrahouse/utils.py
   ```

3. **Add Type Hint for autoscaling_client:**
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from mypy_boto3_autoscaling import AutoScalingClient

   def wait_for_instance_refresh(
       asg_name: str,
       autoscaling_client: "AutoScalingClient",
       timeout: int = 3600,
       poll_interval: int = DEFAULT_PROGRESS_INTERVAL,
   ) -> None:
   ```

### Minor Suggestions

1. **Add Usage Example to Docstring:**
   ```python
   """
   Wait for any in-progress ASG instance refreshes to complete.

   Example:
       >>> from pytest_infrahouse.utils import wait_for_instance_refresh
       >>> wait_for_instance_refresh(
       ...     asg_name="my-jumphost-asg",
       ...     autoscaling_client=autoscaling_client,
       ...     timeout=600,
       ...     poll_interval=5
       ... )

   :param asg_name: Name of the Auto Scaling Group
   ...
   ```

2. **Add __all__ Export:**
   ```python
   # In utils.py
   __all__ = ["wait_for_instance_refresh"]
   ```

3. **Add Module Docstring:**
   ```python
   # At the top of utils.py
   """
   Utility functions for pytest-infrahouse tests.

   This module provides helper functions for common AWS operations
   in infrastructure tests, such as waiting for ASG instance refreshes.
   """
   ```

4. **Consider Making MaxRecords Configurable:**
   ```python
   def wait_for_instance_refresh(
       asg_name: str,
       autoscaling_client,
       timeout: int = 3600,
       poll_interval: int = DEFAULT_PROGRESS_INTERVAL,
       max_records: int = 10,  # ← Add this parameter
   ) -> None:
       ...
       response = autoscaling_client.describe_instance_refreshes(
           AutoScalingGroupName=asg_name, MaxRecords=max_records
       )
   ```

5. **Add Unit Tests with Mocking:**
   ```python
   # In tests/test_utils.py
   from unittest.mock import MagicMock
   import pytest
   from pytest_infrahouse.utils import wait_for_instance_refresh

   def test_wait_for_instance_refresh_success():
       """Test successful instance refresh completion."""
       mock_client = MagicMock()
       mock_client.describe_instance_refreshes.return_value = {
           "InstanceRefreshes": []
       }

       # Should complete without error
       wait_for_instance_refresh("test-asg", mock_client)

   def test_wait_for_instance_refresh_timeout():
       """Test timeout when refresh doesn't complete."""
       mock_client = MagicMock()
       mock_client.describe_instance_refreshes.return_value = {
           "InstanceRefreshes": [
               {
                   "InstanceRefreshId": "test-id",
                   "Status": "InProgress",
                   "PercentageComplete": 50
               }
           ]
       }

       with pytest.raises(TimeoutError):
           wait_for_instance_refresh("test-asg", mock_client, timeout=1)
   ```

---

## Testing Recommendations

1. **Add Unit Tests:**
   - Create `tests/test_utils.py`
   - Mock boto3 autoscaling client
   - Test success path (no refreshes, completed refreshes)
   - Test failure paths (failed refresh, cancelled refresh)
   - Test timeout behavior
   - Test error handling (ASG not found, API errors)

2. **Add Integration Test:**
   - Use in `test_jumphost.py` after ASG creation
   - Verify it handles no refreshes gracefully
   - Consider triggering an instance refresh to test full flow

3. **Add to Documentation:**
   - Update README.rst with example usage
   - Document when tests should use this utility
   - Add to "Best Practices" section

---

## Next Steps

**IMPORTANT: Please review the findings and approve which changes to implement before I proceed with any fixes.**

### Recommended Actions (in priority order):

1. **Must Fix:**
   - Add newline at end of `utils.py` (POSIX compliance)
   - Revert file permissions to 644 (unless there's a specific reason for 755)

2. **Should Fix:**
   - Add type hint for `autoscaling_client` parameter
   - Add module docstring to `utils.py`
   - Add usage example to function docstring

3. **Nice to Have:**
   - Add unit tests for `wait_for_instance_refresh()`
   - Add integration test usage in `test_jumphost.py` or similar
   - Add `__all__` export list
   - Consider making `max_records` configurable

4. **Documentation:**
   - Update README.rst with example usage
   - Add to "Best Practices" section
   - Consider adding to CHANGELOG.md

---

## Conclusion

This PR introduces well-designed, production-ready code that enhances pytest-infrahouse's ability to test ASG instance refresh scenarios. The implementation follows Python and AWS best practices, includes comprehensive error handling, and provides excellent observability through detailed logging.

**The changes are APPROVED for merge** with the minor recommendations addressed.

**Key Strengths:**
- ✅ Comprehensive error handling
- ✅ Excellent logging with progress tracking
- ✅ Proper timeout and polling mechanism
- ✅ Follows established project patterns
- ✅ Non-breaking changes
- ✅ Security-conscious implementation

**Minor Issues to Address:**
- ⚠️ Add newline at end of file
- ⚠️ Revert file permissions to 644
- ⚠️ Add type hints and documentation

**Overall Quality:** High - This is well-crafted infrastructure testing code that will improve test reliability.