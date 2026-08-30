import sys
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.table import Table

from agent import run_agent
from guardrails import check_input
from memory import load_memory, save_memory
from logger import get_logger

console = Console()

def print_trace(result: dict):
    final_answer = result["final_answer"]
    tools_used = result["tools_used"]
    steps = result["steps"]
    escalated = result.get("escalated", False)

    console.print()
    console.print(Panel.fit(final_answer, title="Final Answer", border_style="green"))

    table = Table(title="Trace Summary")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_row("Steps", str(steps))
    table.add_row("Tools Used", ", ".join(tools_used) if tools_used else "none")
    table.add_row("Escalated", str(escalated))
    console.print(table)
    console.print()

def main():
    console.print(Panel.fit("Skincare Support Agent", title="Welcome", border_style="blue"))
    console.print("Type your skincare question or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("Goodbye!")
            break

        try:
            check_input(user_input)
        except ValueError as e:
            console.print(f"[red]Blocked:[/red] {e}")
            console.print()
            continue

        memory = load_memory()

        if "my skin type is" in user_input.lower() or "i have" in user_input.lower():
            memory = save_memory(memory)

        result = run_agent(user_input)

        print_trace(result)

        memory = save_memory(memory)

if __name__ == "__main__":
    main()