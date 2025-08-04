import ipaddress
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from wireguard_py.interface import WireGuardInterface
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer

import json, httpx

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from pydantic import BaseModel
from dataclasses import asdict
from typing import List, Mapping, Optional

from wire_fabric.daemon.ifmanager import InterfaceManager
from wire_fabric.daemon.server.state import DistributedState, ServerStatus, WeightedEndpoint
from wire_fabric.daemon.pyroute_worker import IPRouteWorker
from wire_fabric.daemon.server.model import EndpointModel, KeyModel, WireguardKeyModel, \
                                            RegisterKeyModel, \
                                            SharedStateModel, ManagementModel, Actions

import asyncio

import uvicorn
from threading import Thread


class APIServer:
    def __init__(self, 
        app: FastAPI,
        host:str, port:int,
        shared_state: DistributedState,
        public_management_endpoint: Endpoint,
        ipyrouteworker: IPRouteWorker
    ):
        self.app = app
        self.shared_state = shared_state
        self.public_management_endpoint = public_management_endpoint
        # if self.public_management_endpoint:
        #     self.shared_state.management.append(self.public_management_endpoint)
        self.ipr = ipyrouteworker


        self.host = host
        self.port = port
        self.iface = None
        # self._interface_manager = InterfaceManager()
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[Thread] = None
        self._running = False

        self.register()

    def register(self, ):
        raise NotImplementedError()

    def __call__(self, ):
        pass

    async def fetch_state(self, ep:Endpoint):
        url = f"http://{ep.ip}:{ep.port}/state"
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            print(f"[WARN] Failed to pull from {url}: {e}")
            raise e

    async def sync_with_all_management(self, ):
        """Pull state from all management nodes, and push only if state changes."""
        old_state_serialized = self.shared_state.to_json()
        received_state_serialized = self.shared_state.to_json()

        # PULL
        management_nodes = list(self.shared_state.management.keys()).copy()
        for name in management_nodes:
            ep = self.shared_state.management[name]
            if name == self.shared_state.name:
                # Skip when pulling from self
                continue
            url = f"http://{ep.ip}:{ep.port}/state"
            try:
                async with httpx.AsyncClient(timeout=3) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        received_state_serialized = resp.json()
                        received_state_serialized = json.dumps(received_state_serialized, sort_keys=True)
                        self.shared_state.merge(resp.json())
            except Exception as e:
                print(f"[WARN] Failed to pull from {url}: {e}")


        # PUSH
        new_state_serialized = self.shared_state.to_json()
        if old_state_serialized != new_state_serialized or received_state_serialized != new_state_serialized:
            print("[INFO] State changed after pulling — pushing to all management nodes.")
            for name, ep in self.shared_state.management.items():
                if name == self.shared_state.name:
                    # Skip when pushing to self
                    continue
                url = f"http://{ep.ip}:{ep.port}/state"
                try:
                    async with httpx.AsyncClient(timeout=3) as client:
                        resp = await client.post(url, json=json.loads(self.shared_state.to_json()))
                        if resp.status_code != 200:
                            print(resp.json())
                except Exception as e:
                    print(f"[WARN] Failed to push to {url}: {e}")
        else:
            print("[INFO] No state change — no push necessary.")

    def get_next_available_ip(self, used_pool:List[IPv4Address | IPv6Address]) -> IPv4Address | IPv6Address:
        for ip in self.shared_state.network.hosts():
            if ip not in used_pool:
                return ip

    def up(self):
        if self._running:
            print("[APIServer] Already running.")
            return

        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
        self._server = uvicorn.Server(config)

        def _run():
            self._running = True
            asyncio.run(self._server.serve())
            self._running = False

        self._thread = Thread(target=_run, daemon=True)
        self._thread.start()
        print("[APIServer] Started.")

    def down(self):
        if self._server and self._running:
            print("[APIServer] Stopping...")
            self._server.should_exit = True
            self._thread.join(timeout=5)
            self._running = False
            print("[APIServer] Stopped.")

class FabricAPIServer(APIServer):

    def register(self, ):
        self.app.get("/")(self.index)
        self.app.get("/state")(self.get_state)
        self.app.post("/state")(self.post_state)
        self.app.post("/register/master")(self.register_master)
        self.app.post("/register/management")(self.register_management)
        self.app.post("/register/key")(self.register_node_key)
        self.app.post("/manage")(self.manage)

    # --- API Endpoints ---
    async def index(self, ):
        return {"message": "Hello World !"}

    async def get_state(self, ):
        return self.shared_state.to_dict()

    async def post_state(self, state: SharedStateModel):
        try:
            self.shared_state.merge(state.dict())
            return {"status": "merged", "node_count": len(self.shared_state.node_keys)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid state data: {e}")

    async def register_master(self, ep: EndpointModel):
        endpoint = Endpoint(ep.ip, ep.port)
        endpoint_state = await self.fetch_state(endpoint)
        name = endpoint_state['name']
        if name not in self.shared_state.master_nodes or endpoint != self.shared_state.master_nodes[name]:
            self.shared_state.master_nodes[name] = WeightedEndpoint(**ep.dict())
        await self.sync_with_all_management()
        return {"status": "ok", "master_nodes": [asdict(ep) for ep in self.shared_state.master_nodes]}

    async def register_management(self, ep: EndpointModel):
        endpoint = Endpoint(ep.ip, ep.port)
        endpoint_state = await self.fetch_state(endpoint)
        name = endpoint_state['name']
        if name not in self.shared_state.management or endpoint != self.shared_state.management[name]:
            self.shared_state.management[name] = WeightedEndpoint(**ep.dict())
        await self.sync_with_all_management()
        return {"status": "ok", "endpoint": asdict(endpoint)}

    async def register_node_key(self, reg: RegisterKeyModel):
        if reg.key.public:
            assert WireguardKey(reg.key.public.encode()) == WireguardKey(reg.key.private.encode()).public_key()
        self.shared_state.node_keys[reg.identifier] = WireguardKey(reg.key.private.encode())

        await self.sync_with_all_management()
        return {"status": "ok"}
    
    async def manage(self, management: ManagementModel):
        # Start or stop Wireguard Server and change the state
        if management.action == Actions.START:
            # Allocate IP Address if not allocated before
            if not self.shared_state.private_ip.ip:
                # Get current pool of used ip address
                used_pool = [ipaddress.ip_address(ip) for ip in self.shared_state.node_keys.keys()]
                allocated_private_ip = self.get_next_available_ip(used_pool)
                self.shared_state.private_ip.ip = allocated_private_ip
            # Allocate Node Key if not allocated before
            if str(self.shared_state.private_ip.ip) not in self.shared_state.node_keys:
                self.shared_state.node_keys[str(allocated_private_ip)] = WireguardKey.generate() # WireguardKey(b"WireguardKey")

            # If wireguard interface already exists and is up
            if self.iface and self.iface.status:
                self.iface.bring_down()
            # Create wireguard interface
            self.iface = WireGuardInterface(
                interface_name = self.shared_state.name,
                cidr = self.shared_state.network,
                ip = self.shared_state.private_ip.ip, # Subnetwork Ip
                keypair=self.shared_state.node_keys[str(self.shared_state.private_ip.ip)],
                endpoint=Endpoint(
                    ip = None, # This will become the public ip address of the node.
                    port = self.shared_state.master_nodes[self.shared_state.name].port # Data Port
                ),
                ipr=self.ipr # IpRoute()
            )
            self.iface.bring_up()
            # Set status to active
            self.shared_state.status = ServerStatus.ACTIVE
        if management.action == Actions.STOP:
            # If wireguard interface already exists and is up
            if self.iface and self.iface.status:
                self.iface.bring_down()
            # Set status to inactive
            self.shared_state.status = ServerStatus.INACTIVE
        # self.shared_state.master_nodes
        await self.sync_with_all_management()
        return {"status": "ok"}

    
