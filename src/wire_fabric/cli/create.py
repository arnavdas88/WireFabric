from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from typing import List, Optional
from dataclasses import dataclass, field

from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer
from wireguard_py.interface import WireGuardInterface

import time

@dataclass
class InterfaceConfig:
    key: WireguardKey
    public_endpoint: Endpoint
    private_endpoint: Endpoint

@dataclass
class InterfaceConfigList:
    config: List[InterfaceConfig] = field(default_factory=list)

interface_config_list = InterfaceConfigList()

def create(
    network: IPv4Network | IPv6Network,
    ip_address: Optional[IPv4Address | IPv6Address],
    public_ip: Optional[IPv4Address | IPv6Address],
    fabric_port: int
):
    # This is a Server Node
    node_1_key = WireguardKey.generate()
    node_1_endpoint = Endpoint(ip=ip_address, port=40261)

    wg0 = WireGuardInterface(
        "wg-1101", 
        endpoint=node_1_endpoint,
        ip=node_1_endpoint.ip,
        cidr=network,
        keypair=node_1_key,
    )
    interface_config_list.config.append(
        InterfaceConfig(
            key = node_1_key,
            public_endpoint = node_1_endpoint()
        )
    )

    if wg0.status:
        wg0.bring_down()

    wg0.bring_up()
    print("\nTunnel is Up ...")

    while True:
        time.sleep(3)
    
    wg0.bring_down()
    print("\nTunnel is Down ...")