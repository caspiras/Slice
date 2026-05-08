"""UI components for slice-agent using Rich and prompt-toolkit."""

from typing import Optional
import sys
import signal
import tty
import termios
from pathlib import Path
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

console = Console()


class ModelSelector:
    """Interactive model selector with tool support indicators."""

    # Known models with good tool/function calling support
    TOOL_CAPABLE_MODELS = [
        "llama3", "llama3.1", "llama3.2", "llama3.3",
        "mistral", "mixtral",
        "gemma", "gemma2", "gemma4",
        "command-r", "command-r-plus",
        "qwen", "qwen2",
    ]

    def select_model(self) -> Optional[str]:
        """Display available Ollama models and let user select with arrow keys."""
        try:
            # Get list of local models
            models_response = ollama.list()
            models = [model.model for model in models_response.models]

            if not models:
                console.print("[red]No local Ollama models found.[/red]")
                console.print("[yellow]Run 'ollama pull <model>' to download a model first.[/yellow]")
                return None

            # Check if we're in an interactive terminal
            if not sys.stdin.isatty():
                # Fallback to number selection for non-interactive mode
                return self._select_model_by_number(models)

            console.print("[bold]Available Models:[/bold]")
            console.print("[dim]Use ↑/↓ arrows to navigate, Enter to select, Ctrl+C to exit[/dim]\n")

            selected_idx = 0

            # Use Live display for interactive selection
            with Live(self._render_model_list(models, selected_idx), console=console, auto_refresh=False) as live:
                while True:
                    key = self._get_key()

                    if key == '\x03':  # Ctrl+C
                        console.print("\n[yellow]Selection cancelled[/yellow]")
                        return None
                    elif key == '\x1b[A':  # Up arrow
                        selected_idx = (selected_idx - 1) % len(models)
                        live.update(self._render_model_list(models, selected_idx))
                        live.refresh()
                    elif key == '\x1b[B':  # Down arrow
                        selected_idx = (selected_idx + 1) % len(models)
                        live.update(self._render_model_list(models, selected_idx))
                        live.refresh()
                    elif key in ('\r', '\n'):  # Enter
                        selected = models[selected_idx]
                        break

            console.print(f"\n[green]✓ Selected: {selected}[/green]\n")
            return selected

        except Exception as e:
            console.print(f"[red]Error fetching models: {e}[/red]")
            return None

    def _select_model_by_number(self, models: list[str]) -> Optional[str]:
        """Fallback number-based selection for non-interactive terminals."""
        for idx, model in enumerate(models, 1):
            supports_tools = self._check_tool_support(model)
            tool_indicator = "✓" if supports_tools else "✗"
            console.print(f"  {idx}. {model} [tools {tool_indicator}]")

        console.print("\n🍕 Select a model (enter number): ", end="")
        choice = input().strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                console.print(f"[green]✓ Selected: {selected}[/green]\n")
                return selected
        except ValueError:
            pass

        console.print("[red]Invalid selection[/red]")
        return None

    def _render_model_list(self, models: list[str], selected_idx: int) -> str:
        """Render the model list with the current selection highlighted."""
        lines = []
        for idx, model in enumerate(models):
            supports_tools = self._check_tool_support(model)
            tool_indicator = "[green]✓[/green]" if supports_tools else "[dim]✗[/dim]"

            if idx == selected_idx:
                lines.append(f"[bold cyan]→ {model} [tools {tool_indicator}][/bold cyan]")
            else:
                lines.append(f"[green]  {model} [tools {tool_indicator}][/green]")

        return "\n".join(lines)

    def _get_key(self) -> str:
        """Get a single keypress from stdin."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            # Check for escape sequences (arrow keys)
            if ch == '\x1b':
                ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _check_tool_support(self, model_name: str) -> bool:
        """Check if a model likely supports tool/function calling."""
        model_lower = model_name.lower()
        return any(capable in model_lower for capable in self.TOOL_CAPABLE_MODELS)


class ChatUI:
    """Chat interface with pizza emoji cursor and 'baking' spinner."""

    def __init__(self, agent, safe_directory=None):
        self.agent = agent
        self.console = Console()
        self.exit_count = 0
        self.safe_directory = safe_directory
        self.model_selector = ModelSelector()
        self.streaming_interrupted = False

        # Set up command history - saved in user's home directory
        history_file = Path.home() / ".slice_history"
        self.history = FileHistory(str(history_file))

    def run(self):
        """Run the interactive chat loop."""
        self.console.print("[dim]Type your message (Ctrl+C once for warning, twice to exit)[/dim]")
        self.console.print("[dim]Type /model to switch models[/dim]")
        self.console.print("[dim]Use ↑/↓ arrows for command history\n[/dim]")

        while True:
            try:
                # Show pizza emoji as cursor with command history
                user_input = prompt("🍕 ", history=self.history, key_bindings=self._get_key_bindings())

                if not user_input.strip():
                    continue

                # Reset exit count when user successfully enters a message
                self.exit_count = 0

                # Check for /model command
                if user_input.strip() == '/model':
                    self._switch_model()
                    continue

                # Stream response with live updates
                # Set up temporary signal handler for streaming interruption
                self.streaming_interrupted = False

                def streaming_interrupt_handler(signum, frame):
                    self.streaming_interrupted = True

                old_handler = signal.signal(signal.SIGINT, streaming_interrupt_handler)

                try:
                    response_text = ""
                    first_token = True

                    with Live(
                        Spinner("dots", text="[yellow]baking...[/yellow]"),
                        console=self.console,
                        auto_refresh=True,
                        refresh_per_second=10,
                        transient=True
                    ) as live:
                        for token in self.agent.process_stream(user_input):
                            # Check if streaming was interrupted
                            if self.streaming_interrupted:
                                break

                            # Check for tool call signal - exit Live display so prompts are visible
                            if token == "__TOOL_CALL_START__":
                                live.stop()
                                continue

                            # Skip empty tokens
                            if not token:
                                continue

                            # On first token, switch from spinner to streaming text
                            if first_token:
                                first_token = False
                                response_text = token
                                live.update(Panel(response_text, border_style="cyan"))
                            else:
                                response_text += token
                                live.update(Panel(response_text, border_style="cyan"))

                    # Restore original signal handler
                    signal.signal(signal.SIGINT, old_handler)

                    # If interrupted, raise KeyboardInterrupt
                    if self.streaming_interrupted:
                        # Show final response before interrupting
                        if response_text:
                            self.console.print(Panel(response_text, border_style="cyan"))
                        self.console.print()  # Blank line
                        raise KeyboardInterrupt()

                    # Display final response (Live was transient, so it's gone)
                    if response_text:
                        self.console.print(Panel(response_text, border_style="cyan"))
                    self.console.print()

                except Exception as e:
                    # Restore signal handler on any exception
                    signal.signal(signal.SIGINT, old_handler)
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    else:
                        self.console.print(f"\n[red]Error: {e}[/red]\n")

            except KeyboardInterrupt:
                self.exit_count += 1
                if self.exit_count == 1:
                    self.console.print("\n[yellow]⚠️  Press Ctrl+C again to exit[/yellow]\n")
                    continue
                else:
                    self.console.print("\n[red]👋 Goodbye![/red]")
                    break
            except EOFError:
                self.console.print("\n[red]👋 Goodbye![/red]")
                break

    def _get_key_bindings(self):
        """Create key bindings for the prompt."""
        kb = KeyBindings()

        @kb.add(Keys.ControlC)
        def _(event):
            # Exit the prompt to trigger KeyboardInterrupt handling
            event.app.exit(exception=KeyboardInterrupt())

        return kb

    def _switch_model(self):
        """Switch to a different model."""
        from .agent import SliceAgent  # Lazy import to avoid circular dependency

        self.console.print("\n[cyan]Switching models...[/cyan]\n")

        # Show model selector
        selected_model = self.model_selector.select_model()

        if not selected_model:
            self.console.print("[yellow]No model selected. Keeping current model.[/yellow]\n")
            return

        # Save conversation history
        old_history = self.agent.conversation_history.copy()

        # Create new agent with selected model
        self.agent = SliceAgent(selected_model, safe_directory=self.safe_directory)

        # Restore conversation history to new agent
        self.agent.conversation_history = old_history

        # Show agent mode
        if self.agent.supports_tools:
            self.console.print("[green]✓ Using tool calling for actions[/green]")
        else:
            self.console.print("[yellow]⚠ Using XML fallback for actions (model doesn't support tools)[/yellow]")
        self.console.print()
