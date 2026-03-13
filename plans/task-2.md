# Plan: Documentation Agent (Task 2)

## Goal
Build an agentic loop that allows the LLM to navigate the project wiki using two tools (`read_file`, `list_files`) to find answers and cite sources.

## 1. Tool Schemas

Define tool schemas as OpenAI-compatible function definitions for the LLM:

### `read_file`
```json
{
  "name": "read_file",
  "description": "Read contents of a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

### `list_files`
```json
{
  "name": "list_files",
  "description": "List files and directories at a given path",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative directory path from project root"}
    },
    "required": ["path"]
  }
}
```

## 2. Tool Implementation

### `read_file(path)`
- Resolve path relative to project root (`se-toolkit-lab-6/`)
- **Security**: Reject paths containing `..` or absolute paths
- Return file contents as string, or error message if file doesn't exist

### `list_files(path)`
- Resolve path relative to project root
- **Security**: Reject paths containing `..` or absolute paths
- Return newline-separated listing of files/directories

### Path Security
```python
def is_safe_path(base_dir: str, requested_path: str) -> bool:
    # Reject paths with traversal
    if ".." in requested_path:
        return False
    # Resolve and verify it's within base_dir
    resolved = os.path.normpath(os.path.join(base_dir, requested_path))
    return resolved.startswith(os.path.normpath(base_dir))
```

## 3. Agentic Loop

```
Question → LLM → tool_calls? → execute tools → append results → back to LLM
                                      │
                                      no (final answer)
                                      │
                                      ▼
                                 Extract answer + source → JSON output
```

### Loop Implementation
1. Initialize `messages` list with system prompt + user question
2. Loop (max 10 iterations):
   - Call LLM with `messages` + `tools` schema
   - If response has `tool_calls`:
     - Execute each tool, collect results
     - Append tool results as `role: "tool"` messages
     - Continue loop
   - If response has no tool calls:
     - Extract answer from `message.content`
     - Extract source (file path + section anchor)
     - Break and output JSON
3. If max iterations reached, use whatever answer we have

## 4. System Prompt

Tell the LLM:
- Use `list_files` to discover wiki files
- Use `read_file` to find the answer
- Include source reference (file path + section anchor like `wiki/git-workflow.md#resolving-merge-conflicts`)
- Call tools when needed, otherwise provide final answer

## 5. Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md\n..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## 6. Step-by-Step Tasks

- [ ] Create `plans/task-2.md` (this file)
- [ ] Implement `read_file` and `list_files` tool functions with path security
- [ ] Define tool schemas for LLM function calling
- [ ] Implement agentic loop with max 10 iterations
- [ ] Update system prompt to instruct LLM on tool usage
- [ ] Parse LLM response to extract answer and source
- [ ] Update output JSON to include `source` and populated `tool_calls`
- [ ] Test with: `uv run agent.py "How do you resolve a merge conflict?"`
- [ ] Update `test_agent.py` to verify new fields

## 7. Acceptance Criteria

- [ ] `source` field present in output (string, required)
- [ ] `tool_calls` array populated with tool, args, and result
- [ ] Maximum 10 tool calls per question
- [ ] Path security prevents `../` traversal
- [ ] Agent can discover and read wiki files autonomously
- [ ] JSON-only output to stdout, debug to stderr
