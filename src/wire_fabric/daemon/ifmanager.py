from typing import Dict
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from wireguard_py.interface import WireGuardInterface
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer

from wire_fabric.utils import interface_to_dict

class InterfaceManager:
    def __init__(self):
        self.active_interfaces: Dict[str, WireGuardInterface] = {}
    
    def get(self, name):
        return self.active_interfaces.get(name)

    def list(self, ):
        return [ interface_to_dict(wireguard_interface) for wireguard_interface in self.active_interfaces.values() ]

    def create(self, interface: WireGuardInterface):
        self.active_interfaces[interface.name] = interface
        if interface.status:
            interface.bring_down()
        interface.bring_up()

    def up(self, interface_name: str):
        self.active_interfaces[interface_name].bring_up()

    def down(self, interface_name: str):
        self.active_interfaces[interface_name].bring_down()

    def remove(self, interface_name: str):
        if self.active_interfaces[interface_name].status:
            self.active_interfaces[interface_name].bring_down()
        del self.active_interfaces[interface_name]

    def add_peers(self, interface_name: str, peer: Peer):
        self.active_interfaces[interface_name].bring_down()
        self.active_interfaces[interface_name].add_peer(peer)
        self.active_interfaces[interface_name].bring_up()

    def restart(self, interface_name: str):
        self.active_interfaces[interface_name].bring_down()
        self.active_interfaces[interface_name].bring_up()