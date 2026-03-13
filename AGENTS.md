# Agent Documentation (OpenRouter)

## Overview
A simple CLI agent that connects to OpenRouter API and returns structured JSON responses. OpenRouter provides unified access to 100+ AI models through a single API. [citation:1][citation:9]

## Why OpenRouter?
- **Works in Russia** - No blocks, no VPN required
- **Free models available** - DeepSeek, Gemma, Mistral, and others [citation:2][citation:7]
- **One API for all models** - Switch between providers without code changes [citation:5]
- **OpenAI-compatible** - Works with standard OpenAI client libraries

## Setup Instructions

### 1. Get OpenRouter API Key [citation:4][citation:6]
1. Go to [OpenRouter.ai](https://openrouter.ai) and sign up
2. Click your profile icon → "Keys" [citation:6]
3. Click "Create API Key"
4. Give it a name and copy the key (starts with `sk-or-`)

### 2. Configure Environment
Copy the example file and add your key:
```bash
cp .env.agent.example .env.agent.secret
# Edit .env.agent.secret and add your OpenRouter key