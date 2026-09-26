"""Integration tests for verification subsystem and test detection."""

import os
import pytest
from harness.verification.comparator import compare_test_results
from harness.verification.detector import detect_test_command
from harness.verification.runner import VerificationResult, VerificationRunner, parse_pytest_output


def test_detector(mock_workspace):
    """Verify test command auto-detection on Python workspace."""
    cmd = detect_test_command(mock_workspace)
    assert cmd is not None
    assert "pytest" in cmd


def test_pytest_output_parser():
    """Verify parsing pytest summaries."""
    output = "===== 3 passed, 1 failed, 2 skipped in 0.45s ====="
    total, passed, failed, skipped = parse_pytest_output(output, exit_code=1)
    assert total == 6
    assert passed == 3
    assert failed == 1
    assert skipped == 2


@pytest.mark.asyncio
async def test_verification_runner_lifecycle(mock_workspace):
    """Test running tests on buggy workspace, fixing bug, and re-running."""
    verifier = VerificationRunner(mock_workspace)

    # 1. Initial run on buggy code -> Should fail
    res_before = await verifier.run()
    assert not res_before.passed
    assert res_before.failed_tests >= 1

    # 2. Fix the bug
    calc_path = os.path.join(mock_workspace, "calculator.py")
    with open(calc_path, "w", encoding="utf-8") as f:
        f.write("def add(a: int, b: int) -> int:\n    return a + b\n")

    # 3. Post-fix run -> Should pass
    res_after = await verifier.run()
    assert res_after.passed
    assert res_after.passed_tests >= 1
    assert res_after.failed_tests == 0

    # 4. Compare
    comp = compare_test_results(res_before, res_after)
    assert comp["improved"]
    assert comp["finally_passed"]
