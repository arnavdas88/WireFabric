import asyncio
import uvicorn
from threading import Thread

from typing import List, Mapping, Optional, Dict
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fastapi import FastAPI

from wire_fabric.daemon.ifmanager import InterfaceManager
from wireguard_py.interface import WireGuardInterface
from wire_fabric.daemon.pyroute_worker import IPRouteWorker

class APIServer:
    def __init__(self, 
        app: FastAPI,
        host:str, port:int,
        ifacemanager: InterfaceManager,
        ipyrouteworker: IPRouteWorker
    ):
        self.app = app
        self.ipr = ipyrouteworker

        self.host = host
        self.port = port
        self.interfaces: InterfaceManager = ifacemanager
        
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[Thread] = None
        self._running = False

        self.register()

    def register(self, ):
        raise NotImplementedError()

    def __call__(self, ):
        pass

    def up(self):
        if self._running:
            print("[APIServer] Already running.")
            return

        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
        self._server = uvicorn.Server(config)

        def _run():
            self._running = True
            asyncio.run(self._server.serve()) # pyright: ignore[reportOptionalMemberAccess]
            self._running = False

        self._thread = Thread(target=_run, daemon=True)
        self._thread.start()
        print("[APIServer] Started.")

    def down(self):
        if self._server and self._running:
            print("[APIServer] Stopping...")
            self._server.should_exit = True
            self._thread.join(timeout=5) # pyright: ignore[reportOptionalMemberAccess]
            self._running = False
            print("[APIServer] Stopped.")

