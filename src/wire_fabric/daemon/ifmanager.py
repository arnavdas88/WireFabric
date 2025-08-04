import ipaddress
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from wireguard_py.interface import WireGuardInterface
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer

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