import typer
from pathlib import Path
import ipaddress
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from typing import Optional, List
from wire_fabric.cli.create import create

import time, httpx, json, base64
from fastapi import FastAPI
from wireguard_py.peers import Endpoint
from wire_fabric.daemon.server.state import DistributedState, WeightedEndpoint
from wire_fabric.daemon.server.apiserver import FabricAPIServer 
from wire_fabric.daemon.pyroute_worker import IPRouteWorker

app = typer.Typer(help="Management CLI for Fabric", no_args_is_help=True)

@app.command()
def server(
    name: Optional[str] = typer.Option(None, "--name", help="Name of the host. Default is the system hostname"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host IP to listen to"),
    port: int  = typer.Option(8000, "--port", help="Port to listen to"),
    # Virtual Network
    network: str = typer.Option(..., "--network", help="Network CIDR of the fabric"),
    network_ip: Optional[str] = typer.Option(None, "--network-ip", help="Host IP within the provided CIDR of the fabric"),
    data_port: int = typer.Option(41135, "--data-port", help="Data port for wireguard to listen into"),
    active: bool = typer.Option(False, "--active", help="Activate the data port immediately"),
    # Management
    management_public_ip: str = typer.Option(..., "--public-ip", help="Public IP for the host node"),
    management_servers: Optional[List[str]] = typer.Option(None, "--management-servers-list", help="Management server list"),
    ):
    """Create management server"""
    app = FastAPI(title="VPN Fabric Distributed Daemon")
    shared_state = DistributedState(network = ipaddress.ip_network(network))
    ipyrouteworker = IPRouteWorker()
    if name:
        shared_state.name = name
    if network_ip:
        # Validation
        if not ipaddress.ip_address(network_ip):
            raise Exception()
        network_ip = ipaddress.ip_address(network_ip)
        # Check if IP belongs in the network
        if network_ip in network:
            # Set IP as Endpoint information
            shared_state.private_ip = Endpoint(ip = network_ip, port = data_port)
    else:
        shared_state.private_ip = Endpoint(ip = network_ip, port = data_port)
    server = FabricAPIServer(
        app = app,
        host = host,
        port = port,
        shared_state = shared_state,
        public_management_endpoint = Endpoint(
            ip=management_public_ip, 
            port=port, 
        ),
        ipyrouteworker=ipyrouteworker,
    )
    server.shared_state.management[shared_state.name] = WeightedEndpoint(
        ip=management_public_ip, 
        port=port, 
    )
    server.shared_state.master_nodes[shared_state.name] = WeightedEndpoint(
        ip=network_ip, 
        port=data_port, 
    )
    server.up()

    # Add management servers
    if management_servers:
        with httpx.Client(timeout=30) as client:
            for servers in management_servers:
                server_host, server_port = servers.split(":")
                response = client.post(f"http://{host}:{port}/register/management", json={"ip": server_host, "port": int(server_port)})
                if response.status_code == 200:
                    typer.echo("Joined management server.")
                    # print(f"http://{host}:{port}/register/management")
                    # print({"ip": server_host, "port": int(server_port)})
                    # print(response.json())
                else:
                    typer.echo(response.json())
    # Activate the data port
    if active:
        with httpx.Client(timeout=3) as client:
            response = client.post(f"http://{host}:{port}/manage", json={"action": "Start"})
            if response.status_code == 200:
                typer.echo("Data port successfully activated.")
            else:
                typer.echo(response.json())

    my_var_running = True
    while my_var_running:
        time.sleep(5)

    server.down()
    exit(0)
