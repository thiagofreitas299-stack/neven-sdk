"""
NEVEN CLI — Command Line Interface
====================================
Usage:
    neven --help
    neven mock-server
    neven identity create --name my-hub-01
    neven identity show ./my-hub-01-identity.json
    neven demo
    neven status
"""

import json
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


LOGO = """
[bold green]
  ███╗   ██╗███████╗██╗   ██╗███████╗███╗   ██╗
  ████╗  ██║██╔════╝██║   ██║██╔════╝████╗  ██║
  ██╔██╗ ██║█████╗  ██║   ██║█████╗  ██╔██╗ ██║
  ██║╚██╗██║██╔══╝  ╚██╗ ██╔╝██╔══╝  ██║╚██╗██║
  ██║ ╚████║███████╗ ╚████╔╝ ███████╗██║ ╚████║
  ╚═╝  ╚═══╝╚══════╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝
[/bold green]
[dim]Physical Intelligence as a Service — neventech.com[/dim]
"""


@click.group()
@click.version_option("1.0.0", prog_name="neven")
def main():
    """NEVEN SDK — Connect any AI agent to the physical world."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# mock-server
# ─────────────────────────────────────────────────────────────────────────────

@main.command("mock-server")
@click.option("--port", default=8420, help="Port to listen on (default: 8420)")
def mock_server(port: int):
    """Start a local mock server that simulates the NEVEN physical runtime.

    Enables full SDK development and testing without any physical hardware.

    \b
    Example:
        neven mock-server
        # Then in your code:
        client = NevenClient(api_key="nv_test_xxx", mock=True)
    """
    from neven.mock_server import run_mock_server
    run_mock_server(port=port)


# ─────────────────────────────────────────────────────────────────────────────
# identity
# ─────────────────────────────────────────────────────────────────────────────

@main.group()
def identity():
    """Manage NEVEN KAIS cryptographic identities."""
    pass


@identity.command("create")
@click.option("--name", required=True, help="Agent name (e.g. hub-sp-iguatemi-01)")
@click.option("--location", default=None, help="Physical location")
@click.option("--capabilities", default="camera,screen,voice", help="Comma-separated capabilities")
@click.option("--output", default=None, help="Output file path (.json)")
def identity_create(name: str, location: str, capabilities: str, output: str):
    """Create a new KAIS cryptographic identity for a physical node.

    \b
    Example:
        neven identity create --name hub-sp-iguatemi-01 \\
                               --location "Shopping Iguatemi, SP" \\
                               --capabilities camera,screen,voice
    """
    from neven.identity import NevenIdentity

    caps_list = [c.strip() for c in capabilities.split(",") if c.strip()]

    console.print(LOGO)
    with console.status(f"Creating KAIS identity for [bold]{name}[/bold]..."):
        time.sleep(0.5)
        identity_obj = NevenIdentity.create(
            agent_name=name,
            location=location,
            capabilities=caps_list,
        )

    saved = identity_obj.save(output)

    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="green")
    table.add_row("DID", identity_obj.did)
    table.add_row("Agent Name", identity_obj.agent_name)
    table.add_row("Fingerprint", identity_obj.public_key_fingerprint)
    table.add_row("Location", location or "—")
    table.add_row("Capabilities", ", ".join(caps_list))
    table.add_row("Created", identity_obj.created_at)
    table.add_row("Saved to", str(saved))

    console.print(Panel(table, title="✅ NEVEN Identity Created", border_style="green"))
    console.print(f"\n[dim]Keep your identity file safe — it contains your private key.[/dim]")


@identity.command("show")
@click.argument("path")
def identity_show(path: str):
    """Show a NEVEN identity (public info only, no private key)."""
    from neven.identity import NevenIdentity

    try:
        id_obj = NevenIdentity.load(path)
    except FileNotFoundError:
        console.print(f"[red]Identity file not found: {path}[/red]")
        sys.exit(1)

    card = id_obj.to_public_card()
    console.print(Panel(
        json.dumps(card, indent=2),
        title=f"🔑 NEVEN Identity: {id_obj.agent_name}",
        border_style="cyan",
    ))


# ─────────────────────────────────────────────────────────────────────────────
# demo
# ─────────────────────────────────────────────────────────────────────────────

@main.command()
def demo():
    """Run a live demonstration using the mock server.

    Starts a mock server and runs a complete NEVEN workflow:
    connect → perceive → act → subscribe
    """
    from neven.mock_server import MockServer
    from neven.client import NevenClient

    console.print(LOGO)
    console.print("[bold]Starting NEVEN Demo...[/bold]\n")

    # Start mock server in background
    server = MockServer(port=8421)
    server.start_background()

    console.print("✅ Mock server started on [cyan]http://localhost:8421[/cyan]\n")

    import os
    os.environ["NEVEN_MOCK"] = "1"

    client = NevenClient(api_key="nv_test_demo123", mock=True)
    # Override to use demo port
    client.base_url = "http://localhost:8421"

    # Step 1: Connect
    console.print("[bold yellow]Step 1:[/bold yellow] Connecting to physical nodes...")
    with console.status("Connecting..."):
        time.sleep(0.5)
        session = client.connect(
            agent_id="neven-demo-agent",
            requested_nodes=["node_rj_keepithub_01", "node_sp_iguatemi_01"],
            capabilities=["perception", "actuation"],
        )
    console.print(f"  ✅ Connected! Session: [green]{session.session_id[:16]}...[/green]")
    console.print(f"  ✅ Authorized nodes: {list(session.authorized_nodes.keys())}\n")

    # Step 2: Perceive
    console.print("[bold yellow]Step 2:[/bold yellow] Perceiving physical space...")
    with console.status("Querying spatial state..."):
        time.sleep(0.5)
        state = client.perceive(
            node_id="node_rj_keepithub_01",
            target_objects=["person", "vehicle"],
        )

    entities = state["spatial_state"]["detected_entities"]
    telemetry = state["spatial_state"]["environmental_telemetry"]
    console.print(f"  👁  Detected [bold]{len(entities)}[/bold] entities in KEEPITHUB Hub #1")
    for e in entities[:3]:
        console.print(f"      → {e['class']} (confidence: {e['confidence']:.0%})")
    console.print(f"  🌡  Temp: {telemetry['temperature_celsius']}°C | "
                  f"Light: {telemetry['ambient_light_lux']} lux\n")

    # Step 3: Act — Display message
    console.print("[bold yellow]Step 3:[/bold yellow] Acting on the physical world...")
    with console.status("Sending display command..."):
        time.sleep(0.5)
        result = client.display(
            node_id="node_sp_iguatemi_01",
            text="Welcome to NEVEN! Powered by Physical Intelligence.",
            duration=10,
        )
    console.print(f"  📺 Message displayed! TX: [green]{result['transaction_id']}[/green]")
    console.print(f"  🛡  DSE status: [green]{result['safety_evaluation']['dse_status']}[/green]\n")

    # Step 4: Unlock (may be blocked by DSE)
    console.print("[bold yellow]Step 4:[/bold yellow] Attempting compartment unlock (DSE test)...")
    with console.status("Sending unlock command (subject to DSE validation)..."):
        time.sleep(0.5)
        try:
            result = client.unlock(
                node_id="node_rj_keepithub_01",
                compartment_id="C-4",
            )
            console.print(f"  🔓 Compartment C-4 unlocked! TX: [green]{result['transaction_id']}[/green]")
            dse = result["safety_evaluation"]
            for rule in dse.get("rules_evaluated", []):
                icon = "✅" if rule["result"] == "passed" else "❌"
                console.print(f"     {icon} Rule: {rule['rule_id']} → {rule['result']}")
        except Exception as e:
            console.print(f"  🛡  [red]DSE BLOCKED:[/red] {e}")
            console.print(f"     (This is correct! DSE protects the physical world)")

    console.print()
    console.print(Panel(
        "[bold green]NEVEN Demo Complete![/bold green]\n\n"
        "You just:\n"
        "  ✅ Connected an AI agent to physical nodes\n"
        "  ✅ Perceived the semantic state of a real space\n"
        "  ✅ Acted on the physical world via API\n"
        "  ✅ Saw the DSE safety engine in action\n\n"
        "[dim]Next: pip install neven-sdk && connect to real hardware[/dim]\n"
        "[dim]Docs: https://docs.neventech.com[/dim]",
        border_style="green",
    ))

    server.stop()


# ─────────────────────────────────────────────────────────────────────────────
# status
# ─────────────────────────────────────────────────────────────────────────────

@main.command()
def status():
    """Check NEVEN SDK and runtime connectivity status."""
    console.print(LOGO)

    table = Table(box=box.ROUNDED, padding=(0, 2))
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Info")

    # SDK version
    table.add_row("SDK Version", "[green]✅ OK[/green]", "1.0.0")

    # Mock server
    try:
        import requests
        r = requests.get("http://localhost:8420/health", timeout=2)
        if r.ok:
            table.add_row("Mock Server", "[green]✅ Running[/green]", "localhost:8420")
        else:
            table.add_row("Mock Server", "[yellow]⚠ Error[/yellow]", str(r.status_code))
    except Exception:
        table.add_row("Mock Server", "[dim]○ Not running[/dim]", "Start: neven mock-server")

    # Production API
    try:
        import requests
        r = requests.get("https://api.neventech.com/health", timeout=5)
        table.add_row("Production API", "[green]✅ Reachable[/green]", "api.neventech.com")
    except Exception:
        table.add_row("Production API", "[yellow]○ Not reachable[/yellow]", "Coming soon")

    # Dependencies
    deps = {"requests": True, "rich": True, "click": True, "pydantic": True}
    for dep, _ in deps.items():
        try:
            __import__(dep)
            table.add_row(f"  dep:{dep}", "[green]✅[/green]", "installed")
        except ImportError:
            table.add_row(f"  dep:{dep}", "[red]❌ Missing[/red]", f"pip install {dep}")

    console.print(Panel(table, title="NEVEN Status", border_style="cyan"))


if __name__ == "__main__":
    main()
