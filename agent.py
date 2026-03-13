#!/usr/bin/env python3
"""
Documentation Agent with agentic loop.
Uses LLM function calling to navigate the project wiki with read_file and list_files tools.
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env.agent.secret
load_dotenv('.env.agent.secret')

# Project root directory (where agent.py is located)
PROJECT_ROOT = Path(__file__).parent.resolve()

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def log_debug(message: str) -> None:
    """Print debug messages to stderr."""
    print(f"[DEBUG] {message}", file=sys.stderr)


def is_safe_path(requested_path: str) -> bool:
    """
    Check if the requested path is safe (within project root).
    Rejects paths containing '..' or absolute paths that escape project root.
    """
    # Reject paths with traversal
    if ".." in requested_path:
        return False
    
    # Reject absolute paths
    if os.path.isabs(requested_path):
        return False
    
    # Resolve and verify it's within project root
    try:
        resolved = (PROJECT_ROOT / requested_path).resolve()
        return str(resolved).startswith(str(PROJECT_ROOT))
    except (ValueError, OSError):
        return False


def read_file(path: str) -> str:
    """
    Read contents of a file from the project repository.
    
    Args:
        path: Relative path from project root.
    
    Returns:
        File contents as string, or error message if file doesn't exist.
    """
    if not is_safe_path(path):
        return f"Error: Access denied - path '{path}' is not allowed"
    
    file_path = PROJECT_ROOT / path
    
    if not file_path.exists():
        return f"Error: File not found - '{path}'"
    
    if not file_path.is_file():
        return f"Error: Not a file - '{path}'"
    
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading file: {str(e)}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root.
    
    Returns:
        Newline-separated listing of entries, or error message.
    """
    if not is_safe_path(path):
        return f"Error: Access denied - path '{path}' is not allowed"
    
    dir_path = PROJECT_ROOT / path
    
    if not dir_path.exists():
        return f"Error: Directory not found - '{path}'"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory - '{path}'"
    
    try:
        entries = sorted(dir_path.iterdir())
        lines = []
        for entry in entries:
            # Skip hidden files/directories and common non-wiki directories
            if entry.name.startswith('.'):
                continue
            if entry.name in ('.venv', '.git', 'node_modules', '__pycache__', '.qwen'):
                continue
            
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{entry.name}{suffix}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


# Tool schemas for LLM function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read wiki documentation files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover what wiki files are available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files
}

SYSTEM_PROMPT = """You are a documentation assistant that helps users find information in the project wiki.

You have access to two tools:
1. list_files - List files and directories at a given path
2. read_file - Read the contents of a file

When answering questions:
1. First use list_files to discover relevant wiki files (start with "wiki" directory)
2. Then use read_file to read the contents of relevant files
3. Find the specific section that answers the question
4. Provide a concise answer with the source reference

Source reference format: wiki/filename.md#section-anchor
- Use the file path relative to project root
- Add #section-anchor for the specific section (use lowercase with hyphens)

Always include the source field in your final answer pointing to the exact wiki file and section.

If you cannot find the answer after exploring relevant files, say so and suggest which files might contain the answer.

Think step by step: explore the wiki structure, read relevant files, then provide your answer with source."""


def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool with the given arguments.
    
    Args:
        tool_name: Name of the tool to execute.
        args: Arguments for the tool.
    
    Returns:
        Tool result as a string.
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{tool_name}'"
    
    func = TOOL_FUNCTIONS[tool_name]
    path = args.get("path", "")
    
    try:
        return func(path)
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def call_lllm(messages: list, tools: list, api_key: str, api_base: str, model: str) -> dict:
    """
    Call the LLM API with messages and tool definitions.
    
    Args:
        messages: List of message objects.
        tools: List of tool schemas.
        api_key: API key for authentication.
        api_base: Base URL for the API.
        model: Model name to use.
    
    Returns:
        Parsed response from the LLM.
    """
    url = f"{api_base}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.3,
        "max_tokens": 1500
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    
    return response.json()


def extract_source_from_content(content: str, file_path: str) -> str:
    """
    Try to extract a section anchor from the content based on headings.
    Returns a source reference like 'wiki/file.md#section'.
    """
    lines = content.split('\n')
    
    # Look for markdown headings that might indicate the relevant section
    for line in lines:
        if line.startswith('## ') or line.startswith('### '):
            # Extract heading text and convert to anchor
            heading = line.lstrip('#').strip()
            anchor = heading.lower().replace(' ', '-').replace('.', '')
            # Remove special characters except hyphens
            anchor = ''.join(c if c.isalnum() or c == '-' else '' for c in anchor)
            return f"{file_path}#{anchor}"
    
    # Default to just the file path if no section found
    return file_path


def main() -> None:
    """Main entry point for the agent."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ask a question to the documentation agent')
    parser.add_argument('question', type=str, help='The question to ask')
    args = parser.parse_args()

    # Get configuration from environment
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
    model = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat-v3-0324:free')

    if not api_key:
        log_debug("Missing LLM_API_KEY in .env.agent.secret")
        print(json.dumps({
            "answer": "Error: No API key found",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)

    try:
        log_debug(f"Starting agentic loop for question: {args.question}")

        # Initialize messages with system prompt and user question
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": args.question}
        ]

        # Track all tool calls for output
        tool_calls_log = []
        
        # Agentic loop
        iteration = 0
        final_answer = None
        final_source = None

        while iteration < MAX_TOOL_CALLS:
            iteration += 1
            log_debug(f"Iteration {iteration}/{MAX_TOOL_CALLS}")

            # Call LLM
            result = call_lllm(messages, TOOL_SCHEMAS, api_key, api_base, model)
            
            # Get the assistant message
            assistant_message = result['choices'][0]['message']
            
            # Check for tool calls
            tool_calls = assistant_message.get('tool_calls', [])
            
            if tool_calls:
                log_debug(f"LLM returned {len(tool_calls)} tool call(s)")
                
                # Add assistant message to conversation
                messages.append(assistant_message)
                
                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    tool_args = json.loads(tool_call['function']['arguments'])
                    
                    log_debug(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Execute the tool
                    tool_result = execute_tool(tool_name, tool_args)
                    
                    # Log the tool call
                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": tool_result
                    })
                
                # Continue the loop to get LLM's response to tool results
                continue
            else:
                # No tool calls - this is the final answer
                log_debug("LLM returned final answer (no tool calls)")
                final_answer = assistant_message.get('content', '')
                
                # Try to extract source from the answer or use a default
                # Look for patterns like "wiki/file.md" or "source: wiki/file.md"
                import re
                source_match = re.search(r'(wiki/[\w\-\.]+(?:#[\w\-]+)?)', final_answer)
                if source_match:
                    final_source = source_match.group(1)
                    # Ensure it has an anchor
                    if '#' not in final_source:
                        # Try to find section from recent file read
                        for tc in reversed(tool_calls_log):
                            if tc['tool'] == 'read_file':
                                final_source = extract_source_from_content(
                                    tc['result'], 
                                    tc['args']['path']
                                )
                                break
                elif tool_calls_log:
                    # Use the last read file as source
                    for tc in reversed(tool_calls_log):
                        if tc['tool'] == 'read_file':
                            final_source = extract_source_from_content(
                                tc['result'],
                                tc['args']['path']
                            )
                            break
                
                if not final_source:
                    final_source = "wiki/"
                
                break
        else:
            # Max iterations reached
            log_debug("Max tool calls reached")
            if not final_answer:
                final_answer = "I reached the maximum number of tool calls without finding a complete answer."
                final_source = ""

        # Prepare output
        output = {
            "answer": final_answer,
            "source": final_source or "",
            "tool_calls": tool_calls_log
        }

        # Print only JSON to stdout
        print(json.dumps(output, ensure_ascii=False, indent=2))

    except requests.exceptions.RequestException as e:
        log_debug(f"Error calling LLM: {str(e)}")
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)
    except Exception as e:
        log_debug(f"Unexpected error: {str(e)}")
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
