from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from wireguard_py.interface import WireGuardInterface
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer

import time


def main():
    # THIS IS NODE 1
    network = IPv4Network("10.10.10.0/24")
    node_1_key = WireguardKey("yO+XDIp4FP7jqjTJkYQuN6VI+r9heqoUjVSVvoGwf3w=")
    node_2_key = WireguardKey("kCZHwpflKBj6tSyHkeoqlnC/31NRtgBpRUjw1u/w81Q=")
    node_1_endpoint = Endpoint(ip=IPv4Address("10.10.10.1"), port=40261)
    node_2_endpoint = Endpoint(ip=IPv4Address("10.10.10.2"), port=40262)

    wg0 = WireGuardInterface(
        "wg-1101", 
        endpoint=node_1_endpoint, # 10.10.10.1:40261
        ip=node_1_endpoint.ip,    # 10.10.10.1
        cidr=network,
        keypair=node_1_key,
        peers={
            "p1": Peer(
                interface=node_2_endpoint,  # 10.10.10.2:40262
                allowed_ips=[ network ],
                # privkey=str(node_2_key.private_key()), # Not Compulsory
                pubkey=str(node_2_key.public_key()), 
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