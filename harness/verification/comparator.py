"""Compares baseline test results with post-execution test results."""

from typing import Dict
from harness.verification.runner import VerificationResult


def compare_test_results(
    before: VerificationResult, after: VerificationResult
) -> Dict[str, any]:
    """Analyzes the delta between initial and post-fix test runs."""
    fixed_count = max(0, before.failed_tests - after.failed_tests)
    new_failures = max(0, after.failed_tests - before.failed_tests)
    improved = after.passed and not before.passed

    return {
        "improved": improved,
        "initially_passed": before.passed,
        "finally_passed": after.passed,
        "fixed_tests_count": fixed_count,
        "new_failures_count": new_failures,
        "summary": (
            f"Pre-test: {before.summary} -> Post-test: {after.summary}. "
            f"Result: {'SUCCESSFULLY RESOLVED' if after.passed else 'VERIFICATION FAILED'}"
        ),
    }
