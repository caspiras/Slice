🍕

```css
▄█████ ▄▄    ▄▄  ▄▄▄▄ ▄▄▄▄▄
▀▀▀▄▄▄ ██    ██ ██▀▀▀ ██▄▄
█████▀ ██▄▄▄ ██ ▀████ ██▄▄▄
```

**A local-first IDE wrapper for Ollama models. Chat naturally. Edit code with diffs. Read/write documents. All permission-gated. All local.**

Slice is a beautiful terminal IDE that wraps local Ollama models with practical coding tools. Built with **Python** and the **Rich** library, it provides streaming chat, code editing with diffs, document operations, and git integration - all sandboxed to your project directory.

## 🆕 What's New in v1.4.0

- **🎯 Enhanced Model Behavior** - Major improvements to tool calling across models
  - Fixed critical system message issues preventing models from using tools correctly
  - Models now properly create Python apps with bash (not write_document)
  - Better tool calling behavior for gemma4, granite4, and other models
  - Added explicit guidance for creating executable files
  - Improved sequential tool execution (create file → run file)
  - Note: llama3.1 8B has poor tool calling support; use gemma4 or granite4 instead

### Previous Updates (v1.3.2)

- **📝 Convert to Markdown** - New `convert_to_markdown` tool for document conversion
  - Convert Excel, CSV, Word (with tables), and PDF files to Markdown format
  - Tables automatically formatted with Markdown table syntax (| separators)
  - Example: `convert budget.xlsx to budget.md`

### v1.3.1

- **📊 Word Document Table Extraction** - Tables in Word documents are now extracted alongside paragraphs
- **🚀 Large File Support** - New `convert_to_json` tool handles massive files efficiently
- **🔧 Dedicated Conversion Tool** - Replaces error-prone bash one-liners with proper error handling

### v1.3.0

- **🔄 Universal File to JSON Conversion** - Convert Excel, CSV, Word, and PDF files to JSON seamlessly
- **🐛 Fixed UI Issues** - Removed `<tool_call>` tags appearing in model output
- **💬 Better Tool Response** - Fixed models not responding after reading documents
- **🧹 Cleaner UI** - All spinners properly clean up after completion

### v1.2.0

- **📝 PDF Writing Enabled** - Create and edit PDFs directly
- **📊 Enhanced Spreadsheet Support** - Improved tool guidance for better Excel/CSV editing
- **🔄 Universal Document Editing** - ALL file types editable (PDF, Word, Excel, PowerPoint, CSV, Markdown, code)
- **⚡ Cross-Format Operations** - Move data between formats (PDF→Excel, Word→Markdown, etc.)

## What It Does

Slice brings IDE-like capabilities to local Ollama models through a permission-gated interface:

- 💬 **Natural conversation** - Ask questions, discuss code, get explanations
- ✏️ **Code editing with diffs** - Propose changes, review side-by-side diffs, apply with approval
- 📄 **Universal document editing** - Read/write PDF, Word, Excel, PowerPoint, CSV, Markdown, and ANY text-based file
- 🔧 **Bash execution** - Run commands after approval
- 🌳 **Git integration** - Stage, commit, create branches (never auto-pushes)
- 🔒 **Directory sandboxing** - All operations confined to current directory
- 🍕 **Beautiful terminal UI** - Streaming responses with Rich styling

## Prerequisites

Before installing Slice, you need:

1. **Python 3.9 or higher**
   ```bash
   python3 --version  # Should show 3.9+
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
   
   # Or try llama3.1 (works well for code tasks)
   ollama pull llama3.1
   ```

## Installation

```bash
# Clone the repository
git clone https://github.com/caspiras/Slice.git
cd Slice

# Install Python package
pip install -e .
```

## Uninstall

```bash
# Uninstall the package
pip uninstall slice
```

**Upgrading from v1.0 (slice-agent)?**
```bash
# Uninstall old version first
pip uninstall slice-agent -y

# Then install new version
pip install -e .
```

## Quick Start

```bash
# Start Slice
slice
```

1. **Select a model** using arrow keys (↑/↓) and press Enter
2. **Start chatting** at the 🍕 prompt
3. **Ask it to do things** - it will request permission before executing
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

**Code editing with diffs:**
```
🍕 read main.py and fix the typo where it says "resposne" instead of "response"
```
Shows a syntax-highlighted diff for your approval before applying changes.

**Document operations:**
```
🍕 what's the total in the budget.xlsx file for Q2?
🍕 create a PDF report called summary.pdf with our Q1 findings
🍕 read contract.pdf and extract the key terms into a spreadsheet
```
Read/write ANY document type - PDF, Excel, Word, CSV, Markdown, etc.

**File format conversion:**
```
🍕 convert budget.xlsx to budget.json
🍕 convert budget.xlsx to budget.md
🍕 convert report.docx to report.json
🍕 convert report.docx to report.md
🍕 convert contract.pdf to contract.json
🍕 convert data.csv to data.md
```
Seamlessly convert Excel, Word, PDF, and CSV files to JSON or Markdown format.

**Git workflows:**
```
🍕 check git status and create a commit with my changes
```
Stages files and creates commits (never auto-pushes without explicit request).

**File operations:**
- "Create a folder called src"
- "List all Python files in this directory"
- "Search for TODO comments in my code"

**Code exploration:**
- "Find all functions that use the requests library"
- "Show me files modified in the last 24 hours"
- "What's the overall structure of this project?"

### Switch Models Mid-Session
```
🍕 /model
```
Use arrow keys to pick a new model. Your conversation history is preserved!

## Security & Safety

Slice is designed with **security first**. Multiple layers protect your system:

### 🔒 Directory Sandboxing (Primary Protection)

**By default, all commands are restricted to the directory where you started `slice`.**

**💡 Best Practice:** Always start Slice inside a specific project folder, not in your home directory or system root. This provides natural boundaries for operations:

```bash
# ✅ Good - Start in a specific project
cd ~/projects/my-app
slice

# ❌ Avoid - Starting in home directory or root
cd ~
slice
```

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
- Slice can't silently access files outside your starting directory

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

Slice is built entirely in **Python** using the Rich library for beautiful terminal UX:

### Architecture Overview

```
┌──────────────────────────────────────┐
│  Slice (Python)                      │
│  ├─ Rich Terminal UI ✨              │
│  ├─ Ollama API Client                │
│  ├─ Chat Session Manager             │
│  ├─ Code Editor (with diffs)         │
│  ├─ Document Reader/Writer           │
│  ├─ Command Executor & Sandboxing    │
│  └─ Permission Prompt System         │
└──────────────────────────────────────┘
```

**Core capabilities:**
- **Rich terminal UI** - Beautiful panels, spinners, syntax highlighting
- **Ollama integration** - Streaming chat with tool calling support
- **Code editing** - Read files, generate diffs, apply changes with approval
- **Document operations** - Read/write PDF, Word, Excel, PowerPoint, CSV
- **Command execution** - Sandboxed bash with 30-second timeout
- **Git operations** - Stage, commit, branch (never auto-pushes)
- **Permission gates** - Every action requires explicit user approval

### Project Structure

```
slice_agent/
├── src/slice/
│   ├── main.py              # CLI entry point & startup
│   ├── ui.py                # Rich terminal UI components
│   ├── chat.py              # Chat session & tool execution
│   ├── executor.py          # Command executor & sandboxing
│   ├── document_reader.py   # PDF/Word/Excel/CSV reading
│   └── document_writer.py   # Document writing operations
└── pyproject.toml           # Python dependencies & metadata
```

## Development

```bash
# Install Python dependencies with dev tools
pip install -e ".[dev]"

# Run Python tests
pytest

# Format Python code
black src/

# Lint Python code
ruff check src/
```

### Key Dependencies

**Python:**
- **rich** - Beautiful terminal UI with panels, spinners, syntax highlighting
- **prompt-toolkit** - Interactive prompts with command history
- **ollama** - Python client for Ollama API
- **pypdf, reportlab** - PDF reading and writing
- **python-docx, openpyxl, python-pptx** - Word, Excel, PowerPoint operations

## Features

- ✏️ **Code Editing with Diffs**
  - Read source files and propose changes
  - Syntax-highlighted diff preview before applying
  - User approval required for every edit

- 📄 **Document Operations**
  - Read: PDF, Word (.docx), Excel (.xlsx), PowerPoint, CSV, text
  - Write: PDF, Word, Excel, PowerPoint, CSV, text
  - All document types in the directory are editable
  - Truncates large documents automatically for efficiency

- 🌳 **Git Integration**
  - Safe read-only operations (status, log, diff)
  - Local operations with approval (add, commit, branch)
  - Never auto-pushes without explicit user request

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

### Best for Code Tasks
- **llama3.1, llama3.2, llama3.3** - Trained heavily for tool use
- May try to execute commands for general knowledge questions
- Works perfectly for file operations and coding workflows

```bash
ollama pull llama3.1
```

**💡 Tip:** Models marked with `[tools ✓]` in the selector support function calling.

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
- Beautiful terminal UI powered by [Rich](https://github.com/Textualize/rich)
- Interactive prompts via [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
- Document handling with pypdf, reportlab, python-docx, openpyxl, python-pptx
- Inspired by the need for safe, permission-gated AI coding tools

---

**Made with 🍕 by the community**
