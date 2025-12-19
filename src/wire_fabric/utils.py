import ipaddress
import socket
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from pydantic import BaseModel, Field
from pyroute2.netlink.rtnl import rt_proto, rt_scope
from wireguard_py.interface import WireGuardInterface
from wire_fabric.daemon.server.model import RouteDefinition

def interface_to_dict(interface: WireGuardInterface):
    return {
        "name": interface.name,
        "ip": interface.ip,
        "peers": list(interface.peers.keys()),
        "cidr": interface.cidr,
        "status": interface.status,
        "endpoint": interface.endpoint,
        "public_key": str(interface.keypair.public_key()),
        "private_key": str(interface.keypair.private_key()),
    }

    # endpoint: Endpoint | None
    # private_key : WireguardKey | None # Private Key
    # public_key : WireguardKey | None # Public Key

def validate_interface_name(name, ipr):

    if not name:
        name = f"wf"
    interface_names = ipr.interface_names()

    unique_name = name
    num = 1

    while unique_name in interface_names:
        unique_name = f"{name}_{num}"
        num += 1

    return unique_name

def route_to_model(route, interfaces):
    attrs = dict(route['attrs'])

    dst = attrs.get('RTA_DST')
    src = attrs.get('RTA_PREFSRC')
    gateway = attrs.get('RTA_GATEWAY')
    oif = route.get('oif')
    is_default = dst is None and route.get('dst_len', 0) == 0


    proto = rt_proto.get(route.get('proto'), str(route.get('proto')))
    scope = rt_scope.get(route.get('scope'), str(route.get('scope')))
    is_link = route.get('scope') == rt_scope['link']

    route_dict = {
        "src": ipaddress.ip_address(src) if src else None,
        "dst": (
            ipaddress.ip_network(f"{dst}/{route['dst_len']}", strict=False)
            if dst else
            ipaddress.ip_network("0.0.0.0/0")
        ),
        "gateway": ipaddress.ip_address(gateway) if gateway else None,
        "interface": interfaces.get(oif),
        "is_default": is_default,
        "proto": proto,
        "scope": scope,
        "is_link": is_link
    }
    return Route(**route_dict)