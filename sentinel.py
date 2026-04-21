#!/usr/bin/env python3
"""Sentinel: System Administrator AI assistant for Linux operators using Groq API.

Features:
- Expert system admin diagnoses for failed commands and system issues
- Leverages Groq API with llama-3.3-70b-versatile for intelligent recommendations
- Show recent shell commands from history
- Optionally execute suggested fixes after explicit approval
- Real-time system context (load, memory, disk, uptime)

Usage:
  sentinel.py <issue text>          # Free-form system admin question
  sentinel.py recent -n 10          # Show recent commands
  sentinel.py diagnose --command "cmd" --error "error msg"  # Diagnose specific error
"""

import os
import sys
import json
import subprocess
import re
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

try:
    from groq import Groq
except ImportError:
    Groq = None

# Load .env file from project directory
_project_dir = Path(__file__).parent
load_dotenv(_project_dir / ".env")

# Conversation history file
_history_file = _project_dir / ".conversation_history"


def load_conversation_history() -> str:
    """Load recent conversation history for context."""
    if not _history_file.exists():
        return ""
    try:
        with open(_history_file, 'r') as f:
            lines = f.readlines()[-10:]  # Last 10 lines (5 exchanges)
            return "".join(lines).strip()
    except Exception:
        return ""


def save_to_conversation_history(user_query: str, response: str) -> None:
    """Append to conversation history."""
    try:
        with open(_history_file, 'a') as f:
            f.write(f"User: {user_query}\n")
            f.write(f"Assistant: {response}\n")
    except Exception:
        pass


def clear_conversation_history() -> None:
    """Clear conversation history."""
    try:
        _history_file.unlink(missing_ok=True)
    except Exception:
        pass


def get_history() -> str:
    """Reads the last few commands from shell history."""
    try:
        hist_file = os.path.expanduser("~/.zsh_history")
        if not os.path.exists(hist_file):
            hist_file = os.path.expanduser("~/.bash_history")
        
        if os.path.exists(hist_file):
            with open(hist_file, 'r', errors='ignore') as f:
                lines = f.readlines()[-10:]
                cmds = []
                for line in lines:
                    if ';' in line:
                        cmd = line.split(';')[-1].strip()
                    else:
                        cmd = line.strip()
                    if cmd:
                        cmds.append(cmd)
                return "\n".join(cmds)
    except Exception:
        pass
    return "No history found."


def gather_system_context() -> str:
    """Gather current system diagnostics for context."""
    ctx_parts = []
    
    try:
        with open("/proc/loadavg") as f:
            load = f.read().strip()
            ctx_parts.append(f"Load: {load}")
    except Exception:
        pass
    
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()[:3]
            ctx_parts.append(f"Memory: {' | '.join(line.strip() for line in lines)}")
    except Exception:
        pass
    
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                ctx_parts.append(f"Disk: {lines[1]}")
    except Exception:
        pass
    
    return "\n".join(ctx_parts) if ctx_parts else "(system diagnostics unavailable)"


def is_dangerous(cmd: str) -> bool:
    """Check if command is potentially dangerous."""
    danger_patterns = [
        r"\bsudo\b",
        r"\brm\b",
        r"/etc/",
        r"\bchmod\b",
        r"\bchown\b",
        r"\bsystemctl\s+(enable|disable|restart|stop)\b",
        r"\bsed\s+-i\b",
    ]
    return any(re.search(p, cmd) for p in danger_patterns)


def maybe_tag_danger(command: str, thought: str) -> str:
    """Add danger warning if command is risky."""
    if not is_dangerous(command):
        return thought
    return (
        "⚠️ DANGER: This command uses elevated privileges or changes system state. "
        "Review target paths/services carefully before running. "
        + thought
    )


def extract_backtick_commands(text: str) -> list:
    """Extract commands wrapped in backticks."""
    return re.findall(r'`([^`]+)`', text)


def analyze_with_groq(query: str) -> str:
    """Use Groq API to analyze user issue and return conversational response."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or Groq is None:
        print("❌ Error: GROQ_API_KEY not set in .env file", file=sys.stderr)
        sys.exit(1)
    
    history = get_history()
    system_context = gather_system_context()
    conversation_history = load_conversation_history()
    
    conv_context = ""
    if conversation_history:
        conv_context = f"\nPrevious conversation context:\n{conversation_history}\n"
    
    prompt = f"""You are Sentinel, an expert Linux System Administrator. Be brief, professional, direct.

System:
{system_context}

Recent shell commands:
{history}
{conv_context}
Current User Query:
{query}

Respond naturally and conversationally. If you suggest a command, wrap it in backticks like `command here`. No "Thought:" or "Command:" labels. Remember context from previous messages.""".strip()

    try:
        client = Groq(api_key=api_key)
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=512
        )
        response = chat.choices[0].message.content.strip()
        save_to_conversation_history(query, response)
        return response
    
    except Exception as e:
        print(f"❌ Groq API error: {e}", file=sys.stderr)
        sys.exit(1)


def print_recent(count: int) -> int:
    """Show recent commands."""
    history = get_history()
    if not history or history == "No history found.":
        print("No shell history found.")
        return 1
    
    cmds = [c for c in history.split("\n") if c.strip()]
    print(f"Recent commands ({len(cmds)}):")
    for i, cmd in enumerate(cmds[-count:], start=1):
        print(f"{i}. {cmd}")
    return 0


def run_command(command: str) -> int:
    """Execute a shell command."""
    shell_path = os.environ.get("SHELL") or "/bin/sh"
    proc = subprocess.run(command, shell=True, executable=shell_path)
    return proc.returncode


def cmd_recent(args: argparse.Namespace) -> int:
    """Handle 'recent' subcommand."""
    return print_recent(args.count)


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Handle 'diagnose' subcommand."""
    issue_text = f"Command: {args.command}\nError: {args.error}"
    response = analyze_with_groq(issue_text)
    print(response)
    
    commands = extract_backtick_commands(response)
    if commands:
        if len(commands) == 1:
            answer = input("\nRun this command? [y/N]: ").strip().lower()
            if answer == "y":
                code = run_command(commands[0])
                print(f"Exit code: {code}")
                return code
        else:
            print(f"\n{len(commands)} commands found. Run one? [y/N]: ", end="")
            answer = input().strip().lower()
            if answer == "y":
                for i, cmd in enumerate(commands, 1):
                    print(f"{i}. {cmd}")
                try:
                    choice = int(input("Which one? [1-{}]: ".format(len(commands))).strip())
                    if 1 <= choice <= len(commands):
                        code = run_command(commands[choice - 1])
                        print(f"Exit code: {code}")
                        return code
                except (ValueError, IndexError):
                    print("Invalid choice.")
    
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    """Handle free-text query mode."""
    issue_text = " ".join(args.query).strip()
    if not issue_text:
        print("Usage: sentinel <issue text>")
        return 2
    
    response = analyze_with_groq(issue_text)
    print(response)
    
    commands = extract_backtick_commands(response)
    if commands:
        if len(commands) == 1:
            answer = input("\nRun this command? [y/N]: ").strip().lower()
            if answer == "y":
                code = run_command(commands[0])
                print(f"Exit code: {code}")
                return code
        else:
            print(f"\n{len(commands)} commands found. Run one? [y/N]: ", end="")
            answer = input().strip().lower()
            if answer == "y":
                for i, cmd in enumerate(commands, 1):
                    print(f"{i}. {cmd}")
                try:
                    choice = int(input("Which one? [1-{}]: ".format(len(commands))).strip())
                    if 1 <= choice <= len(commands):
                        code = run_command(commands[choice - 1])
                        print(f"Exit code: {code}")
                        return code
                except (ValueError, IndexError):
                    print("Invalid choice.")
    
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(description="Sentinel: Linux admin assistant powered by Groq")
    sub = parser.add_subparsers(dest="subcmd", required=True)
    
    p_recent = sub.add_parser("recent", help="Show recent shell commands")
    p_recent.add_argument("-n", "--count", type=int, default=5, help="How many commands to show")
    p_recent.set_defaults(func=cmd_recent)
    
    p_diag = sub.add_parser("diagnose", help="Diagnose a failed command")
    p_diag.add_argument("--command", required=True, help="Original command that failed")
    p_diag.add_argument("--error", required=True, help="Error output text")
    p_diag.add_argument("--run", action="store_true", help="Prompt to run suggested fix")
    p_diag.set_defaults(func=cmd_diagnose)
    
    return parser


def main() -> int:
    """Main entry point."""
    known_subcommands = {"recent", "diagnose", "-h", "--help"}
    
    if len(sys.argv) > 1 and sys.argv[1] not in known_subcommands:
        issue_args = argparse.Namespace(query=sys.argv[1:])
        return cmd_chat(issue_args)
    
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
