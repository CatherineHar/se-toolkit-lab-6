# Plan: System Agent with query_api Tool (Task 3)
#hello
## Goal   
Extend the Task 2 documentation agent with a `query_api` tool to talk to the deployed backend API. The agent will answer:
1. **Static system facts** — framework, ports, status codes (via `read_file` on source code)
2. **Data-dependent queries** — item count, scores, analytics (via `query_api`)
3. **Wiki documentation** — unchanged from Task 2 (via `read_file` and `list_files`)

## 1. query_api Tool Schema

Define an OpenAI-compatible function definition:

```json
{
  "name": "query_api",
  "description": "Call the deployed backend API to fetch data or trigger actions. Use this for questions about database contents, analytics, or API behavior.",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {
        "type": "string",
        "description": "HTTP method (GET, POST, PUT, DELETE, etc.)",
        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
      },
      "path": {
        "type": "string",
        "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
      },
      "body": {
        "type": "string",
        "description": "Optional JSON request body for POST/PUT/PATCH requests"
      }
    },
    "required": ["method", "path"]
  }
}
```

## 2. query_api Tool Implementation

```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    """
    Call the deployed backend API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path
        body: Optional JSON request body
        
    Returns:
        JSON string with status_code and body
    """
    # Read configuration from environment
    api_base = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    api_key = os.getenv('LMS_API_KEY')
    
    url = f"{api_base}{path}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json.loads(body) if body else None,
            timeout=30
        )
        
        result = {
            "status_code": response.status_code,
            "body": response.text
        }
        return json.dumps(result)
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "error": str(e)
        })
```

### Authentication
- Use `LMS_API_KEY` from `.env.docker.secret` (NOT the LLM API key)
- Send as `Authorization: Bearer <LMS_API_KEY>` header
- Default `AGENT_API_BASE_URL` to `http://localhost:42002` (Caddy proxy port)

## 3. System Prompt Update

Update the system prompt to guide the LLM on when to use each tool:

```
You are a system agent that helps users find information about the project.

You have access to these tools:
1. list_files - List files and directories at a given path
2. read_file - Read the contents of a file (use for wiki docs and source code)
3. query_api - Call the backend API (use for data queries and API behavior questions)

Tool selection guide:
- Use list_files/read_file with "wiki/" path for documentation questions
- Use read_file with source code paths (backend/app/, docker-compose.yml, etc.) for system facts
- Use query_api for questions about database contents, analytics, or API responses

When answering questions:
1. Identify what type of information is needed
2. Use the appropriate tool(s)
3. For API errors, use read_file to find the buggy source code
4. Provide concise answers with source references when applicable
```

## 4. Environment Variables

The agent must read all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api (default: http://localhost:42002) | Optional, defaults to localhost |

**Important**: The autochecker runs with different credentials. Never hardcode values.

## 5. Step-by-Step Tasks

- [x] Create `plans/task-3.md` (this file)
- [ ] Add `query_api` tool function to `agent.py`
- [ ] Add `query_api` schema to `TOOL_SCHEMAS`
- [ ] Register `query_api` in `TOOL_FUNCTIONS`
- [ ] Update `SYSTEM_PROMPT` with tool selection guidance
- [ ] Test: `uv run agent.py "How many items are in the database?"`
- [ ] Run `uv run run_eval.py` and iterate on failures

## 6. Benchmark Questions Analysis

| # | Question | Tool(s) Required | Notes |
|---|----------|------------------|-------|
| 0 | Wiki: protect a branch | read_file | Wiki lookup |
| 1 | Wiki: SSH connection | read_file | Wiki lookup |
| 2 | What web framework? | read_file | Read backend/app/main.py |
| 3 | List API routers | list_files | List backend/app/routers/ |
| 4 | How many items in DB? | query_api | GET /items/ |
| 5 | Status code without auth? | query_api | GET /items/ without Authorization header |
| 6 | /analytics/completion-rate error | query_api, read_file | ZeroDivisionError bug |
| 7 | /analytics/top-learners crash | query_api, read_file | TypeError/None bug |
| 8 | Request lifecycle | read_file | Read docker-compose.yml, Dockerfile |
| 9 | ETL idempotency | read_file | Read backend/app/etl.py |

## 7. Known Bugs to Discover

### Bug 1: ZeroDivisionError in /analytics/completion-rate
When a lab has no data, `total_learners` is 0, causing division by zero.

### Bug 2: TypeError in /analytics/top-learners
When there are no interactions, `rows` is empty and `sorted()` may fail on None values.

## 8. Acceptance Criteria

- [ ] `query_api` tool correctly calls backend with authentication
- [ ] Agent passes all 10 local benchmark questions
- [ ] Agent uses correct tools for each question type
- [ ] Environment variables are read dynamically (no hardcoding)
- [ ] Error responses from API are handled gracefully

## 9. Iteration Log

*To be filled after first run_eval.py execution*

### Initial Score
- Date: 2026-03-14
- Score: Pending (LLM API key needs valid credentials)

### Implementation Status
- [x] `query_api` tool function implemented with authentication
- [x] `query_api` schema added to TOOL_SCHEMAS
- [x] `query_api` registered in TOOL_FUNCTIONS
- [x] SYSTEM_PROMPT updated with tool selection guidance
- [x] execute_tool updated to handle query_api arguments
- [x] Fixed `content: null` handling issue
- [x] Added `use_auth` parameter for unauthenticated requests (question 5)

### First Failures
- Issue: LLM API key (OpenRouter) returns 429/402 errors
- Fix: Autochecker will inject valid credentials during evaluation

### Iteration Strategy
1. Verify query_api tool works correctly (done - tested manually)
2. Ensure system prompt guides LLM to use correct tools
3. Test with autochecker credentials when available
4. Fix any tool selection issues based on evaluation feedback

### Manual Testing Results
- `query_api('GET', '/items/')` - Returns items list correctly (44 items)
- `query_api('GET', '/items/', use_auth=False)` - Returns 401 "Not authenticated"
- `query_api('POST', '/pipeline/sync')` - Triggers ETL sync
- Authentication with LMS_API_KEY works correctly
- Error handling for missing API key works correctly
