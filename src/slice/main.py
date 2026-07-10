"""Main entry point for Slice IDE."""

import sys
import os
import signal
from rich.console import Console
from .ui import ModelSelector, ChatUI
from .chat import ChatSession
from .skills import SkillLoader

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

▄█████ ▄▄    ▄▄  ▄▄▄▄ ▄▄▄▄▄
▀▀▀▄▄▄ ██    ██ ██▀▀▀ ██▄▄
█████▀ ██▄▄▄ ██ ▀████ ██▄▄▄
                                [/bold cyan]""")
    console.print("[cyan]" + "─" * 64 + "[/cyan]")
    console.print("[cyan]v1.4.0 - Skills Support[/cyan]")
    console.print()
    console.print("[cyan]💡 Tips:[/cyan]")
    console.print("[cyan]  • Type /model to switch models during your session[/cyan]")
    console.print("[cyan]  • Press Ctrl+C once to interrupt generation, twice to exit[/cyan]")
    console.print("[cyan]  • Press Ctrl+Z to completely stop the process and exit[/cyan]")
    console.print()
    console.print("[dim]Different models have different strengths. Choose based on your task:[/dim]")
    console.print("[dim]  • Code tasks: Models trained for tool use work best[/dim]")
    console.print("[dim]  • Mixed chat/actions: Try gemma4, mistral, or qwen2[/dim]")
    console.print()

    # Show model selector
    selector = ModelSelector()
    selected_model = selector.select_model()

    if not selected_model:
        console.print("[yellow]No model selected. Exiting.[/yellow]")
        return

    # Initialize chat session with selected model
    safe_dir = os.getcwd()

    # Load skills from slice-skills/ directory
    skill_loader = SkillLoader(safe_dir)
    loaded_skills = skill_loader.load_skills()

    # Display loaded skills if any
    if skill_loader.has_skills():
        console.print(f"[cyan]✓ Loaded {len(loaded_skills)} skill(s): {', '.join(f'/{name}' for name in skill_loader.list_skill_names())}[/cyan]")
        console.print()

    session = ChatSession(selected_model, safe_directory=safe_dir, skill_loader=skill_loader)

    # Start chat UI
    chat_ui = ChatUI(session, safe_directory=safe_dir)
    chat_ui.run()


if __name__ == "__main__":
    main()
