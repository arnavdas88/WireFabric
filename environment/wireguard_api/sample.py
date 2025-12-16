import httpx
import socket
from ipaddress import IPv4Address, IPv4Network

HOSTS = ['172.30.30.101', '172.30.30.102', '172.30.30.103']
HOSTNAME = socket.gethostname()
CIDR = IPv4Network("10.10.10.0/24")

for host, private_ip in zip(HOSTS, CIDR.hosts()):
    # Create wireguard interface
    with httpx.Client(timeout=3) as client:
        response = client.post(
            f"http://{host}:8000/interfaces", 
            json = {
                "name": "string",
                "ip": private_ip,
                "cidr": str(CIDR),
                "listen_port": 45531,
                "private_key": "string"
            }
        )
        status = response.json()

    # Verify wireguard interface
    with httpx.Client(timeout=3) as client:
        response = client.get(f"http://{host}:8000/interfaces")
        status = response.json()



MASTER = HOSTS[0:1]
PEER = HOSTS[1:]

for host in PEER:
    for master in MASTER:
        # Add host to master
        # Add master to host
        pass



