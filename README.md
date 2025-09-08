# WireFabric – WireGuard Fabric Management Tool

**WireFabric** is a Python-based tool that simplifies the management of a WireGuard VPN for Linux systems. It includes both a **client command-line interface** and a **Web API** for easy administration.

---

## 🚀 Features

### Client - Control Plane CLI

Assuming one of the manage server is running on `xxx.xxx.xxx.xxx:yyyy`, 

Show information of the cluster and nodes
```sh
$ python -m wire_fabric client info --host xxx.xxx.xxx.xxx --port yyyy

Name :  ...
Status :  Active / Inactive
Network :  10.0.0.0/24
Total master servers :  3
        alice
        bob
        ...
Total management servers :  3
        alice
        bob
        ...
Total nodes :  3
        10.0.0.1
        10.0.0.2
        ...
```


---

## 📦 Requirements & Setup

For Client CLI Setup, run
```sh
python -m pip install -e . --break-system-packages
```

> [!NOTE]
> For Management and Peer nodes, follow the steps in the Dockerfile [`environment/wireguard_fabric/Dockerfile`](environment/wireguard_fabric/Dockerfile)


## ⚙️ Fast Setup and Testing

For setting up testing environment, we use docker for our network orchestration. Refer to [`environment/wireguard_fabric/Walkthorugh.md`](environment/wireguard_fabric/Walkthorugh.md)

