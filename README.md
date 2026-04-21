# sentinel

Expert Linux System Administrator AI assistant for your terminal.

Powered by Groq's `llama-3.3-70b-versatile` model. Conversational, context-aware, and optionally executes suggested fixes.

## What it does

- Expert Linux System Administrator AI powered by Groq
- Conversational responses with contextual system diagnostics (load, memory, disk)
- Maintains conversation history for multi-turn context
- Suggests commands wrapped in backticks—optionally run them with approval
- Three modes:
  - **Free-text**: `sentinel.py <issue text>` - Ask any Linux sysadmin question
  - **Recent**: `sentinel.py recent -n 10` - Show recent shell commands
  - **Diagnose**: `sentinel.py diagnose --command "cmd" --error "msg"` - Analyze specific errors

## Quick start

```bash
# 1. Install sentinel globally (creates venv + installs dependencies)
cd /home/mike/Development/sentinel
bash install.sh

# 2. Set up your Groq API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY from https://console.groq.com

# 3. Use it
sentinel what is my cpu usage?
```

## Usage

**Free-text conversation** (default mode):

```bash
sentinel what is my cpu usage?
sentinel I can't connect to docker
sentinel how to check disk usage?
```

Sentinel prints an AI response + any suggested commands. Commands are wrapped in backticks:

```text
Your load average is... You can check with `uptime`. Want to run it? [y/N]:
```

Answer `y` to run, anything else to skip.

**Show recent commands**:

```bash
sentinel.py recent -n 10
```

**Diagnose a specific error**:

```bash
sentinel.py diagnose --command "nmap -sV 10.0.0.1" --error "nmap: command not found"
```

## Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```ini
# Your Groq API key from https://console.groq.com
GROQ_API_KEY=your-api-key-here
```

The `.env` file is automatically loaded when you run Sentinel, and it's ignored by git for security.

## Requirements

- **Groq API Key** - Required to run (get from https://console.groq.com)
- Python 3.7+
- Dependencies: `groq>=0.4.0`, `python-dotenv>=1.0.0`