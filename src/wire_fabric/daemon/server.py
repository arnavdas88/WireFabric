from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from wireguard_py.interface import WireGuardInterface
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pyroute2

from typing import List, Mapping

from wire_fabric.daemon.dataclass import NetworkDefinition, VirtualFabricNodes, VirtualFabricNetwork
from wire_fabric.daemon.pyroute_worker import IPRouteWorker
app = FastAPI()

class InterfaceManager:
    def __init__(self):
        self.active_interfaces: Mapping[str, WireGuardInterface] = {}

    def create(self, interface: WireGuardInterface):
        self.active_interfaces[interface.name] = interface
        if interface.status:
            interface.bring_down()
        interface.bring_up()

    def remove(self, interface_name: str):
        self.active_interfaces[interface_name].bring_down()
        del self.active_interfaces[interface_name]

    def add_peers(self, interface_name: str, peer: Peer):
        self.active_interfaces[interface_name].bring_down()
        self.active_interfaces[interface_name].add_peer(peer)
        self.active_interfaces[interface_name].bring_up()

    def restart(self, interface_name: str):
        self.active_interfaces[interface_name].bring_down()
        self.active_interfaces[interface_name].bring_up()

manager = InterfaceManager()
ipr = IPRouteWorker()

@app.get("/")
def index():
    return {"message": "Hello World !"}

@app.get("/interfaces")
def get_interfaces():
    for interface_name in manager.active_interfaces:
        interface = manager.active_interfaces[interface_name]
        yield {
            "ip": interface.ip,
            "name": interface.name,
            "cidr": interface.cidr,
            "endpoint": interface.endpoint,
            "public_key": interface.keypair.public_key(),
            "peers": list(interface.peers.keys())
        }

@app.get("/interfaces/{name}")
def fetch_interfaces(name: str):
    interface = manager.active_interfaces[name]
    return {
        "ip": interface.ip,
        "name": interface.name,
        "cidr": interface.cidr,
        "endpoint": interface.endpoint,
        "public_key": interface.keypair.public_key()
    }

@app.post("/interfaces/{name}")
def post_interfaces(name:str, network: NetworkDefinition):
    if name in manager.active_interfaces:
        raise HTTPException(status_code=409, detail="Conflict with existing network interface name")

    if network.ip not in network.network:
        raise HTTPException(status_code=422, detail="The IP provided is not a part of the subnet provided")
    

    interface = WireGuardInterface(
        interface_name = name,
        cidr = network.network,
        ip = network.ip, # Subnetwork Ip
        keypair=WireguardKey.generate(),
        endpoint=Endpoint(
            ip = None, # This will become the public ip address of the node.
            port = network.port # Data Port
        ),
        ipr=ipr # IpRoute()
    )
    interface.bring_up()
    VirtualFabricNodes(
        # Endpoints only had data ports for now. Management ports are defined seperately
        public_endpoint=Endpoint(ip=None, port=network.port),
        private_endpoint=Endpoint(ip=network.ip, port=network.port),
        management_port=8000,
        keys=interface.keypair,
        node_type = NodeType.SERVER
    )
    if interface.status:
        print(f"{interface.status =}")
        raise HTTPException(status_code=409, detail="Conflict with existing network interface")

    manager.create(
        interface
    )

    if name in manager.active_interfaces:
        if interface.status:
            return {"message": "success"}
        print(f"{interface.status =}")
        raise HTTPException(status_code=520, detail=f"Unable to bring up the network interface {name}") 

    print(f"{manager.active_interfaces =}")
    raise HTTPException(status_code=520, detail=f"Unable to create network interface {name}")

@app.post("/interfaces/{name}/{peer}")
def post_peers(name: str, peer: str, peer_config: NetworkDefinition):
    interface = manager.active_interfaces[name]
    peer = Peer(
        interface=Endpoint(),
        allowed_ips=[ interface.cidr ],
        privkey=str(node_2_key.private_key()), # Not Compulsory
        pubkey=str(node_2_key.public_key()), 
    )
