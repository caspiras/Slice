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
            "description": "Read documents (PDF, Word, Excel, CSV, text). CRITICAL RULES: (1) DO NOT read the same file twice in one turn. (2) ONLY read files the user explicitly mentioned - DO NOT make up filenames. (3) When user mentions a filename, read it directly without running 'ls' or 'find' first. (4) If you already read a file and have its content, DO NOT read it again. (5) For Excel files, you get ALL the data at once - don't re-read for different sheets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "EXACT filename user mentioned. DO NOT invent filenames. DO NOT read files you already read. Use current directory unless specified otherwise."
                    }
                },
                "required": ["file_path"]
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

        # If model doesn't support tools, add system message for XML fallback
        if not self.supports_tools:
            self.conversation_history.append({
                "role": "system",
                "content": (
                    "You are a helpful AI assistant with two special XML tags:\n"
                    "1. <action command='...'>reason</action> - for creating/deleting/modifying files, git status\n"
                    "2. <read file='...'/> - for reading documents (PDF, Word, Excel, CSV, text files)\n\n"
                    "CRITICAL RULES TO PREVENT LOOPS:\n"
                    "- DO NOT use the same XML tag twice in one response\n"
                    "- DO NOT read the same file multiple times\n"
                    "- DO NOT run the same command multiple times\n"
                    "- ONLY read files the user explicitly mentioned - DO NOT invent filenames\n"
                    "- When user mentions a filename, read it directly - DO NOT use 'ls' or 'find' first\n"
                    "- If you already have file content, DO NOT re-read it\n\n"
                    "When user asks about content IN a document, use <read file='exact-filename'/> ONCE.\n"
                    "For Excel files, you get ALL sheets and data at once - no need to re-read.\n"
                    "Only use <action> for creating/modifying files or git commands, NOT for verifying file existence."
                )
            })

    def _check_tool_support(self) -> bool:
        """
        Check if the model supports tool/function calling.

        Returns True if the model likely supports tools, False otherwise.
        """
        # Known models with good tool support
        tool_capable_models = [
            "llama3", "llama3.1", "llama3.2", "llama3.3",
            "mistral", "mixtral",
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

            # Check for XML tags if no tool support
            if not self.supports_tools:
                full_message = self._handle_xml_actions(full_message)

            # Add assistant response to history
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

                    try:
                        # Read the document with spinner
                        console.print(f"\n[bold cyan]📄 Reading Document[/bold cyan]")
                        console.print(f"[dim]File: {file_path}[/dim]")

                        with Live(
                            Spinner("dots", text="[yellow]reading...[/yellow]"),
                            console=console,
                            auto_refresh=True,
                            refresh_per_second=10,
                            transient=True
                        ):
                            result = read_document(file_path)

                        if result["success"]:
                            console.print(f"[green]✓ Successfully read {result['file_type']}[/green]")
                            # Display a preview of the content
                            content_preview = result['content'][:500]
                            if len(result['content']) > 500:
                                content_preview += f"\n... ({len(result['content']) - 500} more characters)"
                            preview_text = Text(content_preview)
                            console.print(Panel(preview_text, title="Content Preview", border_style="cyan"))
                            console.print()

                            # Add full content to conversation history
                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"Successfully read {result['file_type']}: {file_path}\n\nContent:\n{result['content']}"
                            })
                        else:
                            console.print(f"[red]✗ {result['error']}[/red]\n")
                            self.conversation_history.append({
                                "role": "tool",
                                "content": f"Error: {result['error']}"
                            })

                    except Exception as e:
                        error_msg = f"Failed to read document: {str(e)}"
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
        # Handle command execution
        action_pattern = r"<action command=['\"]([^'\"]+)['\"]>([^<]*)</action>"

        def replace_action(match):
            command = match.group(1)
            reason = match.group(2).strip()

            # Execute with permission
            result = self.executor.execute_with_permission(command, reason)

            if result["cancelled"]:
                return "[Action cancelled by user]"
            elif result["success"]:
                return f"[Command executed successfully]\nOutput: {result['output']}"
            else:
                return f"[Command failed]\nError: {result['error']}"

        text = re.sub(action_pattern, replace_action, text)

        # Handle document reading
        read_pattern = r"<read file=['\"]([^'\"]+)['\"]\s*/>"

        def replace_read(match):
            file_path = match.group(1)

            console.print(f"\n[bold cyan]📄 Reading Document[/bold cyan]")
            console.print(f"[dim]File: {file_path}[/dim]")

            with Live(
                Spinner("dots", text="[yellow]reading...[/yellow]"),
                console=console,
                auto_refresh=True,
                refresh_per_second=10,
                transient=True
            ):
                result = read_document(file_path)

            if result["success"]:
                console.print(f"[green]✓ Successfully read {result['file_type']}[/green]")
                # Display a preview
                content_preview = result['content'][:500]
                if len(result['content']) > 500:
                    content_preview += f"\n... ({len(result['content']) - 500} more characters)"
                preview_text = Text(content_preview)
                console.print(Panel(preview_text, title="Content Preview", border_style="cyan"))
                console.print()
                return f"[Document read successfully]\n\nContent from {file_path}:\n{result['content']}"
            else:
                console.print(f"[red]✗ {result['error']}[/red]\n")
                return f"[Failed to read document: {result['error']}]"

        text = re.sub(read_pattern, replace_read, text)

        return text
