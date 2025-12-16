import time
import ipaddress
from typing import Optional, List

import typer
from fastapi import FastAPI

from wireguard_py.peers import Endpoint

from wire_fabric.daemon.ifmanager import InterfaceManager
from wire_fabric.daemon.server.fabricapi import FabricAPIServer
from wire_fabric.daemon.pyroute_worker import IPRouteWorker

app = typer.Typer(help="Management CLI for Fabric", no_args_is_help=True)

@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", help="Host IP to listen to"),
    port: int  = typer.Option(8000, "--port", help="Port to listen to"),
    ):
    """Create management server"""

    app = FastAPI(
        title="Wireguard API",
        summary="",
        description="",
        version="1.0"
    )
    # _network = ipaddress.ip_network(network)
    ipyrouteworker = IPRouteWorker()
    iface_manager = InterfaceManager()

    server = FabricAPIServer(
        app = app,
        host = host,
        port = port,
        ifacemanager = iface_manager,
        ipyrouteworker=ipyrouteworker,
    )
    server.up()

    my_var_running = True
    while my_var_running:
        time.sleep(5)

    server.down()
    exit(0)
