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

app = typer.Typer(help="Wire Fabric CLI Tool", )

@app.command()
def management_server(
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
        )
    )
    server.shared_state.management[shared_state.name] = WeightedEndpoint(
        ip=management_public_ip, 
        port=port, 
    )
    server.shared_state.master_nodes[shared_state.name] = WeightedEndpoint(
        ip=management_public_ip, 
        port=data_port, 
    )
    server.up()

    # Add management servers
    if management_servers:
        with httpx.Client(timeout=3) as client:
            for servers in management_servers:
                server_host, server_port = servers.split(":")
                response = client.post(f"http://{host}:{port}/register/management", json={"ip": server_host, "port": int(server_port)})
                if response.status_code == 200:
                    typer.echo("Joined management server.")
                    print(f"http://{host}:{port}/register/management")
                    print({"ip": server_host, "port": int(server_port)})
                    print(response.json())
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
