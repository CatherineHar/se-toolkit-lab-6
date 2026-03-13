# Documentation Agent

## Overview
A CLI agent that uses an LLM to answer questions about the project wiki. The agent has tools to navigate the file system (`list_files`) and read documentation (`read_file`), then uses an agentic loop to find answers and cite sources.

## Provider
- **API**: OpenRouter.ai (OpenAI-compatible endpoint)
- **Model**: `meta-llama/llama-3.3-70b-instruct:free` (configurable)

## Tools

The agent has two tools registered as function-calling schemas:

### `read_file`
Reads the contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or an error message if the file doesn't exist.

**Security:** Blocks paths containing `..` (traversal) or absolute paths to prevent reading files outside the project directory.

### `list_files`
Lists files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries, or an error message.

**Security:** Same path restrictions as `read_file`.

## Agentic Loop

The agent implements a reasoning loop that allows the LLM to decide which tools to call:

```
Question → LLM → tool_calls? → execute tools → append results → back to LLM
                                      │
                                      no (final answer)
                                      │
                                      ▼
                                 Extract answer + source → JSON output
```

**Loop steps:**
1. Initialize conversation with system prompt + user question
2. Call LLM with tool schemas
3. If LLM returns `tool_calls`:
   - Execute each tool function
   - Append results as `role: "tool"` messages
   - Repeat from step 2
4. If LLM returns text (no tool calls):
   - Extract answer and source
   - Output JSON and exit
5. Maximum 10 tool calls per question (prevents infinite loops)

## System Prompt Strategy

The system prompt instructs the LLM to:

1. **Discover**: Use `list_files` to explore the wiki directory structure
2. **Read**: Use `read_file` to examine relevant documentation files
3. **Cite**: Include a source reference in the format `wiki/filename.md#section-anchor`
4. **Reason**: Think step-by-step before providing the final answer

Example prompt excerpt:
> "When answering questions:
> 1. First use list_files to discover relevant wiki files (start with 'wiki' directory)
> 2. Then use read_file to read the contents of relevant files
> 3. Find the specific section that answers the question
> 4. Provide a concise answer with the source reference"

## Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git workflow\n..."
    }
  ]
}
```

**Fields:**
- `answer` (string): The LLM's answer to the question
- `source` (string): Wiki file path with section anchor (e.g., `wiki/git-workflow.md#merge-conflicts`)
- `tool_calls` (array): All tool calls made during the agentic loop, each with `tool`, `args`, and `result`

## Usage

```bash
# Ask a question
uv run agent.py "How do you resolve a merge conflict?"

# Run tests
uv run test_agent.py
```

## Configuration

Set environment variables in `.env.agent.secret`:

```bash
LLM_API_KEY=sk-or-v1-YOUR_KEY
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

## Security

Path security prevents directory traversal attacks:
- Rejects paths containing `..`
- Rejects absolute paths
- Verifies resolved paths are within project root
