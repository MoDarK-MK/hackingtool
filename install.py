import os
import subprocess
import sys
import time
import shutil
import stat
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm, Prompt
from rich.text import Text

console = Console()

def check_go_installed():
    """Check if Go is installed."""
    try:
        subprocess.run(["go", "version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_go_tool(tool_url):
    """Install a Go tool using go install."""
    try:
        subprocess.run(["go", "install", tool_url], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error installing {tool_url}: {e}[/bold red]")
        return False

def create_global_command():
    """Create a global command to run the app from any terminal."""
    app_name = "moderndarkterminal"
    script_content = f"""#!/usr/bin/env python3
import os
import sys
import subprocess

# Change to the project directory
project_dir = '{os.path.abspath(os.getcwd())}'
os.chdir(project_dir)

# Run the main.py
subprocess.run([sys.executable, 'main.py'])
"""

    script_path = os.path.join(os.getcwd(), app_name)
    with open(script_path, 'w') as f:
        f.write(script_content)

    os.chmod(script_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    bin_path = '/usr/local/bin' if sys.platform != 'win32' else os.path.join(os.environ.get('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
    
    if sys.platform == 'win32':
        console.print("[yellow]On Windows, adding to PATH manually is recommended. Skipping auto-install for global command.[/yellow]")
        console.print(f"[cyan]Created script at: {script_path}[/cyan]")
        console.print("[cyan]Add the project directory to your PATH or run the script directly.[/cyan]")
        return

    try:
        if Confirm.ask(f"[yellow]Do you want to install the global command '{app_name}'? (Requires sudo)[/yellow]"):
            subprocess.run(['sudo', 'mv', script_path, os.path.join(bin_path, app_name)], check=True)
            console.print(f"[green]✓ Global command '{app_name}' installed! Now run '{app_name}' in any terminal.[/green]")
        else:
            console.print(f"[cyan]Script created at: {script_path}. You can run it with './{app_name}' or add to PATH manually.[/cyan]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error installing global command: {e}[/bold red]")
        console.print(f"[yellow]Please run 'sudo mv {script_path} /usr/local/bin/{app_name}' manually.[/yellow]")

def main():
    console.print(Panel(Text("Welcome to Modern Dark Terminal App Installer!", justify="center", style="bold cyan"), expand=False))

    if not check_go_installed():
        console.print(Panel("[bold red]Go is not installed![/bold red]\nPlease install Go from https://go.dev/dl/ and add it to your PATH.", title="Error", border_style="red"))
        if Confirm.ask("[yellow]Do you want to continue without installing Go tools? (PyQt6 will still be installed)[/yellow]"):
            pass
        else:
            console.print("[bold red]Installation aborted.[/bold red]")
            sys.exit(1)

    tools = [
        "github.com/ffuf/ffuf@latest",
        "github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        transient=True
    ) as progress:
        if check_go_installed():
            task = progress.add_task("[cyan]Installing Go tools...", total=len(tools))
            for tool in tools:
                progress.update(task, description=f"Installing {tool.split('/')[-1].split('@')[0]}...")
                success = install_go_tool(tool)
                if success:
                    console.print(f"[green]✓ {tool} installed successfully![/green]")
                else:
                    console.print(f"[red]✗ Failed to install {tool}.[/red]")
                progress.advance(task)
                time.sleep(0.5)
        else:
            console.print("[yellow]Skipping Go tools installation as Go is not detected.[/yellow]")

    console.print("\n[bold blue]Installing PyQt6...[/bold blue]")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "PyQt6"], check=True)
        console.print("[green]✓ PyQt6 installed successfully![/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error installing PyQt6: {e}[/bold red]")
        console.print("[yellow]Please run 'pip install PyQt6' manually.[/yellow]")

    create_global_command()

    console.print("\n[bold green]Installation Complete![/bold green]")
    console.print(Panel("Run the app with: moderndarkterminal (if installed globally) or python main.py", title="Next Steps", border_style="green"))

if __name__ == "__main__":
    main()