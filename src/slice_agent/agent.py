"""Agent logic for slice-agent with permission-gated actions."""

import re
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from .executor import CommandExecutor
from .document_reader import read_document
from .document_writer import write_document

console = Console()


# Tool definitions for Ollama
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute shell commands. CRITICAL RULES: (1) DO NOT run the same command twice in one conversation turn. (2) When user mentions a filename, DO NOT run 'ls' or 'find' - just use read_document directly. (3) Only call this when user asks to CREATE, DELETE, or MODIFY files, or check git status. (4) For reading/viewing files, use read_document instead. (5) If you already have information from a previous tool call, DO NOT repeat it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to run. DO NOT repeat commands you already ran. Examples: 'touch file.txt', 'git status', 'mkdir folder'"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you need to run this command. Must be a NEW reason, not something you already did."
                    }
                },
                "required": ["command", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Read documents (PDF, Word, Excel, CSV, text). CRITICAL RULES: (1) DO NOT read the same file twice in one turn. (2) When user mentions a filename, read it directly without running 'ls' or 'find' first. (3) If you already read a file and have its content, DO NOT read it again. (4) For Excel files, you get ALL the data at once - don't re-read for different sheets. (5) If a file doesn't exist, you'll get an error - handle it gracefully and continue with the files that do exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Filename to read. Use exact filename user mentioned. DO NOT read files you already read. Use current directory unless specified otherwise. If file doesn't exist, error will be returned."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_document",
            "description": "Write/modify documents for SIMPLE operations only. Use for single-file edits with 1-5 operations. Supports: Word (.docx) - append/replace text; Excel (.xlsx) - set cells, append rows; PowerPoint (.pptx) - add slides; CSV - modify data; Text files. PDF files CANNOT be edited.\n\n✅ CORRECT usage (simple tasks):\n- Append one paragraph to a Word doc\n- Update 3-4 cells in Excel\n- Add a slide to PowerPoint\n\n❌ WRONG - DO NOT use for complex tasks:\n- Multiple source/destination files\n- Excel→Word data transfers with matching\n- 10+ operations or loops\n- Data parsing/extraction/transformation\n\n→ For complex tasks, use generate_automation_script instead!\n\nOperations format: JSON string with 'type' field. Examples: {\"type\":\"append_paragraph\",\"text\":\"New text\"} or {\"type\":\"set_cell\",\"sheet\":\"Sheet1\",\"row\":5,\"col\":\"M\",\"value\":\"Data\"}",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document to write/modify. Use exact filename user mentioned."
                    },
                    "operations": {
                        "type": "string",
                        "description": "JSON string containing operation(s) to perform. Can be single object or array of objects. Each must have 'type' field. Word: append_paragraph, replace_text. Excel: set_cell, append_row, set_column. PowerPoint: add_slide. CSV: append_row, set_cell. Text: replace_content, append_text."
                    }
                },
                "required": ["file_path", "operations"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_automation_script",
            "description": "Generate and execute Python automation script for COMPLEX document operations. Use this when task involves multiple files, data matching, Excel→Word transfers, parsing/extraction, or 10+ operations.\n\n✅ CORRECT usage (complex tasks):\n- Read Excel column G, update Word doc tables with matching data\n- Extract data from multiple PDFs and consolidate to Excel\n- Compare two Word docs and generate diff report\n- Process 50+ rows of data with conditional logic\n\n❌ WRONG - use write_document instead:\n- Simple single-file edits\n- Appending one paragraph\n- Updating 2-3 cells\n\nThe script will be automatically saved to 'automation_script.py' and executed. You provide the full Python code.\n\nAVAILABLE FUNCTIONS IN YOUR SCRIPT:\n\n1. read_document(file_path: str) -> dict\n   Returns: {'success': bool, 'content': str, 'error': str, 'file_type': str}\n   The 'content' is the full text/data from the file as a string.\n   For Excel: content shows all sheets with row data like 'Row 1: col1 | col2 | col3'\n\n2. write_document(file_path: str, operations: list or dict) -> dict\n   Returns: {'success': bool, 'message': str, 'error': str, 'operations_applied': int}\n   Operations: [{'type': 'replace_text', 'find': 'X', 'replace': 'Y'}, ...]\n\nDO NOT hallucinate other function names or classes. ONLY use read_document() and write_document().",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Brief description of what the script will accomplish (for user visibility)."
                    },
                    "script_code": {
                        "type": "string",
                        "description": "Complete Python script code. CRITICAL: Use ONLY these functions:\n\nfrom slice_agent.document_reader import read_document\nfrom slice_agent.document_writer import write_document\n\n# Read file (returns dict with 'success', 'content', 'error' keys)\nexcel_result = read_document('file.xlsx')\nif excel_result['success']:\n    data = excel_result['content']  # This is a STRING with all the data\n    # Parse the string to extract what you need\n    # For Excel, content format: 'Row 1: val1 | val2 | val3\\nRow 2: ...'\n\n# Write file (takes file path and operations list/dict)\nwrite_result = write_document('file.docx', [\n    {'type': 'replace_text', 'find': 'old', 'replace': 'new'}\n])\n\nDO NOT import DocumentReader, DocumentWriter classes - they don't exist!\nDO NOT use read_doc(), read_xlsx() methods - they don't exist!"
                    }
                },
                "required": ["task_description", "script_code"]
            }
        }
    }
]


class SliceAgent:
    """
    Agent that can chat and execute actions with user permission.

    The agent maintains the chatbot personality while identifying action requests
    and asking for permission before executing commands.
    """

    def __init__(self, model: str, safe_directory: str = None):
        self.model = model
        self.conversation_history = []
        self.executor = CommandExecutor(safe_directory=safe_directory)
        self.supports_tools = self._check_tool_support()
        # Track files read in current turn to prevent duplicates and hallucinations
        self.files_read_this_turn = set()
        self.commands_run_this_turn = set()
        # Track completion forcing to prevent infinite loops
        self.completion_forced_this_turn = False
        # Track failed writes to prevent running commands on non-existent files
        self.failed_writes_this_turn = set()

        # If model doesn't support tools, add system message for XML fallback
        if not self.supports_tools:
            self.conversation_history.append({
                "role": "system",
                "content": (
                    "You are an AI assistant that takes ACTION using XML tags. DO NOT just explain - USE THE TAGS!\n\n"
                    "YOUR TOOLS (use these, don't just describe them):\n"
                    "1. <action command='...'>reason</action> - for shell commands (git status, etc.)\n"
                    "2. <read file='...'/> - for reading documents (PDF, Word, Excel, CSV, text files)\n"
                    "3. <write file='...' operations='...' /> - for SIMPLE document edits (1-5 operations, single file)\n\n"
                    "CRITICAL RULES TO PREVENT LOOPS:\n"
                    "- DO NOT use the same XML tag twice in one response\n"
                    "- DO NOT read the same file multiple times\n"
                    "- DO NOT run the same command multiple times\n"
                    "- When user mentions a filename, read it directly - DO NOT use 'ls' or 'find' first\n"
                    "- If you already have file content, DO NOT re-read it\n"
                    "- If a file read fails (file not found), handle the error gracefully and continue\n\n"
                    "✅ SIMPLE TASKS - Use <write> tag:\n"
                    "- Append one paragraph to Word doc\n"
                    "- Update 2-3 cells in Excel\n"
                    "- Single-file edits with few operations\n"
                    "Example: <write file='doc.docx' operations='{\"type\":\"append_paragraph\",\"text\":\"New text\"}'/>\n\n"
                    "❌ COMPLEX TASKS - YOU MUST Generate Python Script:\n"
                    "When task involves: multiple files, data matching, Excel→Word transfers, 10+ operations, parsing/extraction\n"
                    "DO NOT just say 'here is the script' - ACTUALLY GENERATE IT using the XML tags below!\n\n"
                    "AVAILABLE FUNCTIONS FOR YOUR SCRIPT:\n"
                    "1. read_document(file_path: str) -> dict with keys: 'success', 'content', 'error', 'file_type'\n"
                    "   The 'content' is a STRING with the file data. For Excel: 'Row 1: val | val | val\\nRow 2: ...'\n"
                    "2. write_document(file_path: str, operations: list/dict) -> dict\n"
                    "   Operations: [{'type': 'replace_text', 'find': 'X', 'replace': 'Y'}, ...]\n\n"
                    "SCRIPT WRITING TIPS TO AVOID JSON ESCAPING ISSUES:\n"
                    "- Keep Python code SIMPLE - avoid deeply nested dicts/lists inside the script\n"
                    "- Use simple string formatting instead of f-strings with complex expressions\n"
                    "- Build operations list step-by-step instead of nested dict comprehensions\n"
                    "- If you can't generate valid compact JSON, break task into smaller write operations\n\n"
                    "DO THIS PATTERN:\n"
                    "1. Write script using ONLY: from slice_agent.document_reader import read_document\n"
                    "                             from slice_agent.document_writer import write_document\n"
                    "   DO NOT hallucinate DocumentReader/DocumentWriter classes!\n\n"
                    "2. Save script - USE COMPACT JSON ON ONE LINE:\n"
                    "   ✅ CORRECT (everything on one line, \\n for newlines):\n"
                    "   <write file='automation_script.py' operations='{\"type\":\"replace_content\",\"text\":\"import x\\nimport y\\n\"}'/>\n\n"
                    "   ❌ WRONG (prettified with literal newlines - THIS WILL FAIL):\n"
                    "   <write file='automation_script.py' operations='\n"
                    "   {\n"
                    "       \"type\": \"replace_content\",\n"
                    "       \"text\": \"\n"
                    "   import x\n"
                    "   '\n"
                    "   DO NOT DO THIS ^^^ - no pretty formatting, no actual newlines in JSON structure!\n\n"
                    "3. Execute: <action command='python3 automation_script.py'>Running automation for [task]</action>\n\n"
                    "COMPLETE EXAMPLE for Excel→Word task:\n"
                    "<write file='automation_script.py' operations='{\"type\":\"replace_content\",\"text\":\"from slice_agent.document_reader import read_document\\nfrom slice_agent.document_writer import write_document\\n\\nexcel_result = read_document(\\\"data.xlsx\\\")\\nif excel_result[\\\"success\\\"]:\\n    excel_content = excel_result[\\\"content\\\"]\\n    # Parse Excel content and extract data\\n    # ... your parsing logic ...\\n    # Generate operations list\\n    operations = [{\\\"type\\\":\\\"replace_text\\\", \\\"find\\\":\\\"X\\\", \\\"replace\\\":\\\"Y\\\"}]\\n    write_document(\\\"output.docx\\\", operations)\"}'/>\n"
                    "<action command='python3 automation_script.py'>Running Excel to Word automation</action>\n\n"
                    "Remember: ACTUALLY USE THE XML TAGS - don't just say what you would do!"
                )
            })

    def _check_tool_support(self) -> bool:
        """
        Check if the model supports tool/function calling.

        Returns True if the model likely supports tools, False otherwise.
        """
        # Known models with good tool support in Ollama
        # Note: mixtral does NOT support tools in Ollama (returns 400 error)
        tool_capable_models = [
            "llama3", "llama3.1", "llama3.2", "llama3.3",
            "mistral",  # mistral base models support tools, mixtral does not
            "gemma", "gemma2", "gemma4",
            "command-r", "command-r-plus",
            "qwen", "qwen2",
        ]

        model_lower = self.model.lower()
        return any(capable in model_lower for capable in tool_capable_models)

    def process_stream(self, user_input: str):
        """
        Process user input and yield response tokens as they arrive.

        Yields:
            Tokens of the response as strings
        """
        # Reset per-turn tracking
        self.files_read_this_turn.clear()
        self.commands_run_this_turn.clear()
        self.failed_writes_this_turn.clear()
        self.completion_forced_this_turn = False

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        try:
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": self.conversation_history,
                "stream": True
            }

            # Add tools if supported
            if self.supports_tools:
                request_params["tools"] = TOOLS

            # Stream response from Ollama
            full_message = ""
            has_tool_calls = False

            for chunk in ollama.chat(**request_params):
                message = chunk.message

                # Check if this chunk has tool calls
                if self.supports_tools and message.tool_calls:
                    has_tool_calls = True
                    # Stop streaming, handle tool call non-streaming
                    # Need to get full response first
                    break

                # Get content delta
                content = message.content or ""
                if content:
                    full_message += content
                    yield content

            # If tool calls detected, handle them (non-streaming)
            if has_tool_calls:
                # Signal to UI to exit Live display before showing permission prompts
                yield "__TOOL_CALL_START__"

                # Re-fetch without streaming to get complete tool call info
                response = ollama.chat(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=TOOLS
                )
                result = self._handle_tool_calls(response.message)
                yield result
                return

            # For tool-capable models: detect if they described a task but didn't call tools
            if self.supports_tools and full_message and not self.completion_forced_this_turn:
                incomplete_indicators = [
                    "here's the script", "here is the script",
                    "generated python script", "generated script",
                    "i'll generate", "i will generate",
                    "automation script", "here's how",
                ]
                message_lower = full_message.lower()
                if any(indicator in message_lower for indicator in incomplete_indicators):
                    console.print(f"\n[yellow]⚠️  Model described the task but didn't call tools[/yellow]")
                    console.print(f"[yellow]    Forcing tool use (one attempt)...[/yellow]\n")

                    # Mark that we've forced completion
                    self.completion_forced_this_turn = True

                    # Add message to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_message
                    })

                    # Force tool use with follow-up
                    self.conversation_history.append({
                        "role": "user",
                        "content": "Please actually call the generate_automation_script tool now with the complete Python code. Don't explain - just make the tool call."
                    })

                    # Recursively call to get actual tool use
                    for token in self.process_stream(""):
                        yield token
                    return

            # Check for XML tags if no tool support
            if not self.supports_tools:
                has_xml = ("<action" in full_message or "<read" in full_message or "<write" in full_message)

                # Detect incomplete response: mentions script/automation but no XML tags
                incomplete_response = False
                if not has_xml and not self.completion_forced_this_turn:
                    incomplete_indicators = [
                        "here's the script", "here is the script",
                        "generated python script", "generated script",
                        "i'll generate", "i will generate",
                        "automation script", "here's how",
                    ]
                    message_lower = full_message.lower()
                    if any(indicator in message_lower for indicator in incomplete_indicators):
                        # Model is talking about generating but didn't actually do it
                        incomplete_response = True
                        self.completion_forced_this_turn = True
                        console.print(f"\n[yellow]⚠️  Model described the task but didn't generate XML tags[/yellow]")
                        console.print(f"[yellow]    Forcing completion (one attempt)...[/yellow]\n")

                if has_xml:
                    # Signal to UI that we're processing XML actions
                    yield "__TOOL_CALL_START__"

                    # Process XML actions with visual feedback
                    full_message = self._handle_xml_actions(full_message)

                    # Yield the processed message
                    yield full_message

                    # Add to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_message
                    })
                    return
                elif incomplete_response:
                    # Add incomplete response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_message
                    })

                    # Force completion with follow-up
                    self.conversation_history.append({
                        "role": "user",
                        "content": "Please actually generate the XML tags now. Don't explain - just output the <write> and <action> tags with the complete script."
                    })

                    # Recursively call to get the actual tags
                    for token in self.process_stream(""):  # Empty string since we just added the prompt
                        yield token
                    return

            # Add assistant response to history (no XML actions)
            self.conversation_history.append({
                "role": "assistant",
                "content": full_message
            })

        except KeyboardInterrupt:
            # Let KeyboardInterrupt propagate up
            raise
        except Exception as e:
            error_msg = f"Error communicating with model: {e}"
            console.print(f"[red]{error_msg}[/red]")
            yield error_msg

    def process(self, user_input: str) -> str:
        """
        Process user input and return response (non-streaming).

        Handles both chat and action requests. For actions, asks user permission
        before executing.
        """
        # Use streaming and collect all tokens
        return "".join(self.process_stream(user_input))

    def _handle_tool_calls(self, message) -> str:
        """Handle tool calls from the model, including multiple sequential calls."""
        max_iterations = 10  # Prevent infinite loops
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            # Check if message has tool calls
            if not message.tool_calls:
                # No more tool calls, return the text content
                content = message.content or ""
                # If content is empty after tool calls, provide a default message
                if not content.strip() and iterations > 1:
                    content = "Done."
                self.conversation_history.append({
                    "role": "assistant",
                    "content": content
                })
                return content

            tool_calls = message.tool_calls

            # Add assistant message with tool calls to history (as dict)
            self.conversation_history.append(dict(message))

            # Process each tool call
            user_cancelled = False
            for tool_call in tool_calls:
                function = tool_call.get("function", {}) if isinstance(tool_call, dict) else tool_call.function
                function_name = function.get("name") if isinstance(function, dict) else function.name
                arguments = function.get("arguments", {}) if isinstance(function, dict) else function.arguments

                if function_name == "execute_command":
                    command = arguments.get("command", "") if isinstance(arguments, dict) else getattr(arguments, "command", "")
                    reason = arguments.get("reason", "") if isinstance(arguments, dict) else getattr(arguments, "reason", "")

                    # Validate command is not empty
                    if not command or not command.strip():
                        # Model called tool with empty command - tell it to answer normally
                        invalid_call_msg = "Invalid tool call - no command provided. Please answer the user's question directly from your knowledge without using tools."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": invalid_call_msg
                        })
                        continue  # Skip to next tool call

                    # Check if command was already run this turn
                    if command in self.commands_run_this_turn:
                        # Silently reject duplicate - model gets feedback but user doesn't see warning
                        duplicate_msg = f"REJECTED: You already ran this command in this turn: '{command}'. DO NOT repeat commands. Use the result from the previous execution."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": duplicate_msg
                        })
                        continue

                    # Check if command references a file that failed to write
                    for failed_file in self.failed_writes_this_turn:
                        if failed_file in command:
                            console.print(f"[red]⚠️  Skipping command - file '{failed_file}' failed to write[/red]\n")
                            skip_msg = f"SKIPPED: Cannot execute command because '{failed_file}' failed to write. Fix the write operation first before trying to run commands that use this file."
                            self.conversation_history.append({
                                "role": "tool",
                                "content": skip_msg
                            })
                            continue

                    # Track this command
                    self.commands_run_this_turn.add(command)

                    try:
                        # Execute with permission
                        result = self.executor.execute_with_permission(command, reason)

                        # Check if user cancelled
                        if result.get("cancelled", False):
                            user_cancelled = True
                            # Don't add to history, just break out
                            break

                        # Add tool result to history
                        self.conversation_history.append({
                            "role": "tool",
                            "content": str(result)
                        })
                    except KeyboardInterrupt:
                        # User pressed Ctrl+C during permission prompt
                        user_cancelled = True
                        break

                elif function_name == "read_document":
                    file_path = arguments.get("file_path", "") if isinstance(arguments, dict) else getattr(arguments, "file_path", "")

                    # Validate file_path is not empty
                    if not file_path or not file_path.strip():
                        invalid_call_msg = "Invalid tool call - no file path provided."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": invalid_call_msg
                        })
                        continue

                    # Check if file was already read this turn
                    if file_path in self.files_read_this_turn:
                        # Silently reject duplicate - model gets feedback but user doesn't see warning
                        duplicate_msg = f"REJECTED: You already read '{file_path}' in this turn. The content is already in the conversation history. DO NOT re-read files."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": duplicate_msg
                        })
                        continue

                    # Track this file
                    self.files_read_this_turn.add(file_path)

                    try:
                        # Read the document with spinner (only show for successful reads)
                        with Live(
                            Spinner("dots", text="[yellow]reading...[/yellow]"),
                            console=console,
                            auto_refresh=True,
                            refresh_per_second=10,
                            transient=True
                        ):
                            result = read_document(file_path)

                        if result["success"]:
                            # Only show output for successful reads
                            console.print(f"\n[bold cyan]📄 Reading Document[/bold cyan]")
                            console.print(f"[dim]File: {file_path}[/dim]")
                            console.print(f"[green]✓ Successfully read {result['file_type']}[/green]")
                            # Display a preview of the content
                            content_preview = result['content'][:500]
                            if len(result['content']) > 500:
                                content_preview += f"\n... ({len(result['content']) - 500} more characters)"
                            preview_text = Text(content_preview)
                            console.print(Panel(preview_text, title="Content Preview", border_style="cyan"))
                            console.print()

                            # Add content to conversation history (truncate if too large to prevent context overflow)
                            content_for_history = result['content']
                            MAX_CONTENT_SIZE = 50000  # 50KB limit to prevent context overflow

                            if len(result['content']) > MAX_CONTENT_SIZE:
                                # Truncate large content but keep structure
                                content_for_history = result['content'][:MAX_CONTENT_SIZE]
                                content_for_history += f"\n\n[... Content truncated. Total size: {len(result['content'])} characters. Showing first {MAX_CONTENT_SIZE} characters. If you need specific data, you can generate a Python script to extract it.]"

                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"Successfully read {result['file_type']}: {file_path}\n\nContent:\n{content_for_history}"
                            })
                        else:
                            # Silently pass error to model without showing user
                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"Error: {result['error']}"
                            })

                    except Exception as e:
                        # Silently pass error to model without showing user
                        error_msg = f"Failed to read document: {str(e)}"
                        self.conversation_history.append({
                            "role": "tool",
                            "content": error_msg
                        })

                elif function_name == "write_document":
                    file_path = arguments.get("file_path", "") if isinstance(arguments, dict) else getattr(arguments, "file_path", "")
                    operations_param = arguments.get("operations", "") if isinstance(arguments, dict) else getattr(arguments, "operations", "")

                    # Validate parameters
                    if not file_path or not file_path.strip():
                        invalid_call_msg = "Invalid tool call - no file path provided."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": invalid_call_msg
                        })
                        continue

                    # Check if operations is provided (could be string or already parsed object)
                    if not operations_param:
                        invalid_call_msg = "Invalid tool call - no operations provided."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": invalid_call_msg
                        })
                        continue

                    try:
                        import json
                        import ast

                        # Handle both JSON string and already-parsed objects
                        if isinstance(operations_param, str):
                            # DEBUG: Show the raw operations string
                            console.print(f"\n[yellow]DEBUG - Raw operations string:[/yellow]")
                            console.print(f"[dim]{operations_param[:500]}{'...' if len(operations_param) > 500 else ''}[/dim]\n")

                            # Try JSON first
                            try:
                                operations = json.loads(operations_param)
                            except json.JSONDecodeError as e:
                                # Model might have passed Python dict notation with single quotes
                                # OR it might have literal newlines in the JSON string values
                                console.print(f"[yellow]⚠️  JSON parse error, attempting comprehensive fix...[/yellow]")
                                import re

                                # COMPREHENSIVE FIX - same as XML mode
                                fixed_json = operations_param

                                # Step 1: Fix invalid escape sequences
                                fixed_json = re.sub(r'\\([^"\\\/bfnrtu])', r'\1', fixed_json)

                                # Step 2: Fix literal newlines INSIDE JSON string values
                                def escape_literal_newlines_in_json_strings(json_str):
                                    """Escape literal newlines/tabs that appear inside JSON string values."""
                                    result = []
                                    in_string = False
                                    escape_next = False

                                    for char in json_str:
                                        if escape_next:
                                            result.append(char)
                                            escape_next = False
                                            continue

                                        if char == '\\':
                                            result.append(char)
                                            escape_next = True
                                            continue

                                        if char == '"':
                                            in_string = not in_string
                                            result.append(char)
                                            continue

                                        if in_string and char == '\n':
                                            result.append('\\n')
                                            continue

                                        if in_string and char == '\r':
                                            result.append('\\r')
                                            continue

                                        if in_string and char == '\t':
                                            result.append('\\t')
                                            continue

                                        result.append(char)

                                    return ''.join(result)

                                fixed_json = escape_literal_newlines_in_json_strings(fixed_json)

                                # Step 3: Try parsing as Python literal (handles prettified JSON)
                                try:
                                    operations = ast.literal_eval(fixed_json.strip())
                                    console.print(f"[green]✓ Fixed and parsed as Python literal[/green]\n")
                                except:
                                    # Try direct JSON parsing
                                    try:
                                        operations = json.loads(fixed_json)
                                        console.print(f"[green]✓ Fixed with literal newline escaping[/green]\n")
                                    except json.JSONDecodeError as e2:
                                        console.print(f"[red]✗ JSON parsing failed even after fixes[/red]")
                                        console.print(f"[red]  Original error: {e}[/red]")
                                        console.print(f"[red]  After fixes: {e2}[/red]")
                                        # If this looks like a script attempt, give helpful guidance
                                        if 'automation' in file_path.lower() or file_path.endswith('.py'):
                                            console.print(f"[yellow]💡 Tip: Use generate_automation_script tool instead of write_document for complex scripts[/yellow]\n")
                                        # Re-raise with helpful message
                                        raise json.JSONDecodeError(
                                            f"Invalid JSON even after fixes. Use compact JSON: {{\"type\":\"...\"}}, not prettified or with literal newlines",
                                            operations_param,
                                            0
                                        )
                        elif isinstance(operations_param, (list, dict)):
                            # Model passed operations as already-parsed object
                            console.print(f"\n[yellow]DEBUG - Operations passed as object (not string)[/yellow]")
                            console.print(f"[dim]Type: {type(operations_param)}[/dim]\n")
                            operations = operations_param
                        else:
                            raise ValueError(f"Operations must be JSON string or list/dict, got {type(operations_param)}")

                        # Resolve file path relative to safe_directory
                        from pathlib import Path
                        file_path_obj = Path(file_path)
                        if not file_path_obj.is_absolute():
                            # Relative path - make it relative to safe_directory
                            file_path = str(self.executor.safe_directory / file_path)

                        # Write the document with spinner
                        console.print(f"\n[bold green]✏️  Writing Document[/bold green]")
                        console.print(f"[dim]File: {file_path}[/dim]")

                        with Live(
                            Spinner("dots", text="[yellow]writing...[/yellow]"),
                            console=console,
                            auto_refresh=True,
                            refresh_per_second=10,
                            transient=True
                        ):
                            result = write_document(file_path, operations)

                        if result["success"]:
                            console.print(f"[green]✓ Successfully wrote document[/green]")
                            console.print(f"[dim]{result['message']}[/dim]")
                            console.print(f"[dim]Operations applied: {result['operations_applied']}[/dim]")
                            console.print()

                            # Add result to conversation history
                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"Successfully modified {file_path}\n{result['message']}\nOperations applied: {result['operations_applied']}"
                            })
                        else:
                            console.print(f"[red]✗ {result['error']}[/red]\n")
                            # Track failed write
                            from pathlib import Path
                            self.failed_writes_this_turn.add(Path(file_path).name)
                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"Error: {result['error']}"
                            })

                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid operations JSON: {str(e)}"
                        console.print(f"[red]✗ {error_msg}[/red]")
                        console.print(f"[red]Raw data that failed:[/red]")
                        console.print(f"[dim]{operations_param}[/dim]\n")
                        # Track failed write
                        from pathlib import Path
                        self.failed_writes_this_turn.add(Path(file_path).name)
                        self.conversation_history.append({
                            "role": "tool",
                            "content": f"{error_msg}\n\nThe JSON you provided is malformed. Remember: all property names must be in double quotes. Example: {{\"type\":\"append_paragraph\",\"text\":\"Hello\"}}"
                        })
                    except ValueError as e:
                        # Invalid type for operations parameter
                        error_msg = f"Invalid operations parameter: {str(e)}"
                        console.print(f"[red]✗ {error_msg}[/red]\n")
                        # Track failed write
                        from pathlib import Path
                        self.failed_writes_this_turn.add(Path(file_path).name)
                        self.conversation_history.append({
                            "role": "tool",
                            "content": error_msg
                        })
                    except Exception as e:
                        error_msg = f"Failed to write document: {str(e)}"
                        console.print(f"[red]✗ {error_msg}[/red]\n")
                        # Track failed write
                        from pathlib import Path
                        self.failed_writes_this_turn.add(Path(file_path).name)
                        self.conversation_history.append({
                            "role": "tool",
                            "content": error_msg
                        })

                elif function_name == "generate_automation_script":
                    task_description = arguments.get("task_description", "") if isinstance(arguments, dict) else getattr(arguments, "task_description", "")
                    script_code = arguments.get("script_code", "") if isinstance(arguments, dict) else getattr(arguments, "script_code", "")

                    # Validate parameters
                    if not task_description or not task_description.strip():
                        invalid_call_msg = "Invalid tool call - no task description provided."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": invalid_call_msg
                        })
                        continue

                    if not script_code or not script_code.strip():
                        invalid_call_msg = "Invalid tool call - no script code provided."
                        self.conversation_history.append({
                            "role": "tool",
                            "content": invalid_call_msg
                        })
                        continue

                    try:
                        console.print(f"\n[bold magenta]🤖 Generating Automation Script[/bold magenta]")
                        console.print(f"[dim]Task: {task_description}[/dim]")

                        # Strip markdown code fences and triple quotes
                        cleaned = False

                        # Strip markdown code fences (```python or ```)
                        if script_code.startswith("```"):
                            first_newline = script_code.find('\n')
                            if first_newline > 0:
                                script_code = script_code[first_newline+1:]
                            else:
                                script_code = script_code[3:]

                            if script_code.endswith("```"):
                                script_code = script_code[:-3]

                            script_code = script_code.strip()
                            cleaned = True

                        # Strip triple quotes
                        elif script_code.startswith("'''") and script_code.endswith("'''"):
                            script_code = script_code[3:-3].strip()
                            cleaned = True
                        elif script_code.startswith('"""') and script_code.endswith('"""'):
                            script_code = script_code[3:-3].strip()
                            cleaned = True

                        if cleaned:
                            console.print(f"[yellow]⚠️  Stripped markdown/quotes from script[/yellow]")

                        # Validate script has required imports
                        if "from slice_agent.document_reader import read_document" not in script_code:
                            error_msg = "Script is missing required import: from slice_agent.document_reader import read_document"
                            console.print(f"[red]✗ {error_msg}[/red]\n")
                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"ERROR: {error_msg}\n\nYou must import read_document to read files. Regenerate the script with proper imports."
                            })
                            continue

                        # Warn about placeholder code
                        if "# ..." in script_code or "# Process" in script_code or "operations_list" in script_code:
                            console.print(f"[yellow]⚠️  Warning: Script contains placeholders or incomplete code[/yellow]")
                            console.print(f"[yellow]    This will likely fail during execution[/yellow]\n")

                        # Save script to automation_script.py (in current directory)
                        import os
                        script_path = "automation_script.py"
                        full_path = os.path.join(self.executor.safe_directory, script_path)

                        console.print(f"[dim]Saving script to: {full_path}[/dim]")
                        result = write_document(script_path, {"type": "replace_content", "text": script_code})

                        if not result["success"]:
                            error_msg = f"Failed to save script: {result['error']}"
                            console.print(f"[red]✗ {error_msg}[/red]\n")
                            self.conversation_history.append({
                                "role": "tool",
                                "content": error_msg
                            })
                            continue

                        console.print(f"[green]✓ Script saved to {script_path}[/green]")
                        console.print(f"[dim]Executing script...[/dim]\n")

                        # Execute the script (use python3 for macOS compatibility)
                        exec_result = self.executor.execute_with_permission(
                            f"python3 {script_path}",
                            f"Run automation script: {task_description}"
                        )

                        # Check if user cancelled
                        if exec_result.get("cancelled", False):
                            user_cancelled = True
                            break

                        # Add result to conversation history
                        if exec_result["success"]:
                            success_msg = f"Automation script executed successfully.\n\nTask: {task_description}\nOutput:\n{exec_result['output']}"
                            self.conversation_history.append({
                                "role": "tool",
                                "content": success_msg
                            })
                        else:
                            error_msg = f"Script execution failed.\n\nTask: {task_description}\nError:\n{exec_result['error']}"
                            self.conversation_history.append({
                                "role": "tool",
                                "content": error_msg
                            })

                    except Exception as e:
                        error_msg = f"Failed to generate/execute automation script: {str(e)}"
                        console.print(f"[red]✗ {error_msg}[/red]\n")
                        self.conversation_history.append({
                            "role": "tool",
                            "content": error_msg
                        })

            # If user cancelled, stop the loop and return
            if user_cancelled:
                cancellation_msg = "I understand. Let me know if you need anything else!"
                self.conversation_history.append({
                    "role": "assistant",
                    "content": cancellation_msg
                })
                return cancellation_msg

            # Get response after tool execution (might be another tool call or final message)
            # Show spinner while model is thinking
            with Live(
                Spinner("dots", text="[yellow]baking...[/yellow]"),
                console=console,
                auto_refresh=True,
                refresh_per_second=10,
                transient=True
            ):
                response = ollama.chat(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=TOOLS
                )

            message = response.message

        # If we hit max iterations, return what we have
        content = message.content or ""
        if not content.strip():
            content = "Maximum tool call iterations reached."
        self.conversation_history.append({
            "role": "assistant",
            "content": content
        })
        return content

    def _handle_xml_actions(self, text: str) -> str:
        """
        Handle action requests in XML format for models without tool support.

        Looks for:
        - <action command='ls -la'>reason</action>
        - <read file='document.pdf'/>
        """
        # PROCESS ORDER: read → write → action
        # This ensures writes complete before actions that depend on them

        # Handle document reading
        read_pattern = r"<read file=['\"]([^'\"]+)['\"]\s*/>"

        def replace_read(match):
            file_path = match.group(1)

            # Check if file was already read this turn (silently reject)
            if file_path in self.files_read_this_turn:
                return f"[REJECTED: You already read '{file_path}' in this turn. DO NOT re-read files.]"

            # Track this file
            self.files_read_this_turn.add(file_path)

            # Read with spinner (only show output for successful reads)
            with Live(
                Spinner("dots", text="[yellow]reading...[/yellow]"),
                console=console,
                auto_refresh=True,
                refresh_per_second=10,
                transient=True
            ):
                result = read_document(file_path)

            if result["success"]:
                # Only show output for successful reads
                console.print(f"\n[bold cyan]📄 Reading Document[/bold cyan]")
                console.print(f"[dim]File: {file_path}[/dim]")
                console.print(f"[green]✓ Successfully read {result['file_type']}[/green]")
                # Display a preview
                content_preview = result['content'][:500]
                if len(result['content']) > 500:
                    content_preview += f"\n... ({len(result['content']) - 500} more characters)"
                preview_text = Text(content_preview)
                console.print(Panel(preview_text, title="Content Preview", border_style="cyan"))
                console.print()

                # Truncate large content to prevent context overflow
                content_for_model = result['content']
                MAX_CONTENT_SIZE = 50000  # 50KB limit

                if len(result['content']) > MAX_CONTENT_SIZE:
                    content_for_model = result['content'][:MAX_CONTENT_SIZE]
                    content_for_model += f"\n\n[... Content truncated. Total size: {len(result['content'])} characters. Showing first {MAX_CONTENT_SIZE} characters. Generate a Python script to process the full file if needed.]"

                return f"[Document read successfully]\n\nContent from {file_path}:\n{content_for_model}"
            else:
                # Silently return error to model without showing user
                return f"[Failed to read document: {result['error']}]"

        text = re.sub(read_pattern, replace_read, text)

        # Handle document writing
        # Use single quotes for operations attribute to allow JSON double quotes inside
        # Pattern supports: <write file='...' operations='...' /> or </write>
        # Handles single quotes ', triple quotes ''', and various endings
        # Use re.DOTALL to match across newlines
        write_pattern = r"<write\s+file=['\"]([^'\"]+)['\"]\s+operations=['\"]+(.*?)['\"]+ *(?:/>|>.*?</write>)"

        def replace_write(match):
            import json
            file_path = match.group(1)
            operations_json = match.group(2).strip()

            try:
                # DEBUG: Show the raw JSON we're trying to parse
                console.print(f"\n[yellow]DEBUG - Raw operations JSON:[/yellow]")
                console.print(f"[dim]{operations_json[:500]}{'...' if len(operations_json) > 500 else ''}[/dim]\n")

                # Handle common JSON errors from models
                try:
                    operations = json.loads(operations_json)
                except json.JSONDecodeError as e:
                    console.print(f"[yellow]⚠️  JSON parse error, attempting comprehensive fix...[/yellow]")
                    import re
                    import ast

                    # COMPREHENSIVE FIX - handle all common model errors at once
                    fixed_json = operations_json

                    # Step 1: Fix invalid escape sequences FIRST (before any other processing)
                    # Models escape underscores: slice\_agent → slice_agent
                    # Only valid JSON escapes are: \" \\ \/ \b \f \n \r \t \uXXXX
                    fixed_json = re.sub(r'\\([^"\\\/bfnrtu])', r'\1', fixed_json)

                    # Step 2: Fix literal newlines INSIDE JSON string values
                    # This uses a state machine to track when we're inside a string and escape literal newlines
                    def escape_literal_newlines_in_json_strings(json_str):
                        """Escape literal newlines/tabs that appear inside JSON string values."""
                        result = []
                        in_string = False
                        escape_next = False

                        for char in json_str:
                            if escape_next:
                                # Previous char was backslash, keep this char as-is
                                result.append(char)
                                escape_next = False
                                continue

                            if char == '\\':
                                # Backslash - next char is escaped
                                result.append(char)
                                escape_next = True
                                continue

                            if char == '"':
                                # Quote - toggle in/out of string
                                in_string = not in_string
                                result.append(char)
                                continue

                            if in_string and char == '\n':
                                # Literal newline inside a string value - escape it
                                result.append('\\n')
                                continue

                            if in_string and char == '\r':
                                # Literal carriage return inside a string value - escape it
                                result.append('\\r')
                                continue

                            if in_string and char == '\t':
                                # Literal tab inside a string value - escape it
                                result.append('\\t')
                                continue

                            # Regular character - keep as-is
                            result.append(char)

                        return ''.join(result)

                    fixed_json = escape_literal_newlines_in_json_strings(fixed_json)

                    # Step 3: Try parsing as Python literal (handles prettified JSON)
                    try:
                        parsed = ast.literal_eval(fixed_json.strip())
                        # Success! Convert to proper JSON
                        operations = parsed if isinstance(parsed, (dict, list)) else json.loads(json.dumps(parsed))
                        console.print(f"[green]✓ Fixed JSON using comprehensive repairs[/green]\n")
                    except:
                        # ast.literal_eval failed, try direct JSON parsing
                        try:
                            operations = json.loads(fixed_json)
                            console.print(f"[green]✓ Fixed JSON with literal newline escaping[/green]\n")
                        except json.JSONDecodeError as e2:
                            # Last resort: show detailed error
                            console.print(f"[red]✗ JSON parsing failed even after fixes[/red]")
                            console.print(f"[red]  Original error: {e}[/red]")
                            console.print(f"[red]  After fixes: {e2}[/red]")
                            # If this looks like a script attempt, give helpful guidance
                            if 'automation' in file_path.lower() or file_path.endswith('.py'):
                                console.print(f"[yellow]💡 Tip: Try generating SIMPLER Python code without complex nested structures[/yellow]")
                                console.print(f"[yellow]   Or break the task into smaller write operations instead of one big script[/yellow]\n")
                            raise e

                # If writing an automation script, validate it
                if file_path.endswith('.py') and 'automation' in file_path.lower():
                    # Get the script content from operations
                    script_content = ""
                    if isinstance(operations, dict) and operations.get('type') == 'replace_content':
                        script_content = operations.get('text', '')
                    elif isinstance(operations, list):
                        for op in operations:
                            if isinstance(op, dict) and op.get('type') == 'replace_content':
                                script_content = op.get('text', '')
                                break

                    # Strip markdown code fences and triple quotes from script
                    cleaned = False

                    # Strip markdown code fences (```python or ```)
                    if script_content.startswith("```"):
                        # Find end of first line (language identifier)
                        first_newline = script_content.find('\n')
                        if first_newline > 0:
                            script_content = script_content[first_newline+1:]
                        else:
                            script_content = script_content[3:]

                        # Strip closing ```
                        if script_content.endswith("```"):
                            script_content = script_content[:-3]

                        script_content = script_content.strip()
                        cleaned = True

                    # Strip triple quotes if model wrapped the script
                    elif script_content.startswith("'''") and script_content.endswith("'''"):
                        script_content = script_content[3:-3].strip()
                        cleaned = True
                    elif script_content.startswith('"""') and script_content.endswith('"""'):
                        script_content = script_content[3:-3].strip()
                        cleaned = True

                    # Update operations if we cleaned anything
                    if cleaned:
                        if isinstance(operations, dict):
                            operations['text'] = script_content
                        elif isinstance(operations, list):
                            for op in operations:
                                if isinstance(op, dict) and op.get('type') == 'replace_content':
                                    op['text'] = script_content
                                    break
                        console.print(f"[yellow]⚠️  Stripped markdown/quotes from script content[/yellow]")

                    # Validate script
                    if script_content:
                        console.print(f"\n[bold magenta]🤖 Validating Automation Script[/bold magenta]")

                        if "from slice_agent.document_reader import read_document" not in script_content:
                            console.print(f"[red]✗ Script is missing required import: from slice_agent.document_reader import read_document[/red]\n")
                            return "[ERROR: Script validation failed - missing required imports. You must import read_document.]"

                        # Warn about placeholder code
                        if "# ..." in script_content or ("# Process" in script_content and "..." in script_content) or ("operations_list" in script_content and "operations_list = " not in script_content):
                            console.print(f"[yellow]⚠️  Warning: Script contains placeholders or incomplete code[/yellow]")
                            console.print(f"[yellow]    The script will likely fail when executed[/yellow]")
                            console.print(f"[yellow]    Please generate a COMPLETE script with all logic implemented[/yellow]\n")

                # Resolve file path relative to safe_directory
                from pathlib import Path
                file_path_obj = Path(file_path)
                if not file_path_obj.is_absolute():
                    # Relative path - make it relative to safe_directory
                    file_path = str(self.executor.safe_directory / file_path)

                console.print(f"\n[bold green]✏️  Writing Document[/bold green]")
                console.print(f"[dim]File: {file_path}[/dim]")

                with Live(
                    Spinner("dots", text="[yellow]writing...[/yellow]"),
                    console=console,
                    auto_refresh=True,
                    refresh_per_second=10,
                    transient=True
                ):
                    result = write_document(file_path, operations)

                if result["success"]:
                    console.print(f"[green]✓ Successfully wrote document[/green]")
                    console.print(f"[dim]{result['message']}[/dim]")
                    console.print()
                    return f"[Document written successfully]\n{result['message']}\nOperations applied: {result['operations_applied']}"
                else:
                    console.print(f"[red]✗ {result['error']}[/red]\n")
                    # Track failed write - extract filename for dependency checking
                    from pathlib import Path
                    self.failed_writes_this_turn.add(Path(file_path).name)
                    return f"[Failed to write document: {result['error']}]"

            except json.JSONDecodeError as e:
                console.print(f"[red]✗ Invalid operations JSON: {e}[/red]")
                console.print(f"[red]Raw JSON that failed:[/red]")
                console.print(f"[dim]{operations_json}[/dim]\n")
                # Track failed write
                from pathlib import Path
                self.failed_writes_this_turn.add(Path(file_path).name)
                return f"[Failed to write document: Invalid JSON - {str(e)}. All property names must be in double quotes.]"
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]\n")
                # Track failed write
                from pathlib import Path
                self.failed_writes_this_turn.add(Path(file_path).name)
                return f"[Failed to write document: {str(e)}]"

        text = re.sub(write_pattern, replace_write, text, flags=re.DOTALL)

        # Handle command execution (processed LAST so we can check for failed writes)
        action_pattern = r"<action command=['\"]([^'\"]+)['\"]>([^<]*)</action>"

        def replace_action(match):
            command = match.group(1)
            reason = match.group(2).strip()

            # Check if command was already run this turn (silently reject)
            if command in self.commands_run_this_turn:
                return f"[REJECTED: You already ran '{command}' in this turn. DO NOT repeat commands.]"

            # Check if command references a file that failed to write
            for failed_file in self.failed_writes_this_turn:
                if failed_file in command:
                    console.print(f"[red]⚠️  Skipping action - file '{failed_file}' failed to write[/red]\n")
                    return f"[SKIPPED: Cannot execute command because '{failed_file}' failed to write. Fix the write operation first.]"

            # Track this command
            self.commands_run_this_turn.add(command)

            # Execute with permission
            result = self.executor.execute_with_permission(command, reason)

            if result["cancelled"]:
                return "[Action cancelled by user]"
            elif result["success"]:
                return f"[Command executed successfully]\nOutput: {result['output']}"
            else:
                return f"[Command failed]\nError: {result['error']}"

        text = re.sub(action_pattern, replace_action, text)

        return text
