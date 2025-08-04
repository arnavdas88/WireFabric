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

app = typer.Typer(help="Fabrics Management Client", no_args_is_help=True)

@app.command()
def info(
    host: str = typer.Option("127.0.0.1", "--host", help="The management host to connect the cli to"),
    port: int = typer.Option(8000, "--port", help="The management host to connect the cli to"),
    ):
    with httpx.Client(timeout=3) as client:
        response = client.get(f"http://{host}:{port}/state")
        stats = response.json()
        print("Name : ", stats['name'])
        print("Status : ", stats['status'])
        print("Network : ", stats['network'])

        sorted_master_endpoints = sorted(stats['master_nodes'].items(), key=lambda x:x[1]['weight'])
        sorted_management_endpoints = sorted(stats['management'].items(), key=lambda x:x[1]['weight'])

        # Master
        print("Total master servers : ", len(stats['master_nodes']))
        for name, master_server in sorted_master_endpoints:
            print("\t" + name)

        # Management
        print("Total management servers : ", len(stats['management']))
        for name, management_server in sorted_management_endpoints:
            print("\t" + name)

        # Nodes
        print("Total nodes : ", len(stats['node_keys']))
        for node_names, _ in stats['node_keys'].items():
            print("\t" + str(node_names))

@app.command()
def discovery_token(
    host: str = typer.Option("127.0.0.1", "--host", help="The management host to connect the cli to"),
    port: int = typer.Option(8000, "--port", help="The management host to connect the cli to"),
    ):
    with httpx.Client(timeout=3) as client:
        response = client.get(f"http://{host}:{port}/state")
        stats = response.json()

        sorted_master_endpoints = sorted(stats['master_nodes'].items(), key=lambda x:x[1]['weight'])
        sorted_management_endpoints = sorted(stats['management'].items(), key=lambda x:x[1]['weight'])
        
        # Take the first management server
        # TODO: Choose the first alive and active management server
        name, management_server = sorted_management_endpoints[0]
        management_server = management_server.copy()
        del management_server['weight']
        token = base64.urlsafe_b64encode(json.dumps(management_server).encode())

        print(f"wire_fabric join --token {token.decode()}")

@app.command()
def join(
    token: str = typer.Option(..., "--token", help="Join token for the fabric (e.g. abcdefg.ijklmno.pqrstuv)"),
    host: str = typer.Option("127.0.0.1", "--host", help="The management host to connect the cli to"),
    port: int = typer.Option(8000, "--port", help="The management host to connect the cli to"),
    ):
    """Join an existing Wire Fabric node using a token."""
    # if len(token.split('.')) != 3:
    #     typer.echo("❌ Invalid token format. Expected three parts separated by dots.")
    #     raise typer.Exit(code=1)
    data = base64.urlsafe_b64decode(token.encode())
    data = json.loads(data.decode())
    print(data)

    with httpx.Client(timeout=3) as client:
        response = client.post(f"http://{host}:{port}/register/management", json=data)
        if not response.status_code == 200:
            typer.echo(response.json())

    typer.echo(f"🔗 Joining Wire Fabric using token: {token}")
    # Here, you would call logic to join the fabric
    typer.echo("✅ Successfully joined the fabric!")

@app.command()
def activate(
    host: str = typer.Option("127.0.0.1", "--host", help="The management host to connect the cli to"),
    port: int = typer.Option(8000, "--port", help="The management host to connect the cli to"),
    ):
    with httpx.Client(timeout=3) as client:
        response = client.post(f"http://{host}:{port}/manage", data=json.dumps({"action": "Start"}))
        if response.status_code == 200:
            status = response.json()
            print(status)
        else:
            raise Exception()

@app.command()
def deactivate(
    host: str = typer.Option("127.0.0.1", "--host", help="The management host to connect the cli to"),
    port: int = typer.Option(8000, "--port", help="The management host to connect the cli to"),
    ):
    with httpx.Client(timeout=3) as client:
        response = client.post(f"http://{host}:{port}/manage", data=json.dumps({"action": "Stop"}))
        if response.status_code == 200:
            status = response.json()
            print(status)
        else:
            raise Exception()
