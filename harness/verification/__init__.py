"""Verification and automated test runner subsystem."""

from harness.verification.detector import detect_test_command
from harness.verification.runner import VerificationResult, VerificationRunner
from harness.verification.comparator import compare_test_results

__all__ = [
    "detect_test_command",
    "VerificationResult",
    "VerificationRunner",
    "compare_test_results",
]
