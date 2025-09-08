from pydantic import BaseModel
from enum import StrEnum
from typing import List, Mapping, Optional
from wireguard_py.keys import WireguardKey
from wire_fabric.daemon.server.state import ServerStatus

# --- Pydantic for Input Validation ---

class EndpointModel(BaseModel):
    ip: Optional[str]
    port: int

class KeyModel(BaseModel):
    private: str
    public: Optional[str] = None

class WireguardKeyModel(BaseModel):
    keydata: str

class RegisterKeyModel(BaseModel):
    identifier: str  # str(ip) or str(endpoint)
    key: KeyModel

class SharedStateModel(BaseModel):
    # Static Variables
    network: str
    name: str
    status: ServerStatus
    private_ip: Optional[EndpointModel]

    master_nodes: Mapping[str, EndpointModel]
    management: Mapping[str, EndpointModel]
    node_keys: Mapping[str, WireguardKeyModel]

class Actions(StrEnum):
    START = "Start"
    STOP = "Stop"
    RESTART = "Restart"

class ManagementModel(BaseModel):
    action: Actions