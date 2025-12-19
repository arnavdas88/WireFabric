from pydantic import BaseModel, SecretStr
from typing import Dict, List, Mapping, Optional
from ipaddress import IPv4Network, IPv4Address, IPv6Network, IPv6Address
from wireguard_py.peers import Endpoint, Peer
from wireguard_py.keys import WireguardKey

class PeerRequest(BaseModel):
    name: str
    pubkey: str
    endpoint_ip: Optional[IPv4Address]
    endpoint_port: int
    allowed_cidr: IPv4Network

class InterfaceRequest(BaseModel):
    ip: IPv4Address
    cidr: IPv4Network
    listen_port: int
    name: Optional[str] = None
    private_key: Optional[str] = None

class RouteDefinition(BaseModel):
    src: IPv4Network | IPv6Network | None 
    dst: IPv4Network | IPv6Network | None
    gateway: IPv4Address | IPv6Address | None
    interface: str
    is_default: bool
    proto: str
    scope: str
    is_link: bool

class WireGuardInterfaceDefination(BaseModel):
    name : str
    cidr : IPv4Network | IPv6Network
    endpoint: Endpoint | None
    peers : Dict[str, Peer] | List[str] | None
    private_key : WireguardKey | SecretStr | None
    public_key : WireguardKey | str | None
    ip : IPv4Address | IPv6Address | None
    status: bool | None