
from typing import Dict, List
from fastapi import HTTPException, Depends

from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer
from wireguard_py.interface import WireGuardInterface

from wire_fabric.daemon.server.auth import require_role
from wire_fabric.daemon.server.base import APIServer
from wire_fabric.daemon.server.model import InterfaceRequest, PeerRequest, RouteDefinition, WireGuardInterfaceDefination
from wire_fabric.utils import validate_interface_name, route_to_model


class FabricAPIServer(APIServer):

    def register(self, ):
        self.app.get("/")(self.index)
        
        # Interface
        self.app.get("/interfaces", dependencies=[Depends(require_role("admin", "operator", "viewer"))], response_model=List[WireGuardInterfaceDefination])(self.get_interfaces)
        self.app.post("/interfaces", dependencies=[Depends(require_role("admin"))])(self.create_interface)
        self.app.get("/interfaces/{name}", dependencies=[Depends(require_role("admin", "operator", "viewer"))])(self.retrieve_interface)
        self.app.delete("/interfaces/{name}", dependencies=[Depends(require_role("admin"))])(self.delete_interface)
        
        self.app.post("/interfaces/{name}/peers", dependencies=[Depends(require_role("admin", "operator"))])(self.add_peer)
        self.app.delete("/interfaces/{name}/peers/{peer_name}", dependencies=[Depends(require_role("admin", "operator"))])(self.remove_peer)

        # Route
        self.app.get("/routes", dependencies=[Depends(require_role("admin"))], response_model=List[RouteDefinition])(self.get_routes)


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

        return {
            "name": wg.name,
            "status": wg.status,
            "peers": list(wg.peers.keys())
        }

    def delete_interface(self, name: str):
        wg = self.interfaces.get(name)
        if not wg:
            raise HTTPException(404, "Interface not found")

        wg.bring_down()
        return {"status": "down", "interface": name}

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


