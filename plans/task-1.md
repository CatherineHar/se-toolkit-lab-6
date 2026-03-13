2. Get question from command line: `uv run agent.py "question"`
3. Call OpenRouter API using OpenAI client [citation:1][citation:5]
4. Print JSON to stdout: `{"answer": "...", "tool_calls": []}`
5. Print debug info to stderr
6. Exit 0 on success, 1 on error

### 5. What I'll Do Step by Step
- [ ] Create OpenRouter account and get API key
- [ ] Copy `.env.agent.example` to `.env.agent.secret` and add OpenRouter key
- [ ] Create `agent.py` with OpenRouter API call
- [ ] Test manually: `uv run agent.py "What is REST?"`
- [ ] Write `AGENT.md` explaining OpenRouter setup
- [ ] Create test in `test_agent.py`
- [ ] Run test to verify
- [ ] Commit and PR

### 6. Requirements Check
- [ ] Output is only JSON (no extra text)
- [ ] Has "answer" and "tool_calls" fields
- [ ] tool_calls is empty array
- [ ] Responds in < 60 seconds
- [ ] Exit code 0 if OK