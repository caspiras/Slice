# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Slice** is a local-first IDE wrapper for Ollama models. Built entirely in **Python**, it provides a beautiful terminal interface with permission-gated command execution, code editing with diffs, and comprehensive document operations.

## Architecture

**Pure Python** implementation using:
- **Rich** - Terminal UI with panels, spinners, syntax highlighting
- **Ollama Python SDK** - Direct API integration for streaming chat and tool calling
- **prompt-toolkit** - Interactive prompts with command history
- Document libraries - pypdf, python-docx, openpyxl, python-pptx

### Core Components

1. **main.py** - CLI entry point, signal handling (double Ctrl+C to exit), startup banner
2. **ui.py** - ModelSelector (arrow-key selection) and ChatUI (prompt interface)
3. **chat.py** - ChatSession class, Ollama API integration, tool definitions and execution
4. **executor.py** - CommandExecutor class for sandboxed bash execution with permission prompts
5. **document_reader.py** - Read PDF, Word, Excel, PowerPoint, CSV, text files
6. **document_writer.py** - Write Word, Excel, PowerPoint, CSV, text files with operations

### Project Structure

```
slice_agent/
├── src/slice/
│   ├── main.py              # Entry point & signal handling
│   ├── ui.py                # ModelSelector & ChatUI (Rich + prompt-toolkit)
│   ├── chat.py              # ChatSession with Ollama integration (~629 lines)
│   ├── executor.py          # CommandExecutor for sandboxed bash (~234 lines)
│   ├── document_reader.py   # Multi-format document reading (~222 lines)
│   └── document_writer.py   # Multi-format document writing (~442 lines)
├── pyproject.toml           # Python package config (v1.1.0)
└── README.md                # User documentation
```

## Development Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run Slice
slice

# Format code (line-length 100, target py39)
black src/

# Lint code (line-length 100, target py39)
ruff check src/

# Note: Tests directory doesn't exist yet - pytest infrastructure is configured but tests not yet written
```

## Key Architecture Principles

### 1. Permission-Gated Actions

**Core principle:** Always ask permission before executing actions.

- **Chat responses** flow naturally without interruption
- **Tool calls** (bash, edit_code, write_document) trigger permission prompts
- User sees the command/operation and context before approval
- Never execute actions silently

### 2. Tool-Based Model Interaction

Slice uses Ollama's function/tool calling feature. Models that support tools receive 4 tool definitions:

**Available Tools:**
1. **bash** - Execute shell commands (file operations, git, search, etc.)
2. **read_document** - Read PDF, Word (.docx), Excel (.xlsx), CSV, text files
3. **write_document** - Write Word, Excel, PowerPoint, PDF, CSV, text with JSON operations
4. **edit_code** - Edit source code files with diff preview and approval

**Tool-capable models:** llama3.x, mistral, gemma, gemma2, gemma4, command-r, qwen, qwen2

**How it works:**
- Model decides when to call tools based on user request
- ChatSession receives tool calls from Ollama API
- Tool handlers execute with user permission
- Results fed back to model for final response

### 3. Directory Sandboxing

All operations are restricted to the directory where `slice` was started.

**CommandExecutor detects sandbox escapes:**
- Absolute paths (`/tmp/file`)
- Home directory (`~/Documents/file`)
- Parent traversal (`../../../file`)
- Directory changes (`cd /tmp`)

**Protection layers:**
- Red warning panel for sandbox escapes
- Requires explicit "yes" confirmation (not just "y")
- Shows all suspicious paths found in command
- 30-second timeout on all commands

### 4. Signal Handling (Ctrl+C)

**Double-press to exit pattern:**
- First Ctrl+C: Warning message, increments `exit_count`
- Second Ctrl+C: Actual exit
- Applies during prompt input and model streaming
- Set up in `main.py`, must not be overridden

### 5. UI/UX Requirements

**Visual identity:**
- **Prompt cursor:** 🍕 (pizza emoji)
- **Thinking indicator:** "baking..." with spinner
- **Streaming responses:** Word-by-word token display
- **Model selection:** Arrow-key navigation with tool support indicators `[tools ✓]`
- **Model switching:** `/model` command preserves conversation history

**Implementation details:**
- Rich Live displays for spinners (use `transient=True` for cleanup)
- Syntax-highlighted diffs for code edits
- Panel displays for commands and outputs
- FileHistory for command history (up/down arrows)

## Tool Execution Flow

### Bash Tool
```python
# In chat.py, ChatSession._execute_command()
1. Model calls bash tool with command string
2. ChatSession passes to CommandExecutor.execute_with_permission()
3. CommandExecutor shows permission prompt with context
4. User approves/denies
5. If approved: subprocess runs with 30s timeout in safe_directory
6. Result returned to model
```

### Read Document Tool
```python
# In chat.py, ChatSession._read_document()
1. Model calls read_document with file_path
2. Imports from document_reader module
3. read_document() detects file type by extension
4. Appropriate reader (pypdf, python-docx, openpyxl, etc.)
5. Returns formatted text content to model
```

### Write Document Tool
```python
# In chat.py, ChatSession._write_document()
1. Model calls write_document with file_path and operations JSON
2. Operations parsed (single object or array)
3. Imports from document_writer module
4. write_document() applies operations sequentially
5. Returns success/failure count to model
```

### Edit Code Tool
```python
# In chat.py, ChatSession._edit_code()
1. Model calls edit_code with file_path, old_content, new_content, description
2. Read original file content
3. Check if old_content exists exactly
4. Generate unified diff with difflib
5. Show syntax-highlighted diff in panel
6. Ask user for approval
7. If approved: write new content
8. Return result to model
```

## Document Operations

### Supported Read Formats
- **PDF (.pdf)** - Extract text from all pages (pypdf)
- **Word (.docx)** - Read paragraphs and tables (python-docx)
- **Excel (.xlsx)** - Read all sheets with row/column data (openpyxl)
- **CSV (.csv)** - Read all rows with row numbers
- **Text files** - Any text-based file with encoding detection

### Supported Write Formats
- **Word (.docx)** - append_paragraph, replace_text, insert_after
- **Excel (.xlsx)** - set_cell, append_row, set_column
- **PowerPoint (.pptx)** - add_slide
- **PDF (.pdf)** - add_page, add_paragraph, add_text
- **CSV (.csv)** - append_row, set_cell
- **Text files** - replace_content, append_text

### Operation Examples

```python
# Word operations
{"type": "append_paragraph", "text": "New paragraph"}
{"type": "replace_text", "find": "old", "replace": "new"}
{"type": "insert_after", "search": "Header", "text": "Content"}

# Excel operations
{"type": "set_cell", "sheet": "Sheet1", "row": 5, "col": "M", "value": "Data"}
{"type": "append_row", "sheet": "Sheet1", "values": ["A", "B", "C"]}
{"type": "set_column", "sheet": "Sheet1", "col": "M", "start_row": 3, "values": ["X", "Y"]}

# PowerPoint operations
{"type": "add_slide", "title": "Title", "content": "Content"}

# PDF operations
{"type": "add_page", "title": "Page Title", "content": "Page content"}
{"type": "add_paragraph", "text": "Paragraph text", "font_size": 12}
{"type": "add_text", "text": "Text content", "font_size": 14}

# CSV operations
{"type": "append_row", "values": ["col1", "col2", "col3"]}
{"type": "set_cell", "row": 2, "col": 1, "value": "Value"}

# Text file operations
{"type": "replace_content", "text": "Entirely new content"}
{"type": "append_text", "text": "\nAppended text"}
```

## Model Switching with /model

**How it works:**
1. User types `/model` at the 🍕 prompt
2. ModelSelector displays available models with arrow-key navigation
3. User selects new model
4. New ChatSession created with selected model
5. **Conversation history preserved** via `session.conversation_history`
6. Sandbox directory remains the same

**Implementation:**
- ChatUI holds reference to `safe_directory`
- On model switch: `new_session = ChatSession(new_model, safe_directory)`
- Copy history: `new_session.conversation_history = old_session.conversation_history`
- Lazy import of ChatSession in `ui.py._switch_model()` avoids circular dependencies

## System Message Guidelines

The system message in `chat.py` guides model behavior:

**Tool usage rules:**
- Use bash for file/system operations, NOT for echoing knowledge answers
- Use read_document directly without ls/find verification first
- Use edit_code for source code with diff workflow
- Use write_document for ALL document types (Word, Excel, PowerPoint, PDF, CSV, text)

**Spreadsheet editing workflow (CRITICAL for model success):**
1. **Always read first** - Use read_document to see current structure
2. **Identify changes** - Determine which rows, columns, cells need updating
3. **Use JSON operations** - Pass structured operations to write_document
4. **Common patterns:**
   - Set cell: `{"type": "set_cell", "sheet": "Sheet1", "row": 2, "col": "A", "value": "Data"}`
   - Add row: `{"type": "append_row", "sheet": "Sheet1", "values": ["col1", "col2"]}`
   - Fill column: `{"type": "set_column", "sheet": "Sheet1", "col": "B", "start_row": 2, "values": [10, 20]}`
5. **CSV files** - Same operations but omit "sheet" parameter
6. **Multiple operations** - Combine in array: `[{...}, {...}]`
7. **Column references** - Use letters ("A", "M") or numbers (1, 13)
8. **Row indexing** - 1-indexed (row 1 is first row)

**PDF editing workflow:**
- PDFs can be created and edited with write_document tool
- Common operations: add_page, add_paragraph, add_text
- Use read_document to read existing PDFs
- PDFs are built sequentially - operations applied in order
- Example: `{"type": "add_page", "title": "Report", "content": "Summary text"}`

**Git operation rules:**
- Read-only: safe to suggest (status, log, diff, show, branch)
- Local: safe to suggest (add, commit, checkout -b, merge)
- Remote: **NEVER suggest push/pull unless user explicitly asks**
- After commits, remind user they can push when ready

**File operation rules:**
- When user mentions filename, read directly - don't verify existence first
- Use bash `touch filename` for empty text files only
- **Never** use touch for document files (Excel, Word, PowerPoint, PDF) - they need proper structure
- To create new document files, use write_document with operations (it will create the file)
- Multi-file search: bash with grep -r or find

## Testing Local Ollama Models

Ensure Ollama is running:
```bash
ollama list  # Should show downloaded models
```

Download models:
```bash
# Recommended for balanced chat/action behavior
ollama pull gemma4
ollama pull mistral
ollama pull qwen2

# Good for code-heavy tasks
ollama pull llama3.1
```

## Common Pitfalls

1. **Don't break signal handling**
   - The double-Ctrl+C pattern in `main.py` must work everywhere
   - Don't override the signal handler in other modules

2. **Don't suppress chat flow**
   - Permission prompts are for **actions only** (bash, edit_code, write_document)
   - Chat responses must stream naturally without interruption
   - Never prompt for permission on read_document

3. **Conversation history**
   - Maintained in `ChatSession.conversation_history`
   - Don't duplicate in UI layer
   - Preserved when switching models

4. **Spinner cleanup**
   - Use Rich `Live` with `transient=True`
   - Spinners must disappear after response completes
   - "baking..." spinner shows during model thinking

5. **Sandbox escapes**
   - Always use `safe_directory` for command execution
   - Never bypass sandbox checks
   - Show red warnings for attempts to escape

6. **Model behavior differences**
   - llama3.x models may try to use bash for knowledge questions
   - gemma4, mistral, qwen2 better at distinguishing chat vs. actions
   - Tool support auto-detected, but some models hallucinate unsupported tools

7. **Spreadsheet operation confusion (common with smaller models)**
   - Models struggle if they don't read the file first
   - JSON operations must be valid and properly escaped
   - Column references can be letters OR numbers - both work
   - For CSV, omit the "sheet" parameter entirely
   - The tool description now includes concrete examples to guide models
   - System message includes step-by-step workflow for spreadsheet editing

## Key Dependencies

```toml
# Core dependencies (from pyproject.toml)
rich>=13.0.0              # Terminal UI
ollama>=0.1.0             # Ollama API client
prompt-toolkit>=3.0.0     # Interactive prompts
pypdf>=4.0.0              # PDF reading
reportlab>=4.0.0          # PDF writing
python-docx>=1.0.0        # Word documents
openpyxl>=3.0.0           # Excel spreadsheets
python-pptx>=0.6.0        # PowerPoint presentations

# Dev dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0             # Formatter (line-length 100)
ruff>=0.1.0               # Linter (line-length 100)
```

## Version History

- **v1.2.0** - Current version, full document editing support
  - Added PDF writing capability (reportlab)
  - ALL document types now editable (PDF, Word, Excel, PowerPoint, CSV, text)
  - Enhanced spreadsheet operation guidance for better model success
  - Removed read-only PDF restriction
  
- **v1.1.0** - Pure Python architecture
  - Removed Go hybrid architecture
  - Added code editing with diffs (edit_code tool)
  - Improved model switching with history preservation
  - Enhanced terminal UI with Rich
  
- **v1.0.x** - Initial release with Go + Python hybrid
  - Removed in commit 047c7a6
