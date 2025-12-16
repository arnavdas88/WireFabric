from pydantic import BaseModel
from typing import List, Mapping, Optional
from ipaddress import IPv4Network, IPv4Address

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
