import time
from fastapi import FastAPI
from wire_fabric.cli import app
from wireguard_py.peers import Endpoint
from wire_fabric.daemon.server.state import DistributedState
from wire_fabric.daemon.server.apiserver import FabricAPIServer 

if __name__ == "__main__":
    app()
