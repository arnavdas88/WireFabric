import os
import time
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from icmplib import ping

from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer
from wireguard_py.interface import WireGuardInterface

from pyroute2 import IPRoute

ipr = IPRoute()

def get_current_route(ipr, subnet="172.20.0.0/24"):
    routes = ipr.route("get", dst="172.20.0.1")

    for route in routes:
        oif = route.get("attrs", [])

        interface_index = None
        for attr, value in oif:
            if attr == "RTA_OIF":
                interface_index = value
                break

        if interface_index:
            return ipr.get_links(interface_index)[0].get_attr("IFLA_IFNAME")

    return None

def main():
    # THIS IS FOR NODE 1-2
    network_a = IPv4Network("10.10.10.0/24")
    # THIS IS FOR NODE 1-3
    network_b = IPv4Network("10.10.20.0/24")

    node_1_key = WireguardKey("yO+XDIp4FP7jqjTJkYQuN6VI+r9heqoUjVSVvoGwf3w=")
    node_2_key = WireguardKey("kCZHwpflKBj6tSyHkeoqlnC/31NRtgBpRUjw1u/w81Q=")
    node_3_key = WireguardKey("kCZHwpflKBj6tSyHkeoqlnC/31NRtgBpRUjw1u/w81Q=")
    
    node_1_endpoint_a = Endpoint(ip=IPv4Address("10.10.10.1"), port=40261)
    node_2_endpoint = Endpoint(ip=IPv4Address("10.10.10.2"), port=40262)
    
    node_1_endpoint_b = Endpoint(ip=IPv4Address("10.10.20.1"), port=40361)
    node_3_endpoint = Endpoint(ip=IPv4Address("10.10.20.2"), port=40262)

    wg0 = WireGuardInterface(
        "wg-1101", 
        endpoint=node_1_endpoint_a, # 10.10.10.1:40261
        ip=node_1_endpoint_a.ip,    # 10.10.10.1
        cidr=network_a,
        keypair=node_1_key,
        peers={
            "p1": Peer(
                interface=node_2_endpoint,  # 10.10.10.2:40262
                allowed_ips=[ network_a, IPv4Network("172.20.0.0/24") ],
                # privkey=str(node_2_key.private_key()), # Not Compulsory
                pubkey=str(node_2_key.public_key()), 
            ),
        }
    )



    wg1 = WireGuardInterface(
        "wg-1102", 
        endpoint=node_1_endpoint_b, # 10.10.20.1:40361
        ip=node_1_endpoint_b.ip,    # 10.10.20.1
        cidr=network_b,
        keypair=node_1_key,
        peers={
            "p1": Peer(
                interface=node_3_endpoint,  # 10.10.20.2:40262
                allowed_ips=[ network_b, IPv4Network("172.20.0.0/24") ],
                # privkey=str(node_3_key.private_key()), # Not Compulsory
                pubkey=str(node_3_key.public_key()), 
            )
        }
    )


    if wg0.status:
        wg0.bring_down()

    if wg1.status:
        wg1.bring_down()

    wg0.bring_up()
    wg1.bring_up()
    print("\nTunnel is Up ...")

    host = ping('10.10.10.2', count=5, timeout=3, privileged=False)
    if host.is_alive:
        print(f'Host `10.10.10.2` is up! Response time: {host.avg_rtt} ms')

    host = ping('10.10.20.2', count=5, timeout=3, privileged=False)
    if host.is_alive:
        print(f'Host `10.10.20.2` is up! Response time: {host.avg_rtt} ms')

    while True:
        time.sleep(3)
        host_a = ping('10.10.10.2', count=3, timeout=1, privileged=False)
        host_b = ping('10.10.20.2', count=3, timeout=1, privileged=False)
        current_route = get_current_route(ipr)
        print(f"Current Route : {current_route}")

        if host_a.is_alive:
            if current_route != "wg-1101":
                print("Gateway 1 wg-1101")
                os.system("ip route del 172.20.0.0/24")
                os.system("ip route add 172.20.0.0/24 dev wg-1101 src 10.10.10.1")
        elif host_b.is_alive:
            if current_route != "wg-1102":
                print("Gateway 2 wg-1102")
                os.system("ip route del 172.20.0.0/24")
                os.system("ip route add 172.20.0.0/24 dev wg-1102 src 10.10.20.1")
        else:
            print("No Gateway is Up!")
            break

    
    wg0.bring_down()
    wg1.bring_down()
    print("\nTunnel is Down ...")


if __name__ == "__main__":
    main()