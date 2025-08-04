import typer
from pathlib import Path
import ipaddress
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from typing import Optional, List
from wire_fabric.cli.create import create

import time, httpx, json, base64
from fastapi import FastAPI
from wireguard_py.peers import Endpoint
from wire_fabric.daemon.server.state import DistributedState, WeightedEndpoint
from wire_fabric.daemon.server.apiserver import FabricAPIServer 
from wire_fabric.daemon.pyroute_worker import IPRouteWorker

app = typer.Typer(help="CLI for the Fabric Peer", no_args_is_help=True)
