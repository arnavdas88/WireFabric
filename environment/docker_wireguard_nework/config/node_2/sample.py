from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from wireguard_py.pythonic import WireGuardInterface
from wireguard_py.contrib.WireguardKey import WireguardKey
from wireguard_py.wireguard_common import Endpoint, Peer

import time


def main():
    # THIS IS NODE 2
    network = IPv4Network("10.10.10.0/24")
    node_1_key = WireguardKey("yO+XDIp4FP7jqjTJkYQuN6VI+r9heqoUjVSVvoGwf3w=")
    node_2_key = WireguardKey("kCZHwpflKBj6tSyHkeoqlnC/31NRtgBpRUjw1u/w81Q=")
    node_1_endpoint = Endpoint(ip=IPv4Address("172.30.30.2"), port=40261)
    node_2_endpoint = Endpoint(ip=IPv4Address("10.10.10.2"), port=40262)

    wg0 = WireGuardInterface(
        "wg-1101", 
        endpoint=node_2_endpoint,
        ip=node_2_endpoint.ip,
        cidr=network,
        keypair=node_2_key,
        peers={
            "p1": Peer(
                interface=node_1_endpoint,
                allowed_ips=[ network ],
                privkey=str(node_1_key.private_key()), # Not Compulsory
                pubkey=str(node_1_key.public_key()), 
            )
        }
    )

    if wg0.status:
        wg0.bring_down()

    wg0.bring_up()
    print("\nTunnel is Up ...")

    while True:
        time.sleep(3)
    
    wg0.bring_down()
    print("\nTunnel is Down ...")


if __name__ == "__main__":
    main()