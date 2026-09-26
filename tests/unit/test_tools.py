"""Unit tests for tool implementations and path safety."""

import os
import pytest
from harness.tools.file_tools import (
    EditFileTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
    resolve_safe_path,
    GetFileMetadataTool,
    InspectProjectTool,
    ApplyPatchTool,
    DeleteFileTool,
)
from harness.tools.git_tools import (
    GitCheckpointTool, 
    GitDiffTool, 
    GitRollbackTool, 
    GitStatusTool,
    GitLogTool,
    GitCreateBranchTool,
    GitCommitTool
)
from harness.tools.search_tools import FindFilesTool, GrepSearchTool
from harness.tools.terminal_tools import RunCommandTool


@pytest.mark.asyncio
async def test_path_safety(mock_workspace):
    """Ensure path traversal outside workspace is blocked."""
    with pytest.raises(ValueError, match="Security Error: Access denied"):
        resolve_safe_path(mock_workspace, "../../outside.txt")


@pytest.mark.asyncio
async def test_file_read_write_edit(mock_workspace):
    """Test reading, writing, and surgical editing of workspace files."""
    read_tool = ReadFileTool(mock_workspace)
    write_tool = WriteFileTool(mock_workspace)
    edit_tool = EditFileTool(mock_workspace)

    # 1. Read existing file
    read_res = await read_tool.execute(path="calculator.py")
    assert read_res.success
    assert "return a - b" in read_res.output

    # 2. Edit file
    edit_res = await edit_tool.execute(
        path="calculator.py",
        target_content="return a - b",
        replacement_content="return a + b",
    )
    assert edit_res.success
    assert "Successfully replaced 1 occurrence" in edit_res.output

    # Verify content changed
    read_res_after = await read_tool.execute(path="calculator.py")
    assert "return a + b" in read_res_after.output

    # 3. Write new file
    write_res = await write_tool.execute(
        path="docs/guide.md", content="# Guide\nSample documentation.\n"
    )
    assert write_res.success
    assert os.path.exists(os.path.join(mock_workspace, "docs", "guide.md"))

    # 4. Apply Patch
    patch_tool = ApplyPatchTool(mock_workspace)
    patch_content = '''--- docs/guide.md
+++ docs/guide.md
@@ -1,2 +1,3 @@
 # Guide
 Sample documentation.
+Added via patch.
'''
    patch_res = await patch_tool.execute(patch_content=patch_content)
    assert patch_res.success
    
    # 5. Delete file
    delete_tool = DeleteFileTool(mock_workspace)
    del_res = await delete_tool.execute(path="docs/guide.md")
    assert del_res.success
    assert not os.path.exists(os.path.join(mock_workspace, "docs", "guide.md"))


@pytest.mark.asyncio
async def test_search_and_list_tools(mock_workspace):
    """Test list directory, grep search, and find files."""
    list_tool = ListDirectoryTool(mock_workspace)
    grep_tool = GrepSearchTool(mock_workspace)
    find_tool = FindFilesTool(mock_workspace)

    list_res = await list_tool.execute()
    assert list_res.success
    assert "calculator.py" in list_res.output

    grep_res = await grep_tool.execute(query="def add")
    assert grep_res.success
    assert "calculator.py:1: def add" in grep_res.output

    find_res = await find_tool.execute(pattern="*calc*")
    assert find_res.success
    assert "calculator.py" in find_res.output


@pytest.mark.asyncio
async def test_terminal_tool(mock_workspace):
    """Test shell command execution."""
    term_tool = RunCommandTool(mock_workspace)
    res = await term_tool.execute(command="echo 'AI Harness Test'")
    assert res.success
    assert "AI Harness Test" in res.output
    assert res.data["exit_code"] == 0


@pytest.mark.asyncio
async def test_git_tools(mock_workspace):
    """Test git checkpoint, diff, status, and rollback."""
    status_tool = GitStatusTool(mock_workspace)
    diff_tool = GitDiffTool(mock_workspace)
    checkpoint_tool = GitCheckpointTool(mock_workspace)
    rollback_tool = GitRollbackTool(mock_workspace)
    branch_tool = GitCreateBranchTool(mock_workspace)
    commit_tool = GitCommitTool(mock_workspace)
    log_tool = GitLogTool(mock_workspace)

    # Create checkpoint (initializes repo)
    cp_res = await checkpoint_tool.execute(label="test_save")
    assert cp_res.success

    # Branch creation
    branch_res = await branch_tool.execute(branch_name="feature/test-branch")
    assert branch_res.success

    # Modify file and commit
    write_tool = WriteFileTool(mock_workspace)
    await write_tool.execute(path="temp.txt", content="temporary dirty change")

    commit_res = await commit_tool.execute(message="Test commit", stage_all=True)
    assert commit_res.success
    
    # Git log
    log_res = await log_tool.execute(max_count=2)
    assert log_res.success
    assert "Test commit" in log_res.output

    # Rollback
    rb_res = await rollback_tool.execute(hard=True)
    assert rb_res.success
    assert not os.path.exists(os.path.join(mock_workspace, "bad.txt"))


@pytest.mark.asyncio
async def test_exploration_tools(mock_workspace):
    """Test get_file_metadata and inspect_project tools."""
    write_tool = WriteFileTool(mock_workspace)
    await write_tool.execute(path="config.json", content='{"key": "value"}')

    metadata_tool = GetFileMetadataTool(mock_workspace)
    meta_res = await metadata_tool.execute(path="config.json")
    assert meta_res.success
    assert "Metadata for" in meta_res.output
    assert ".json" in meta_res.output
    assert meta_res.data["extension"] == ".json"

    inspect_tool = InspectProjectTool(mock_workspace)
    insp_res = await inspect_tool.execute()
    assert insp_res.success
    assert "Project Inspection Report" in insp_res.output
