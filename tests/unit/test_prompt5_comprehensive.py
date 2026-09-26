"""Comprehensive tests for Prompt 5: File Editing, Git Tools, Safety, and Integration."""

import os
import shutil
import tempfile
import pytest
from pathlib import Path

from harness.tools.base import ToolResult
from harness.tools.file_tools import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ApplyPatchTool,
    DeleteFileTool,
    GetFileMetadataTool,
    InspectProjectTool,
    resolve_safe_path,
)
from harness.tools.git_tools import (
    GitStatusTool,
    GitDiffTool,
    GitLogTool,
    GitCreateBranchTool,
    GitCommitTool,
    GitCheckpointTool,
    _run_git,
)
from harness.tools.registry import ToolRegistry
from harness.llm.adapter import LLMAdapter
from harness.config import Settings


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing."""
    tmpdir = tempfile.mkdtemp(prefix="agent_p5_test_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_file_operations_flow(temp_workspace):
    """Test full lifecycle of file operations."""
    write_tool = WriteFileTool(temp_workspace)
    read_tool = ReadFileTool(temp_workspace)
    edit_tool = EditFileTool(temp_workspace)
    patch_tool = ApplyPatchTool(temp_workspace)
    delete_tool = DeleteFileTool(temp_workspace)

    # 1. Create a new file
    file_rel = "sub/test.txt"
    res_write = await write_tool.execute(path=file_rel, content="Line 1: Hello\nLine 2: World\n")
    assert res_write.success
    assert os.path.exists(os.path.join(temp_workspace, "sub", "test.txt"))

    # 2. Read it back
    res_read = await read_tool.execute(path=file_rel)
    assert res_read.success
    assert "Line 1: Hello" in res_read.output

    # 3. Edit a unique text match
    res_edit = await edit_tool.execute(
        path=file_rel,
        target_content="Line 2: World",
        replacement_content="Line 2: Antigravity",
    )
    assert res_edit.success
    assert "Successfully replaced 1 occurrence" in res_edit.output
    
    res_read_after = await read_tool.execute(path=file_rel)
    assert "Line 2: Antigravity" in res_read_after.output

    # 4. Reject an ambiguous edit (multiple matches without allow_multiple)
    await write_tool.execute(path="dup.txt", content="foo\nbar\nfoo\n")
    res_ambig = await edit_tool.execute(
        path="dup.txt",
        target_content="foo",
        replacement_content="baz",
        allow_multiple=False,
    )
    assert not res_ambig.success
    assert "matched 2 times" in res_ambig.error

    # Reject missing target edit
    res_missing_target = await edit_tool.execute(
        path="dup.txt",
        target_content="nonexistent",
        replacement_content="baz",
    )
    assert not res_missing_target.success
    assert "Target content not found" in res_missing_target.error

    # 5. Apply a valid patch
    patch_content = """--- sub/test.txt
+++ sub/test.txt
@@ -1,2 +1,3 @@
 Line 1: Hello
 Line 2: Antigravity
+Line 3: Patched
"""
    res_patch = await patch_tool.execute(patch_content=patch_content)
    assert res_patch.success
    res_read_patched = await read_tool.execute(path=file_rel)
    assert "Line 3: Patched" in res_read_patched.output

    # 6. Reject a malformed patch
    malformed_patch = "This is not a patch format\n@@ invalid @@"
    res_bad_patch = await patch_tool.execute(patch_content=malformed_patch)
    assert not res_bad_patch.success
    assert "Failed to apply patch" in res_bad_patch.error or "error" in res_bad_patch.error.lower()

    # 7. Delete a test file
    res_del = await delete_tool.execute(path="dup.txt")
    assert res_del.success
    assert not os.path.exists(os.path.join(temp_workspace, "dup.txt"))

    # 8. Handle missing files & errors
    res_del_missing = await delete_tool.execute(path="nonexistent.txt")
    assert not res_del_missing.success
    assert "File not found" in res_del_missing.error

    res_read_missing = await read_tool.execute(path="nonexistent.txt")
    assert not res_read_missing.success
    assert "File not found" in res_read_missing.error


@pytest.mark.asyncio
async def test_security_sandboxing(temp_workspace):
    """Test security boundaries: path traversal, absolute paths, symlinks, protected files."""
    # Create outside directory and file
    outside_dir = tempfile.mkdtemp(prefix="outside_p5_")
    outside_file = os.path.join(outside_dir, "secret.txt")
    with open(outside_file, "w") as f:
        f.write("top secret content")

    try:
        # 1. Path traversal
        with pytest.raises(ValueError, match="Security Error: Access denied"):
            resolve_safe_path(temp_workspace, "../outside.txt")

        # 2. Absolute path outside workspace
        with pytest.raises(ValueError, match="Security Error: Access denied"):
            resolve_safe_path(temp_workspace, outside_file)

        # 3. Symlink escape
        symlink_path = os.path.join(temp_workspace, "symlink_outside")
        os.symlink(outside_file, symlink_path)

        with pytest.raises(ValueError, match="Security Error: Access denied"):
            resolve_safe_path(temp_workspace, "symlink_outside")

        # Verify WriteFileTool cannot write outside workspace
        write_tool = WriteFileTool(temp_workspace)
        res = await write_tool.execute(path="../escaped.txt", content="hack")
        assert not res.success
        assert "Security Error" in res.error

        # Verify DeleteFileTool cannot delete outside workspace
        delete_tool = DeleteFileTool(temp_workspace)
        res_del = await delete_tool.execute(path="../outside.txt")
        assert not res_del.success
        assert "Security Error" in res_del.error

        # Verify ApplyPatchTool rejects path traversal in patch header
        patch_tool = ApplyPatchTool(temp_workspace)
        bad_patch = """--- ../outside.txt
+++ ../outside.txt
@@ -1 +1 @@
-top secret
+hacked
"""
        res_patch = await patch_tool.execute(patch_content=bad_patch)
        assert not res_patch.success
        assert "Security Error" in res_patch.error

    finally:
        shutil.rmtree(outside_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_git_tools_workflow(temp_workspace):
    """Test Git tools in a temporary git repository."""
    status_tool = GitStatusTool(temp_workspace)
    diff_tool = GitDiffTool(temp_workspace)
    log_tool = GitLogTool(temp_workspace)
    branch_tool = GitCreateBranchTool(temp_workspace)
    commit_tool = GitCommitTool(temp_workspace)
    checkpoint_tool = GitCheckpointTool(temp_workspace)

    # Initialize repository via checkpoint tool
    res_cp = await checkpoint_tool.execute(label="init_repo")
    assert res_cp.success

    # Check status (should be clean)
    res_status = await status_tool.execute()
    assert res_status.success
    assert "[Working tree clean]" in res_status.output or res_status.output == ""

    # Create a new branch
    res_branch = await branch_tool.execute(branch_name="feature/p5-test")
    assert res_branch.success

    # Write a file and check diff
    write_tool = WriteFileTool(temp_workspace)
    await write_tool.execute(path="feature.py", content="print('hello feature')\n")

    res_status2 = await status_tool.execute()
    assert res_status2.success
    assert "feature.py" in res_status2.output

    # Commit changes
    res_commit = await commit_tool.execute(message="Add feature.py", stage_all=True)
    assert res_commit.success

    # Check log
    res_log = await log_tool.execute(max_count=5)
    assert res_log.success
    assert "Add feature.py" in res_log.output

    # Confirm no remote push tools exist in Git tools registry
    git_tool_names = [status_tool.name, diff_tool.name, log_tool.name, branch_tool.name, commit_tool.name, checkpoint_tool.name]
    assert "git_push" not in git_tool_names
    assert "push" not in git_tool_names


@pytest.mark.asyncio
async def test_prompt5_tool_registry_integration(temp_workspace):
    """Test that all file and Git tools register in ToolRegistry and execute properly."""
    from harness.tools.registry import create_default_registry

    registry = create_default_registry(temp_workspace)
    
    expected_tools = [
        "read_file",
        "write_file",
        "edit_file",
        "delete_file",
        "apply_patch",
        "list_files",
        "get_file_metadata",
        "inspect_project",
        "git_status",
        "git_diff",
        "git_log",
        "git_create_branch",
        "git_commit",
        "git_checkpoint",
        "git_rollback",
    ]

    registered = registry.get_tool_names()
    for tool_name in expected_tools:
        assert tool_name in registered, f"Tool '{tool_name}' missing from ToolRegistry"

    # Test invoking write_file through registry
    write_res = await registry.execute("write_file", {"path": "reg_test.txt", "content": "Registry OK"})
    assert write_res.success

    read_res = await registry.execute("read_file", {"path": "reg_test.txt"})
    assert read_res.success
    assert "Registry OK" in read_res.output
