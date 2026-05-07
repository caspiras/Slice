"""Main entry point for slice-agent CLI."""

import sys
import os
import signal
from rich.console import Console
from .ui import ModelSelector, ChatUI
from .agent import SliceAgent

console = Console()
exit_count = 0


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully with double-press to exit."""
    global exit_count
    exit_count += 1

    if exit_count == 1:
        console.print("\n[yellow]⚠️  Press Ctrl+C again to exit[/yellow]")
    else:
        console.print("\n[red]👋 Goodbye![/red]")
        sys.exit(0)


def main():
    """Main CLI entry point."""
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)

    # Display ASCII art banner
    console.print("[cyan]" + "─" * 64 + "[/cyan]")
    console.print("""[bold cyan]

▄█████ ▄▄    ▄▄  ▄▄▄▄ ▄▄▄▄▄   ▄████▄  ▄▄▄▄ ▄▄▄▄▄ ▄▄  ▄▄ ▄▄▄▄▄▄
▀▀▀▄▄▄ ██    ██ ██▀▀▀ ██▄▄    ██▄▄██ ██ ▄▄ ██▄▄  ███▄██   ██
█████▀ ██▄▄▄ ██ ▀████ ██▄▄▄   ██  ██ ▀███▀ ██▄▄▄ ██ ▀██   ██
                                                               [/bold cyan]""")
    console.print("[cyan]" + "─" * 64 + "[/cyan]")
    console.print("[cyan]v1.0[/cyan]")
    console.print()
    console.print("[cyan]💡 Tip: Type /model anytime to switch models during your session[/cyan]")
    console.print()
    console.print("[dim]Different models have different strengths. Choose based on your task:[/dim]")
    console.print("[dim]  • Code/agentic tasks: Models trained for tool use work best[/dim]")
    console.print("[dim]  • Mixed chat/actions: Try gemma4, mistral, or qwen2[/dim]")
    console.print()

    # Show model selector
    selector = ModelSelector()
    selected_model = selector.select_model()

    if not selected_model:
        console.print("[yellow]No model selected. Exiting.[/yellow]")
        return

    # Initialize agent with selected model and current directory as sandbox
    safe_dir = os.getcwd()
    agent = SliceAgent(selected_model, safe_directory=safe_dir)

    # Show agent mode
    if agent.supports_tools:
        console.print("[green]✓ Using tool calling for actions[/green]")
    else:
        console.print("[yellow]⚠ Using XML fallback for actions (model doesn't support tools)[/yellow]")
    console.print()

    # Start chat UI
    chat_ui = ChatUI(agent, safe_directory=safe_dir)
    chat_ui.run()


if __name__ == "__main__":
    main()
