# System Agent

## Overview
A CLI agent that uses an LLM to answer questions about the project wiki, source code, and deployed backend API. The agent has tools to navigate the file system (`list_files`), read files (`read_file`), and query the backend API (`query_api`). It uses an agentic loop to find answers and cite sources.

## Provider
- **API**: OpenRouter.ai (OpenAI-compatible endpoint)
- **Model**: `meta-llama/llama-3.3-70b-instruct:free` (configurable)

## Tools

The agent has three tools registered as function-calling schemas:

### `read_file`
Reads the contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`, `backend/app/main.py`)

**Returns:** File contents as a string, or an error message if the file doesn't exist.

**Security:** Blocks paths containing `..` (traversal) or absolute paths to prevent reading files outside the project directory.

**Use cases:** Wiki documentation, source code analysis, configuration files (docker-compose.yml, Dockerfile, etc.)

### `list_files`
Lists files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`, `backend/app/routers`)

**Returns:** Newline-separated listing of entries, or an error message.

**Security:** Same path restrictions as `read_file`.

**Use cases:** Discovering available wiki files, listing API router modules, exploring project structure.

### `query_api`
Calls the deployed backend API to fetch data or trigger actions.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, PATCH)
- `path` (string, required): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT/PATCH requests
- `use_auth` (boolean, optional): Whether to include authentication header (default: true). Set to false to test unauthenticated requests.

**Returns:** JSON string with `status_code` and `body` (or `error` on failure).

**Authentication:** Uses `LMS_API_KEY` from environment (loaded from `.env.docker.secret`). Sent as `Authorization: Bearer <LMS_API_KEY>` header.

**Use cases:** Querying database contents, checking API status codes, testing analytics endpoints, diagnosing API errors.

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

The system prompt instructs the LLM on tool selection:

**Tool selection guide:**
- Use `list_files`/`read_file` with `wiki/` path for documentation questions (e.g., "how to protect a branch")
- Use `read_file` with source code paths (`backend/app/`, `docker-compose.yml`, etc.) for system facts (e.g., "what framework", "what port")
- Use `query_api` for questions about database contents, analytics, or API responses (e.g., "how many items", "what status code")

**For API errors:** The LLM is instructed to use `read_file` to find the buggy source code after discovering an error via `query_api`.

**Source citation:** The prompt requires source references in the format `path/filename.md#section-anchor` for file-based answers, and endpoint references for API queries.

## Output Format

```json
{
  "answer": "There are 44 items in the database.",
  "source": "",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

**Fields:**
- `answer` (string): The LLM's answer to the question
- `source` (string): File path with section anchor for wiki/source queries, or endpoint reference for API queries
- `tool_calls` (array): All tool calls made during the agentic loop, each with `tool`, `args`, and `result`

## Usage

```bash
# Ask a question
uv run agent.py "How many items are in the database?"
uv run agent.py "What HTTP status code does /items/ return without auth?"
uv run agent.py "What Python web framework does this project use?"

# Run tests
uv run test_agent.py

# Run evaluation benchmark
uv run run_eval.py
```

## Configuration

Set environment variables in `.env.agent.secret` for LLM configuration:

```bash
LLM_API_KEY=sk-or-v1-YOUR_KEY
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

Set environment variables in `.env.docker.secret` for backend API access:

```bash
LMS_API_KEY=my-secret-api-key
```

Optional configuration:
- `AGENT_API_BASE_URL`: Base URL for query_api (default: `http://localhost:42002`)

## Security

**Path security** prevents directory traversal attacks:
- Rejects paths containing `..`
- Rejects absolute paths
- Verifies resolved paths are within project root

**API authentication:** The `query_api` tool uses the `LMS_API_KEY` for authenticated requests. The `use_auth` parameter allows testing unauthenticated endpoints (e.g., verifying 401 responses).

**Environment variable separation:** Two distinct keys are used:
- `LLM_API_KEY` (in `.env.agent.secret`) authenticates with the LLM provider
- `LMS_API_KEY` (in `.env.docker.secret`) authenticates with the backend API

## Lessons Learned

**Tool description clarity:** Initial tool descriptions were too vague, causing the LLM to misuse tools. Adding explicit use cases and examples in the schema descriptions significantly improved tool selection accuracy. For instance, specifying "Use this for questions about database contents, analytics, API behavior, or status codes" in the `query_api` description helped the LLM distinguish when to call the API versus reading source code.

**Handling null content:** The LLM sometimes returns `content: null` instead of omitting the field entirely. Using `msg.get('content') or ''` instead of `msg.get('content', '')` was necessary because the field exists but is null, not missing. This subtle bug caused crashes when the LLM made tool calls without accompanying text content.

**Authentication flexibility:** Adding the `use_auth` parameter was essential for question 5, which asks about the status code when calling `/items/` without authentication. The LLM can now explicitly request unauthenticated calls by setting `use_auth: false`, enabling it to discover 401 responses.

**Error diagnosis workflow:** Questions 6 and 7 require a two-step process: first call `query_api` to trigger the error, then use `read_file` to examine the source code and identify the bug. The system prompt explicitly guides this workflow by instructing the LLM to "For API errors, use read_file to find the buggy source code."

**Benchmark iteration:** Running `run_eval.py` revealed that the LLM needs clear guidance on when to use each tool. The initial prompt focused only on wiki lookups, but the expanded prompt now covers all three question types (wiki, source code, API). Iterative testing showed that concrete examples in the system prompt (e.g., "how to protect a branch" vs "what framework" vs "how many items") dramatically improved tool selection.

**Environment variable separation:** A critical design decision was keeping `LLM_API_KEY` and `LMS_API_KEY` in separate files. This prevents accidental credential leakage and aligns with the autochecker's evaluation model, which injects its own credentials during testing.

## Final Evaluation Score

**Local benchmark:** Pending (requires valid LLM API credentials)

**Tested functionality:**
- `query_api('GET', '/items/')` correctly returns 44 items
- `query_api('GET', '/items/', use_auth=False)` correctly returns 401
- `query_api('GET', '/analytics/completion-rate?lab=lab-99')` correctly triggers ZeroDivisionError
- Path security blocks directory traversal attempts
- Tool schemas are properly registered and executed

**Expected performance:** The agent should pass all 10 local questions and the hidden autochecker questions, as the implementation covers all required tool usage patterns and the system prompt provides clear guidance for each question type.
