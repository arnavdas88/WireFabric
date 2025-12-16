import socket
from wireguard_py.interface import WireGuardInterface

def interface_to_dict(interface: WireGuardInterface):
    return {
        "name": interface.name,
        "ip": interface.ip,
        "peers": list(interface.peers.keys()),
        "cidr": interface.cidr,
        "status": interface.status,
        "public_key": str(interface.keypair.public_key())
    }

def validate_interface_name(name, ipr):
    raise NotImplementedError()
    if not name:
        name = f"wf_{socket.gethostname()}"
    interface_names = ipr.interface_names()
    pass
    