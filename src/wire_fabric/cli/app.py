import typer
from pathlib import Path
import ipaddress

from wire_fabric.cli.create import create

app = typer.Typer(help="Wire Fabric CLI Tool", )

@app.command()
def create(
    network: str = typer.Option(..., "--network", help="CIDR for the fabric network, e.g. 10.10.10.0/24"),
    ip_address: Optional[str]  = typer.Option(None, "--ip-address", help="IP address of this node in the fabric network, e.g. 10.10.10.1"),
    storage_dir: Path = typer.Option(..., "--storage-dir", help="Directory to store fabric data"),
    management_port: int = typer.Option(8000, "--management-port", help="Port for management interface"),
    fabric_port: int = typer.Option(45337, "--fabric-port", help="Port used for fabric communication"),
    public_ip: Optional[str] = typer.Option(None, "--public-ip", help="Public IP of this node"),
):
    """Create a new Wire Fabric node."""
    try:
        ipaddress.ip_network(network)
        if ip_address:
            ipaddress.ip_address(ip_address)
        if public_ip:
            ipaddress.ip_address(public_ip)
        create(
            ipaddress.ip_network(network),
            ipaddress.ip_address(ip_address),
            ipaddress.ip_address(public_ip),
            fabric_port
        )
    except ValueError as e:
        typer.echo(f"Invalid IP or network: {e}")
        raise typer.Exit(code=1)

    typer.echo("🚀 Creating a new Wire Fabric node with the following parameters:")
    typer.echo(f"  Network: {network}")
    typer.echo(f"  Storage directory: {storage_dir}")
    typer.echo(f"  Management port: {management_port}")
    typer.echo(f"  Fabric port: {fabric_port}")
    typer.echo(f"  Public IP: {public_ip}")

    # Here, you would call actual logic to initialize the fabric
    # For now, we just simulate:
    typer.echo("✅ Node created successfully!")


@app.command()
def join(
    token: str = typer.Argument(..., help="Join token for the fabric (e.g. abcdefg.ijklmno.pqrstuv)"),
):
    """Join an existing Wire Fabric node using a token."""
    if len(token.split('.')) != 3:
        typer.echo("❌ Invalid token format. Expected three parts separated by dots.")
        raise typer.Exit(code=1)

    typer.echo(f"🔗 Joining Wire Fabric using token: {token}")
    # Here, you would call logic to join the fabric
    typer.echo("✅ Successfully joined the fabric!")
