import typer

from wire_fabric.cli import client
from wire_fabric.cli import management
from wire_fabric.cli import peer

app = typer.Typer()
app.add_typer(client.app, name="client")
app.add_typer(management.app, name="management")
app.add_typer(peer.app, name="peer")
