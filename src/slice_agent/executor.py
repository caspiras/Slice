"""Safe command execution with user permission."""

import subprocess
import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.formatted_text import HTML

class CommandExecutor:
    """Handles safe execution of shell commands with user permission."""

    def __init__(self, safe_directory: str = None):
        self.allowed_commands = set()  # Commands user has allowed this session
        # Use a dedicated console to avoid conflicts with Live displays
        self.console = Console()
        # Directory sandboxing - commands limited to this directory by default
        self.safe_directory = Path(safe_directory or os.getcwd()).resolve()
        self.console.print(f"[dim]Sandboxed to: {self.safe_directory}[/dim]")

    def execute_with_permission(self, command: str, context: str = "") -> Dict[str, Any]:
        """
        Execute a command after getting user permission.

        Args:
            command: The shell command to execute
            context: Optional context about why the command is being run

        Returns:
            Dict with 'success', 'output', 'error', 'cancelled' keys
        """
        # Show what will be executed
        self.console.print("\n[bold yellow]🔧 Action Requested[/bold yellow]")
        if context:
            self.console.print(f"[dim]{context}[/dim]")

        # Check for dangerous patterns
        is_safe, danger_msg = self.is_safe_command(command)

        # Check for sandbox escape
        escapes_sandbox, suspicious_paths = self.check_sandbox_escape(command)

        # Display the command with appropriate border color
        border_color = "red" if not is_safe or escapes_sandbox else "yellow"
        # Show command in plain black text (no syntax highlighting)
        self.console.print(Panel(command, title="Command", border_style=border_color))

        # Show warnings
        if not is_safe:
            self.console.print(f"[bold red]⚠️  DANGER: {danger_msg}[/bold red]")

        if escapes_sandbox:
            self.console.print(f"[bold red]⚠️  SANDBOX ESCAPE DETECTED[/bold red]")
            self.console.print(f"[red]This command tries to access paths outside: {self.safe_directory}[/red]")
            self.console.print("[red]Suspicious paths:[/red]")
            for path in suspicious_paths:
                self.console.print(f"  [red]• {path}[/red]")
            self.console.print()

        # Ask for permission using prompt_toolkit (works better with Live displays)
        try:
            if escapes_sandbox or not is_safe:
                prompt_text = HTML("<red><b>⚠️  Are you SURE you want to execute this? (yes/N): </b></red>")
                # Require explicit "yes" for dangerous/escaped commands
                response = pt_prompt(prompt_text, default="").strip().lower()
                if response != 'yes':
                    self.console.print("[dim]Action cancelled by user[/dim]\n")
                    return {
                        "success": False,
                        "output": "",
                        "error": "",
                        "cancelled": True
                    }
            else:
                # Normal permission prompt
                response = pt_prompt(
                    HTML("<red>Execute this command? (y/N): </red>"),
                    default=""
                ).strip().lower()

                if response not in ('y', 'yes'):
                    self.console.print("[dim]Action cancelled by user[/dim]\n")
                    return {
                        "success": False,
                        "output": "",
                        "error": "",
                        "cancelled": True
                    }
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[dim]Action cancelled by user[/dim]\n")
            return {
                "success": False,
                "output": "",
                "error": "",
                "cancelled": True
            }

        # Execute the command
        try:
            self.console.print("[dim]Executing...[/dim]")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            success = result.returncode == 0
            output = result.stdout.strip()
            error = result.stderr.strip()

            # Show result
            if success:
                self.console.print("[green]✓ Command completed successfully[/green]")
                if output:
                    self.console.print(Panel(output, title="Output", border_style="green"))
            else:
                self.console.print(f"[red]✗ Command failed (exit code: {result.returncode})[/red]")
                if error:
                    self.console.print(Panel(error, title="Error", border_style="red"))

            self.console.print()  # Blank line

            return {
                "success": success,
                "output": output,
                "error": error,
                "cancelled": False
            }

        except subprocess.TimeoutExpired:
            error_msg = "Command timed out after 30 seconds"
            self.console.print(f"[red]✗ {error_msg}[/red]\n")
            return {
                "success": False,
                "output": "",
                "error": error_msg,
                "cancelled": False
            }
        except Exception as e:
            error_msg = f"Failed to execute: {str(e)}"
            self.console.print(f"[red]✗ {error_msg}[/red]\n")
            return {
                "success": False,
                "output": "",
                "error": error_msg,
                "cancelled": False
            }

    def check_sandbox_escape(self, command: str) -> Tuple[bool, List[str]]:
        """
        Check if a command tries to access paths outside the safe directory.

        Returns:
            (escapes_sandbox, list_of_suspicious_paths)
        """
        suspicious_paths = []

        # Patterns that indicate accessing outside the sandbox
        patterns = [
            # Absolute paths
            (r'(?:^|\s)(/[^\s]+)', 'absolute path'),
            # Home directory
            (r'(?:^|\s)(~[^\s]*)', 'home directory'),
            # Parent directory traversal
            (r'(?:^|\s)(\.\./[^\s]*)', 'parent directory'),
            # cd commands
            (r'cd\s+([^\s;&|]+)', 'directory change'),
        ]

        for pattern, description in patterns:
            matches = re.findall(pattern, command)
            for match in matches:
                path_str = match if isinstance(match, str) else match[0]

                # Expand and resolve the path
                try:
                    if path_str.startswith('~'):
                        expanded = Path(path_str).expanduser().resolve()
                    elif path_str.startswith('/'):
                        expanded = Path(path_str).resolve()
                    elif path_str.startswith('..'):
                        expanded = (self.safe_directory / path_str).resolve()
                    else:
                        # Relative path within sandbox
                        expanded = (self.safe_directory / path_str).resolve()

                    # Check if the resolved path is outside safe_directory
                    try:
                        expanded.relative_to(self.safe_directory)
                    except ValueError:
                        # Path is outside the safe directory
                        suspicious_paths.append(f"{path_str} ({description})")
                except Exception:
                    # If we can't resolve it, mark as suspicious
                    suspicious_paths.append(f"{path_str} ({description})")

        return len(suspicious_paths) > 0, suspicious_paths

    def is_safe_command(self, command: str) -> Tuple[bool, str]:
        """
        Check if a command is potentially dangerous.

        Returns:
            (is_safe, warning_message)
        """
        dangerous_patterns = [
            "rm -rf /",
            "mkfs",
            "dd if=",
            "> /dev/sda",
            "fork bomb",
            ":(){ :|:& };:",
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False, f"Potentially dangerous command detected: contains '{pattern}'"

        return True, ""
