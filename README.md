```
🍕

▄█████ ▄▄    ▄▄  ▄▄▄▄ ▄▄▄▄▄   ▄████▄  ▄▄▄▄ ▄▄▄▄▄ ▄▄  ▄▄ ▄▄▄▄▄▄
▀▀▀▄▄▄ ██    ██ ██▀▀▀ ██▄▄    ██▄▄██ ██ ▄▄ ██▄▄  ███▄██   ██
█████▀ ██▄▄▄ ██ ▀████ ██▄▄▄   ██  ██ ▀███▀ ██▄▄▄ ██ ▀██   ██
```

**Chat with AI. Let it suggest commands. Approve what runs. Stay in control.**

A Python CLI tool that turns local Ollama AI models into interactive agents that can execute commands on your system - but only with your explicit permission.

## What It Does

Most AI chat tools are either pure chatbots (can answer questions but can't do anything) or autonomous agents (do things automatically, which can be risky). Slice Agent bridges this gap:

- 💬 **Chat naturally** with AI about anything
- 🔧 **Let it suggest commands** when you ask it to do something
- ✅ **You approve every action** before it runs
- 🔒 **Sandboxed to your current directory** for safety
- 🍕 **Beautiful terminal UI** with streaming responses

## Prerequisites

Before installing Slice Agent, you need:

1. **Python 3.9 or higher**
   ```bash
   python --version  # Should show 3.9+
   ```

2. **Ollama installed and running**
   - Download from [ollama.ai](https://ollama.ai/)
   - Install for your OS (macOS, Linux, Windows)

3. **At least one Ollama model downloaded**
   ```bash
   # Recommended models for best results:
   ollama pull gemma4      # Best for mixed chat/actions
   ollama pull mistral     # Fast and reliable
   ollama pull qwen2       # Great multilingual support
   
   # Or try llama3.1 (works best for code/agentic tasks)
   ollama pull llama3.1
   ```

## Installation

```bash
# Clone the repository
git clone https://github.com/caspiras/Slice-Agent.git
cd Slice-Agent

# Install the package
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Uninstall

```bash
# Uninstall the package
pip uninstall slice-agent

# Confirm when prompted
# Note: This removes the 'slice' command from your system
```

## Quick Start

```bash
# Start the agent
slice
```

1. **Select a model** using arrow keys (↑/↓) and press Enter
2. **Start chatting** at the 🍕 prompt
3. **Ask it to do things** - it will request permission before running commands
4. **Switch models anytime** by typing `/model`
5. **Exit gracefully** with Ctrl+C (twice)

## Usage Examples

### Just Chat
```
🍕 what is Python?
```
The AI answers directly from knowledge - no commands, just conversation.

### Ask It to Do Something
```
🍕 create a file called notes.txt
```

You'll see:
```
🔧 Action Requested
To create a new text file

┌─ Command ────────────┐
│ touch notes.txt      │
└──────────────────────┘

Execute this command? (y/N): y
✓ Command completed successfully
```

### Common Use Cases

**File operations:**
- "List all files in this directory"
- "Create a folder called src"
- "Delete test.txt"

**Git workflows:**
- "Show me git status"
- "What changed in the last commit?"
- "Check if I have uncommitted changes"

**Code exploration:**
- "Find all Python files"
- "Show me files modified today"
- "Search for the word 'TODO' in this directory"

**Mixed chat + actions:**
- "What's a good name for a config file? Then create it for me"
- "Explain what git status does, then run it"

### Switch Models Mid-Session
```
🍕 /model
```
Use arrow keys to pick a new model. Your conversation history is preserved!

## Security & Safety

Slice Agent is designed with **security first**. Multiple layers protect your system:

### 🔒 Directory Sandboxing (Primary Protection)

**By default, all commands are restricted to the directory where you started `slice`.**

Commands attempting to access files outside trigger a **red warning**:

```
⚠️  SANDBOX ESCAPE DETECTED
This command tries to access paths outside: /your/current/directory
Suspicious paths:
  • /etc/hosts (absolute path)
  • ~/Documents (home directory)
  • ../../../file.txt (parent directory)

⚠️  Are you SURE you want to execute this? (yes/N):
```

**Protected patterns:**
- ✋ Absolute paths: `/tmp/file`, `/etc/hosts`
- ✋ Home directory: `~/Documents/file`
- ✋ Parent traversal: `../../sensitive/file`
- ✋ Directory changes: `cd /tmp`

**Override when needed:**
- Normal commands: Type **y** to approve
- Sandbox escapes: Type **yes** (full word) to explicitly approve
- The agent can't silently access files outside your starting directory

### 🛡️ Additional Safety Layers

1. **Permission prompts for EVERY command**
   - See exactly what will run before it executes
   - Includes the reason/context from the AI
   - Easy to review and deny

2. **Dangerous command detection**
   - Patterns like `rm -rf /`, `mkfs`, `dd if=` trigger warnings
   - Requires explicit "yes" confirmation

3. **30-second execution timeout**
   - Prevents runaway or hanging commands
   - Automatically kills commands that take too long

4. **No automatic execution**
   - The AI can't run anything without your approval
   - Even if the model tries, you see the prompt first

### 🔐 Privacy & Data

- ✅ **100% local**: Everything runs on your machine via Ollama
- ✅ **No cloud API calls**: Your conversations never leave your computer
- ✅ **No data persistence**: Conversation history only exists while running
- ✅ **No telemetry**: No tracking, logging, or data collection

## How It Works (Technical)

Slice Agent uses a dual-mode approach for detecting when to execute commands:

### Tool Calling Mode (Preferred)
For models that support Ollama's function calling API:
- The model is given an `execute_command` tool definition
- When it wants to run a command, it calls the tool with parameters
- You're prompted for permission before execution
- Results are fed back to the model for its final response

### XML Fallback Mode
For models without tool support:
- System prompt instructs the model to wrap commands in XML tags
- Pattern: `<action command='ls'>reason</action>`
- The agent parses XML and extracts commands
- Same permission flow as tool calling mode

The agent automatically detects model capabilities and selects the appropriate mode.

### Architecture

```
src/slice_agent/
├── main.py      # CLI entry point and signal handling
├── ui.py        # Terminal UI components (model selector, chat interface)
├── agent.py     # Agent logic with tool calling and XML fallback
└── executor.py  # Safe command execution with permission prompts
```

**Separation of concerns:**
- `main.py`: Entry point, signal handling (double Ctrl+C), orchestration
- `ui.py`: All terminal rendering using Rich and prompt-toolkit
- `agent.py`: Conversation state, Ollama API calls, action detection
- `executor.py`: Command execution, sandboxing, safety checks

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Lint
ruff check src/

# Type check (if mypy is configured)
mypy src/
```

### Key Dependencies
- **ollama** - Python client for Ollama API
- **rich** - Terminal styling, panels, spinners, live displays
- **prompt-toolkit** - Interactive prompts with key bindings

## Features

- 🎯 **Dual-Mode Action Detection**
  - Tool/function calling for capable models (llama3, mistral, gemma, qwen2)
  - XML fallback for models without tool support
  - Automatic detection and mode selection

- 🍕 **Beautiful Terminal UI**
  - Pizza emoji (🍕) prompt cursor
  - "baking..." spinner while AI thinks
  - Streaming responses (see text appear word-by-word)
  - Clean panels for commands and output

- 🔄 **Model Switching**
  - Interactive arrow-key selection at startup
  - Switch models anytime with `/model` command
  - Conversation history preserved when switching

- ⌨️ **Great UX**
  - Double Ctrl+C to exit (with warning on first press)
  - Interruption support during streaming
  - Clear success/failure indicators

- 🔒 **Security First**
  - Directory sandboxing with escape detection
  - Permission gates for all commands
  - Dangerous pattern warnings
  - 30-second command timeout

## Model Recommendations

**Different models behave differently.** Choose based on your task:

### Best for Mixed Chat + Actions
- **gemma4** - Excellent at knowing when to chat vs. execute commands
- **mistral** - Fast, reliable, good tool calling judgment
- **qwen2** - Great multilingual support with smart tool use

```bash
ollama pull gemma4
```

### Best for Code/Agentic Tasks
- **llama3.1, llama3.2, llama3.3** - Trained heavily for tool use
- May try to execute commands for general knowledge questions
- Works perfectly for file operations and coding workflows

```bash
ollama pull llama3.1
```

**💡 Tip:** Models marked with `[tools ✓]` in the selector support function calling. Models marked `[tools ✗]` use XML fallback (still work, just different implementation).

## Troubleshooting

### "No local Ollama models found"
- Make sure Ollama is running: `ollama list` should show your models
- Download a model: `ollama pull gemma4`
- Verify Ollama service is active

### Command stuck on "baking..."
- This usually means a permission prompt is waiting
- The latest version fixes display issues - update if needed
- Try pressing Ctrl+C to cancel and restart

### Model tries to run commands for chat questions
- This is model-specific behavior (common with llama3.1/3.2/3.3)
- These models are trained heavily for tool use
- Switch to gemma4, mistral, or qwen2 for better chat/action balance
- Use `/model` command to switch without restarting

### "Command timed out after 30 seconds"
- The command took too long and was automatically killed for safety
- Try breaking the task into smaller commands
- Some operations (large builds, downloads) may need to be run manually

### Exit not working
- Press Ctrl+C **twice** (first shows warning, second exits)
- If stuck in a prompt, Ctrl+C cancels it first, then exit normally
- Make sure you're pressing Ctrl+C, not Ctrl+D

### Permission prompt not visible
- Update to the latest version - older versions had display issues
- The prompt should appear after the "baking..." spinner stops

## Contributing

Contributions are welcome! This is an open-source project.

**Ideas for contributions:**
- Support for additional Ollama models
- New safety/security features
- UI/UX improvements
- Bug fixes and performance improvements
- Documentation improvements

**To contribute:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. See the repository for license details.

## Acknowledgments

- Built with [Ollama](https://ollama.ai/) for local AI model hosting
- UI powered by [Rich](https://github.com/Textualize/rich) and [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
- Inspired by the need for safe, permission-gated AI agents

---

**Made with 🍕 by the community**
