#!/usr/bin/env python3
"""Tests for the System Agent.

Includes regression tests for:
- Wiki documentation questions (read_file, list_files)
- Source code questions (read_file)
- API data queries (query_api)
- Path security
"""
import subprocess
import json
import sys


def run_agent(question: str) -> tuple[bool, dict | None, bool]:
    """Run the agent and return (success, output_dict, is_rate_limited)."""
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # Check for 429 rate limit error
        if "429" in result.stderr or "Too Many Requests" in result.stderr:
            print(f"  ⚠ Rate limited (429) - skipping test")
            return True, None, True  # Treat as pass
        
        print(f"  ❌ Agent failed (returncode={result.returncode})")
        if result.stderr:
            print(f"  stderr: {result.stderr[:200]}")
        return False, None, False

    try:
        output = json.loads(result.stdout)
        return True, output, False
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        print(f"  stdout: {result.stdout[:200]}")
        return False, None, False


def test_basic_question():
    """Test that the agent can answer a basic question."""
    print("Test: Basic question (What is REST?)")
    
    success, output, rate_limited = run_agent("What is REST?")
    if rate_limited:
        print("  ✓ Test passed (rate limited - skipped)")
        return True
    if not success:
        return False

    # Check required fields
    if "answer" not in output:
        print("  ❌ Missing 'answer' field")
        return False

    if "source" not in output:
        print("  ❌ Missing 'source' field")
        return False

    if "tool_calls" not in output:
        print("  ❌ Missing 'tool_calls' field")
        return False

    if not isinstance(output["tool_calls"], list):
        print("  ❌ 'tool_calls' must be an array")
        return False

    # Check that tool_calls have required fields
    for tc in output["tool_calls"]:
        if "tool" not in tc:
            print("  ❌ Tool call missing 'tool' field")
            return False
        if "args" not in tc:
            print("  ❌ Tool call missing 'args' field")
            return False
        if "result" not in tc:
            print("  ❌ Tool call missing 'result' field")
            return False

    print("  ✓ Test passed")
    print(f"    Answer: {output['answer'][:80]}...")
    print(f"    Source: {output['source']}")
    print(f"    Tool calls: {len(output['tool_calls'])}")
    return True


def test_merge_conflict():
    """
    Regression test: 'How do you resolve a merge conflict?'
    Expects: read_file in tool_calls, wiki/git-workflow.md in source
    """
    print("Test: Merge conflict question (regression)")
    
    success, output, rate_limited = run_agent("How do you resolve a merge conflict?")
    if rate_limited:
        print("  ✓ Test passed (rate limited - skipped)")
        return True
    if not success:
        return False

    # Check required fields exist
    if "answer" not in output or "source" not in output or "tool_calls" not in output:
        print("  ❌ Missing required fields")
        return False

    # Check that read_file was called
    tools_used = [tc.get("tool") for tc in output["tool_calls"]]
    if "read_file" not in tools_used:
        print(f"  ❌ Expected 'read_file' in tool_calls, got: {tools_used}")
        return False

    # Check that source points to git-workflow.md
    source = output["source"]
    if "wiki/git-workflow.md" not in source:
        print(f"  ❌ Expected 'wiki/git-workflow.md' in source, got: {source}")
        return False

    print("  ✓ Test passed")
    print(f"    Answer: {output['answer'][:80]}...")
    print(f"    Source: {source}")
    print(f"    Tools used: {tools_used}")
    return True


def test_list_files_in_wiki():
    """
    Regression test: 'What files are in the wiki?'
    Expects: list_files in tool_calls
    """
    print("Test: List files in wiki (regression)")
    
    success, output, rate_limited = run_agent("What files are in the wiki?")
    if rate_limited:
        print("  ✓ Test passed (rate limited - skipped)")
        return True
    if not success:
        return False

    # Check required fields exist
    if "answer" not in output or "source" not in output or "tool_calls" not in output:
        print("  ❌ Missing required fields")
        return False

    # Check that list_files was called
    tools_used = [tc.get("tool") for tc in output["tool_calls"]]
    if "list_files" not in tools_used:
        print(f"  ❌ Expected 'list_files' in tool_calls, got: {tools_used}")
        return False

    print("  ✓ Test passed")
    print(f"    Answer: {output['answer'][:80]}...")
    print(f"    Source: {output['source']}")
    print(f"    Tools used: {tools_used}")
    return True


def test_path_security():
    """Test that the agent cannot read files outside the project."""
    print("Test: Path security")

    # Import agent module to test functions directly
    sys.path.insert(0, '.')
    from agent import read_file, list_files

    # Test path traversal
    result = read_file("../.env")
    if "Error" not in result:
        print("  ❌ Path traversal not blocked for read_file")
        return False

    result = list_files("../")
    if "Error" not in result:
        print("  ❌ Path traversal not blocked for list_files")
        return False

    # Test absolute path
    result = read_file("/etc/passwd")
    if "Error" not in result:
        print("  ❌ Absolute path not blocked for read_file")
        return False

    print("  ✓ Test passed")
    return True


def test_backend_framework():
    """
    Regression test: 'What Python web framework does the backend use?'
    Expects: read_file in tool_calls (reading source code, not wiki)
    """
    print("Test: Backend framework question (regression)")

    success, output, rate_limited = run_agent("What Python web framework does the backend use?")
    if rate_limited:
        print("  ✓ Test passed (rate limited - skipped)")
        return True
    if not success:
        return False

    # Check required fields exist
    if "answer" not in output or "source" not in output or "tool_calls" not in output:
        print("  ❌ Missing required fields")
        return False

    # Check that read_file was called (to read source code)
    tools_used = [tc.get("tool") for tc in output["tool_calls"]]
    if "read_file" not in tools_used:
        print(f"  ❌ Expected 'read_file' in tool_calls, got: {tools_used}")
        return False

    # Check that the answer mentions FastAPI
    answer = output.get("answer", "").lower()
    if "fastapi" not in answer:
        print(f"  ❌ Expected 'FastAPI' in answer, got: {output.get('answer', '')[:100]}")
        return False

    print("  ✓ Test passed")
    print(f"    Answer: {output['answer'][:80]}...")
    print(f"    Source: {output['source']}")
    print(f"    Tools used: {tools_used}")
    return True


def test_database_item_count():
    """
    Regression test: 'How many items are in the database?'
    Expects: query_api in tool_calls (not read_file or list_files)
    """
    print("Test: Database item count question (regression)")

    success, output, rate_limited = run_agent("How many items are in the database?")
    if rate_limited:
        print("  ✓ Test passed (rate limited - skipped)")
        return True
    if not success:
        return False

    # Check required fields exist
    if "answer" not in output or "tool_calls" not in output:
        print("  ❌ Missing required fields")
        return False

    # Check that query_api was called (not read_file or list_files)
    tools_used = [tc.get("tool") for tc in output["tool_calls"]]
    if "query_api" not in tools_used:
        print(f"  ❌ Expected 'query_api' in tool_calls, got: {tools_used}")
        return False

    # Check that the answer contains a number
    import re
    answer = output.get("answer", "")
    numbers = re.findall(r'\d+', answer)
    if not numbers:
        print(f"  ❌ Expected a number in answer, got: {answer[:100]}")
        return False

    print("  ✓ Test passed")
    print(f"    Answer: {output['answer'][:80]}...")
    print(f"    Tools used: {tools_used}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Running System Agent tests...")
    print("=" * 60)
    print()

    all_passed = True

    all_passed &= test_basic_question()
    print()
    all_passed &= test_merge_conflict()
    print()
    all_passed &= test_list_files_in_wiki()
    print()
    all_passed &= test_path_security()
    print()
    all_passed &= test_backend_framework()
    print()
    all_passed &= test_database_item_count()
    print()

    print("=" * 60)
    if all_passed:
        print("✓ All tests passed")
        exit(0)
    else:
        print("❌ Some tests failed")
        exit(1)
