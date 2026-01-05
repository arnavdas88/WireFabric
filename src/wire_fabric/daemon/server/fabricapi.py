
from ipaddress import IPv6Address, IPv6Network
from typing import Dict, List
from fastapi import HTTPException, Depends

from pyroute2.netlink.rtnl import rt_scope, rt_proto

from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer
from wireguard_py.interface import WireGuardInterface

from wire_fabric.daemon.server.auth import require_role
from wire_fabric.daemon.server.base import APIServer
from wire_fabric.daemon.server.model import InterfaceRequest, PeerRequest, RouteDefinition, WireGuardInterfaceDefination
from wire_fabric.utils import validate_interface_name, route_to_model, interface_to_dict


class FabricAPIServer(APIServer):

    def register(self, ):
        self.app.get("/")(self.index)
        
        # Interface
        self.app.get("/interfaces", dependencies=[Depends(require_role("admin", "operator", "viewer"))], response_model=List[WireGuardInterfaceDefination])(self.get_interfaces)
        self.app.post("/interfaces", dependencies=[Depends(require_role("admin"))])(self.create_interface)
        self.app.get("/interfaces/{name}", dependencies=[Depends(require_role("admin", "operator", "viewer"))], response_model=WireGuardInterfaceDefination)(self.retrieve_interface)
        self.app.delete("/interfaces/{name}", dependencies=[Depends(require_role("admin"))])(self.delete_interface)
        
        self.app.post("/interfaces/{name}/peers", dependencies=[Depends(require_role("admin", "operator"))])(self.add_peer)
        self.app.delete("/interfaces/{name}/peers/{peer_name}", dependencies=[Depends(require_role("admin", "operator"))])(self.remove_peer)

        # Route
        self.app.get("/routes", dependencies=[Depends(require_role("admin"))], response_model=List[RouteDefinition])(self.get_routes)
        self.app.post("/routes", dependencies=[Depends(require_role("admin"))], response_model=RouteDefinition)(self.create_routes)


    # --- API Endpoints ---
    async def index(self, ):
        return {"message": "Hello World !"}
    
    # --- Interfaces ---
    def get_interfaces(self):
        return list(self.interfaces.list())

    def create_interface(self, req: InterfaceRequest):
        name = validate_interface_name(req.name, self.ipr)

        if req.private_key:
            key = WireguardKey(req.private_key)
        else:
            key = WireguardKey.generate()

        wg = WireGuardInterface(
            interface_name=name,
            endpoint=None,
            ip=req.ip,
            cidr=req.cidr,
            keypair=key,
            peers={},
            ipr=self.ipr
        )

        wg.bring_up()
        self.interfaces.create(wg)

        return {"status": "created", "interface": name}

    def retrieve_interface(self, name: str):
        wg = self.interfaces.get(name)
        if not wg:
            raise HTTPException(404, "Interface not found")

        return interface_to_dict(wg)

    def delete_interface(self, name: str, delete: bool):
        wg = self.interfaces.get(name)
        if not wg:
            raise HTTPException(404, "Interface not found")


        if delete:
            self.interfaces.remove(name)
        else:
            self.interfaces.down(name)

        return {"status": wg.status, "interface": name}

    # --- Peers ---
    def add_peer(self, name: str, req: PeerRequest):
        wg = self.interfaces.get(name)
        if not wg:
            raise HTTPException(404, "Interface not found")

        peer = Peer(
            interface=Endpoint(
                ip=req.endpoint_ip,
                port=req.endpoint_port
            ),
            allowed_ips=[req.allowed_cidr],
            pubkey=req.pubkey
        )
        self.interfaces.add_peers(name, peer)
        return {"status": "peer added", "peer": req.name}

    def remove_peer(self, name: str, peer_name: str):
        wg = self.interfaces.get(name)
        if not wg or peer_name not in wg.peers:
            raise HTTPException(404, "Peer not found")

        # TODO: Need to Implement the remove_peer function in WireguardInterface class in WireguardPy 
        # del wg.peers[peer_name]
        # wg.sync()

        # return {"status": "peer removed", "peer": peer_name}

        raise NotImplementedError()

    # --- Routes ---
    def get_routes(self, ):
        routes = self.ipr.get_routes()
        links = self.ipr.get_links()

        interfaces = {link['index']: link.get_attr('IFLA_IFNAME') for link in links}

        serialized_routes = []

        for route in routes:
            serialized_routes.append(route_to_model( route, interfaces))

        return serialized_routes

    def create_routes(self, route: RouteDefinition):
        
        # Resolve interface index
        links = self.ipr.link_lookup(ifname=route.interface)
        if not links:
            raise ValueError(f"Interface '{route.interface}' not found")
        ifindex = links[0]

        # Determine IP family
        if isinstance(route.dst, IPv6Network) or isinstance(route.gateway, IPv6Address):
            family = 10  # AF_INET6
        else:
            family = 2   # AF_INET

        # Base route attributes
        kwargs = {
            "family": family,
        }

        # Destination
        if route.dst:
            kwargs["dst"] = str(route.dst)

        # Preferred source
        if route.src:
            kwargs["src"] = str(route.src.network_address)

        # Gateway (skip for link routes)
        if route.gateway:
            kwargs["gateway"] = str(route.gateway)

        # Protocol
        if route.proto:
            kwargs["proto"] = rt_proto.get(route.proto, rt_proto["static"])

        # Scope
        if route.scope:
            kwargs["scope"] = rt_scope.get(route.scope, rt_scope["universe"])

        # Create route
        result = self.ipr.route("add", **kwargs)

        return route
