from dataclasses import dataclass, field
from typing import List, Optional
from wireguard_py.peers import Endpoint, Peer
from wireguard_py.keys import WireguardKey
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from enum import StrEnum

class NodeType(StrEnum):
    SERVER = "server" # Public IP Owner
    PEER = "peer" # Doesnot own a public IP 

@dataclass
class NetworkDefinition:
    network: IPv4Network | IPv6Network
    ip: Optional[IPv4Address | IPv6Address]
    port: int

@dataclass
class VirtualFabricNodes:
    public_endpoint: Optional[Endpoint] # Endpoint(ip=..., port=...)
    private_endpoint: Optional[Endpoint] # Endpoint(ip=..., port=...)
    management_port: Optional[int]
    keys: WireguardKey # WireguardKey.generate(), WireguardKey(...).private_key(), WireguardKey(...).public_key()
    node_type: NodeType = field(NodeType.PEER) # OR NodeType.SERVER

@dataclass
class VirtualFabricNetwork:
    server_nodes: List[VirtualFabricNodes]
    peer_nodes: List[VirtualFabricNodes]


