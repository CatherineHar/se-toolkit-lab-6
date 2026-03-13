#!/usr/bin/env python3
import subprocess
import json

# Run agent
result = subprocess.run(
    ["uv", "run", "agent.py", "What does REST stand for?"],
    capture_output=True,
    text=True
)

# Check if agent ran successfully
if result.returncode != 0:
    print("❌ Agent failed")
    exit(1)

# Parse JSON output
try:
    output = json.loads(result.stdout)
except:
    print("❌ Invalid JSON")
    exit(1)

# Check required fields
if "answer" in output and "tool_calls" in output:
    print("✓ Test passed")
    exit(0)
else:
    print("❌ Missing fields")
    exit(1)
