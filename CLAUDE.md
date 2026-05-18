# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Slice** is a sandboxed IDE-like wrapper for local Ollama models. Built with **Go + Python hybrid architecture**, it provides a terminal interface with permission-gated command execution and document operations.

## Key Architecture Principles

### Go + Python Hybrid

**Go handles** (fast, compiled):
- CLI entry point and argument parsing
- Terminal UI (bubbletea + lipgloss)
- Signal handling (Ctrl+C double-press)
- Command execution with 30-second timeout
- Directory sandboxing and permission prompts
- Conversation state management

**Python handles** (ecosystem strength):
- Ollama API integration (streaming, tool calls)
- Document operations (PDF, Word, Excel, PowerPoint, CSV)
- Automation script generation and execution

**Communication:** JSON request/response over stdin/stdout. Go spawns Python as subprocess.

### Permission-Gated Actions
The core principle: **always ask permission before executing actions**. This means:

- **Chat responses**: Flow naturally without interruption
- **Action requests**: Detected, presented to user, and only executed with explicit approval
- The distinction is critical—don't break chat flow with permission prompts unless an actual system action is requested

### Signal Handling (Ctrl+C)
The application uses a custom signal handler with double-press-to-exit behavior:
- **First Ctrl+C**: Warning message, increments `exit_count`
- **Second Ctrl+C**: Actual exit
- This applies both to prompt input and during model output streaming
- The signal handler is set up in `cmd/slice/main.go` and must not be overridden by other components

### UI/UX Requirements
- **Prompt cursor**: Must be 🍕 (pizza emoji)
- **Thinking indicator**: Must show "baking..." with a spinner (not frozen, not stuck)
- **Streaming responses**: Tokens appear word-by-word as the model generates them
- **Model selection**: User selects with arrow keys from list of local Ollama models
- **Model switching**: User can type `/model` during chat to switch to a different model without restarting
- **Graceful degradation**: Handle Ollama connection failures, missing models, etc.

## Project Structure

```
slice_tool/
├── cmd/slice/
│   └── main.go                    # Go entry point
├── internal/
│   ├── ui/
│   │   ├── app.go                 # Main bubbletea app orchestrator
│   │   ├── chat.go                # Chat view with streaming
│   │   ├── model_selector.go      # Model selection view
│   │   └── styles.go              # Lipgloss styles
│   ├── executor/
│   │   ├── executor.go            # Command execution with timeout
│   │   ├── sandbox.go             # Sandboxing & path validation
│   │   └── permissions.go         # Permission prompts
│   ├── python/
│   │   ├── service.go             # Python subprocess management
│   │   └── protocol.go            # JSON request/response types
│   └── state/
│       ├── conversation.go        # Conversation history
│       └── tracking.go            # Anti-loop tracking
├── python/
│   ├── service.py                 # Main Python service (JSON stdin/stdout)
│   ├── ollama_client.py           # Ollama API wrapper
│   ├── document_reader.py         # Read PDF, Word, Excel, CSV, text
│   ├── document_writer.py         # Write Word, Excel, PowerPoint, CSV, text
│   └── automation.py              # Script generation & execution
├── go.mod                         # Go dependencies
└── pyproject.toml                 # Python dependencies
```

**Separation of concerns:**
- **Go (cmd/, internal/)**: CLI, UI, command execution, sandboxing, orchestration
- **Python (python/)**: Ollama API, document operations, automation scripts
- **Bridge (internal/python/)**: JSON communication between Go and Python

## Development Commands

```bash
# Install Python dependencies with dev tools
pip install -e ".[dev]"

# Build Go binary
go build -o slice cmd/slice/main.go

# Run the CLI locally
./slice

# Run Go tests
go test ./...

# Format Go code
go fmt ./...

# Run Python tests
pytest

# Format Python code (Black - line-length 100)
black python/

# Lint Python code (Ruff - line-length 100)
ruff check python/
```

**Note:** Both Black and Ruff are configured for line-length=100 and target Python 3.9+ (see pyproject.toml).

## Key Dependencies

- **rich**: Terminal styling, panels, spinners, console output
- **ollama**: Python client for Ollama API (model listing, chat)
- **prompt-toolkit**: Interactive prompt with key bindings
- **pypdf**: PDF reading
- **python-docx**: Word document reading and writing
- **openpyxl**: Excel spreadsheet reading and writing
- **python-pptx**: PowerPoint presentation creation and modification

## Action Detection Implementation

The tool uses a **dual-mode approach** for detecting and executing actions:

### Tool Calling Mode (Preferred)
For models that support Ollama's function/tool calling:
- Model is given an `execute_command` tool definition
- When the model wants to run a command, it calls the tool with parameters
- User is prompted for permission before execution
- Results are fed back to the model for final response

**Supported models**: llama3.x, mistral, mixtral, command-r, qwen2

### XML Fallback Mode
For models without tool support:
- System prompt instructs model to wrap commands in XML: `<action command='ls'>reason</action>`
- Agent parses XML tags and extracts commands
- User is prompted for permission before execution
- Results are injected back into the response text

The tool automatically detects model capabilities and selects the appropriate mode.

## Document Operations

The tool supports comprehensive document reading and writing across multiple formats.

### Document Reading
Via `read_document` tool or `<read file='...'/>` XML tag:

**Supported formats:**
- **PDF (.pdf)** - Extract text content from all pages
- **Word (.docx)** - Read paragraphs and tables
- **Excel (.xlsx)** - Read all sheets with row/column data (row-numbered format)
- **CSV (.csv)** - Read all rows with row numbers
- **Text files** (.txt, .md, .py, .js, etc.) - Read content with encoding detection

**Key behaviors:**
- Excel files return ALL sheets and data at once - no need to re-read
- Row-numbered format makes it easy to reference specific data
- Built-in encoding detection for text files
- Legacy .xls format not supported (must convert to .xlsx)

### Document Writing
Via `write_document` tool or `<write file='...' operations='...'/>` XML tag:

**Supported formats:**
- **Word (.docx)** - Append paragraphs, replace text, insert content
- **Excel (.xlsx)** - Set cells, append rows, modify columns
- **PowerPoint (.pptx)** - Add slides with title and content
- **CSV (.csv)** - Append rows, modify cells
- **Text files** - Replace content, append text, find/replace
- **PDF (.pdf)** - **NOT SUPPORTED** (PDFs are read-only by design)

**Operation examples:**

```python
# Word operations
{"type": "append_paragraph", "text": "New paragraph text"}
{"type": "replace_text", "find": "old text", "replace": "new text"}
{"type": "insert_after", "search": "Section Header", "text": "New content"}

# Excel operations
{"type": "set_cell", "sheet": "Sheet1", "row": 5, "col": "M", "value": "Data"}
{"type": "append_row", "sheet": "Sheet1", "values": ["A", "B", "C"]}
{"type": "set_column", "sheet": "Sheet1", "col": "M", "start_row": 3, "values": ["X", "Y", "Z"]}

# PowerPoint operations
{"type": "add_slide", "title": "Slide Title", "content": "Slide content text"}

# CSV operations
{"type": "append_row", "values": ["col1", "col2", "col3"]}
{"type": "set_cell", "row": 2, "col": 1, "value": "New Value"}

# Text file operations
{"type": "replace_content", "text": "Entirely new content"}
{"type": "append_text", "text": "\nAppended text"}
```

**Implementation details:**
- Operations are passed as JSON strings in the tool parameter
- Can pass single operation object or array of operations
- `document_writer.py` handles all write operations
- Uses python-docx, openpyxl, python-pptx libraries
- Files are created if they don't exist (except for some operations)
- Returns success/error status and count of operations applied

### Python Script Generation for Complex Document Operations

**IMPORTANT**: Local Ollama models often struggle with complex multi-step document workflows. To solve this, the tool provides two distinct tools with clear separation of concerns:

**Two-Tool Approach:**

1. **`write_document`** - For SIMPLE tasks only (1-5 operations, single file)
   - Append one paragraph to Word doc
   - Update 2-3 cells in Excel
   - Single-file edits with few operations

2. **`generate_automation_script`** - For COMPLEX tasks (the tool models should prefer for complex work)
   - Multiple source/destination files
   - Data parsing and matching (Excel → Word lookups)
   - 10+ individual operations required
   - Data extraction/transformation logic
   - Cross-file data transfers or synchronization
   - Conditional operations based on document content

**How `generate_automation_script` works:**

Models call this tool with:
- `task_description`: Brief explanation of what the script will do
- `script_code`: Complete Python code importing from `slice_tool.document_reader` and `slice_tool.document_writer`

The tool automatically:
1. Saves the script to `automation_script.py` in the **current working directory** (where slice was started)
2. Executes it with user permission in the same directory
3. Returns the results to the model

**CRITICAL**: All scripts and file operations happen in the directory where slice tool is running. Never use absolute paths or home directory paths (`~/`, `/Users/`, etc.) - just use filenames.

**Why this two-tool approach works:**

✅ **Clear separation**: Models see two distinct tools instead of one tool with a paragraph of guidance buried in the description

✅ **Forced choice**: Having separate tools makes models actively choose the right path

✅ **Better prompting**: Tool descriptions use ✅ CORRECT vs ❌ WRONG examples to guide behavior

✅ **Automatic execution**: The script tool handles save + execute, so models don't have to orchestrate multiple steps

**Example script structure:**
```python
from slice_tool.document_reader import read_document
from slice_tool.document_writer import write_document

# Read source data
excel_data = read_document("source.xlsx")
# Parse and process data...

# Write to destination
result = write_document("destination.docx", [
    {"type": "replace_text", "find": "X", "replace": "Y"},
    # ... many more operations
])
```

**For XML fallback mode (models without tool support):**
The system message explicitly instructs models to generate Python scripts for complex tasks using the `<write>` tag to save the script, then `<action>` to execute it.

### Command Execution Safety
All commands execute through `CommandExecutor` which provides multiple layers of protection:

**1. Directory Sandboxing**
- Commands are restricted to the directory where `slice` was started
- Detects attempts to access paths outside the sandbox:
  - Absolute paths (`/tmp/file`)
  - Home directory (`~/Documents/file`)
  - Parent directory traversal (`../../../file`)
  - Directory changes (`cd /tmp`)
- Shows red warning for sandbox escapes and requires explicit "yes" confirmation
- Displays all suspicious paths found in the command

**2. Permission Prompts**
- Shows the command in a syntax-highlighted panel
- Explains the reason (context from model)
- Normal commands: asks y/N permission
- Dangerous/escaped commands: requires explicit "yes" confirmation with red warning

**3. Dangerous Pattern Detection**
- Checks for obviously dangerous patterns (rm -rf /, mkfs, dd, etc.)
- Shows red border and requires explicit "yes" for dangerous commands

**4. Execution Safety**
- 30-second timeout to prevent runaway commands
- Captures stdout/stderr and displays formatted results
- Shows clear success/failure status

**5. Local-First Command Strategy**
- Model is guided to start with simple commands in the CURRENT directory first
- Should use `ls` before `ls -R`, and `ls` before `find`
- Only search subdirectories if files aren't found locally
- This prevents the model from being overly aggressive with recursive searches
- Tool descriptions in both tool-calling and XML modes enforce this behavior

**6. Direct File Access (No Verification)**
- When user mentions a specific filename, model should try to read it directly
- DO NOT run `ls` or `find` commands to verify file existence first
- Assume files user mentions are in the current directory
- The `read_document` tool handles file-not-found errors gracefully
- Only use `ls` when user explicitly asks to list/see files, not for verification
- This prevents unnecessary command execution and speeds up file operations

**7. Anti-Loop Safeguards**
To prevent the model from getting stuck in repetitive loops:
- **No duplicate tool calls**: Model must NOT call the same tool with the same parameters twice in one turn
- **No re-reading**: Once a file is read, its content is in conversation history - don't read it again
- **No hallucinated files**: Model must ONLY read files explicitly mentioned by the user
- **Excel files return all data**: Excel/CSV reads return complete content - no need to re-read for different sheets
- **One action per file**: Read each document once, use each command once per turn
- Tool descriptions explicitly forbid repetition and hallucination

**Runtime Enforcement:**
- `SliceAgent` tracks `files_read_this_turn` and `commands_run_this_turn` sets
- Both sets are cleared at the start of each user turn
- Tool handlers check these sets and REJECT duplicate operations before execution
- Blocked duplicates return clear error messages to the model ("REJECTED: You already read X")
- Applies to both tool-calling mode and XML fallback mode
- User sees red warning when duplicates are blocked: "⚠️  Blocked duplicate file read: X"

**Natural File Error Handling:**
- File reads that reference non-existent files are NOT blocked or rejected
- The `read_document` function naturally returns a "File not found" error
- This error is passed to the model in conversation history
- Model should handle file-not-found errors gracefully and continue with its task
- No user prompts or warnings are shown for hallucinated files
- This prevents the model from getting stuck trying to find files that don't exist
- The model learns from the error and should focus on files that do exist

## Model Switching with /model Command

The `/model` command allows users to switch models mid-session without restarting the application.

**How it works:**
1. User types `/model` at the prompt
2. Model selector displays list of available models
3. User selects a new model with arrow keys
4. New `SliceAgent` instance is created with the selected model
5. **Conversation history is preserved** and transferred to the new tool
6. Sandbox directory remains the same

**Implementation details:**
- The `ChatUI` class holds a reference to `safe_directory` to pass to new tools
- Conversation history is copied from the old tool to the new tool via `tool.conversation_history`
- Lazy import of `SliceAgent` in `ui.py._switch_model()` to avoid circular dependencies
- If user cancels model selection, current model is kept

**Why preserve conversation history:**
Users may want to switch models to:
- Get a different perspective on the same problem
- Use a faster/smaller model for simple tasks
- Use a more capable model for complex reasoning

Preserving history allows seamless continuation of the conversation with context intact.

## Testing Local Ollama Models

Ensure Ollama is running:
```bash
ollama list  # Should show downloaded models
```

If no models exist:
```bash
ollama pull llama2
# or
ollama pull mistral
```

## Common Pitfalls

- **Don't break the exit handler**: The double-Ctrl+C pattern in `main.py` must work everywhere
- **Don't suppress chat**: Permission gates are for **actions only**, not responses
- **Conversation history**: Maintained in `tool.py`, don't duplicate in UI layer
- **Spinner cleanup**: Use Rich's `transient=True` so spinners disappear after response
