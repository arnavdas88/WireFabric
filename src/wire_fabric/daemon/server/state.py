import os, socket, json, ipaddress
from typing import List, Dict, Optional
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer
from ipaddress import IPv4Network, IPv6Network
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import StrEnum

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        else:
            return str(o)
        return super().default(o)


class ServerStatus(StrEnum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"

@dataclass
class WeightedEndpoint(Endpoint):
    weight: int = -1

@dataclass(frozen=True)
class Node(WireguardKey):
    name: str = field(default_factory=socket.gethostname)

@dataclass
class DistributedState:
    # Static Variables
    network: IPv4Network | IPv6Network
    name: str = field(default_factory=socket.gethostname)
    status: ServerStatus = ServerStatus.INACTIVE
    private_ip: Optional[Endpoint] = None

    # Distributed Variables
    management: Dict[str, WeightedEndpoint] = field(default_factory=dict)
    master_nodes: Dict[str, WeightedEndpoint] = field(default_factory=dict)
    node_keys: Dict[str, WireguardKey] = field(default_factory=dict)  # key is str(Endpoint or IP)

    def to_dict(self):
        return asdict(self)
        # result['network'] = str(result['network'])
        # result['node_keys'] = {key:{'keydata': value['keydata'].decode()} for key, value in result['node_keys'].items()}
        
    def to_json(self,):
        return json.dumps(asdict(self), cls=EnhancedJSONEncoder, sort_keys=True)

    def merge(self, incoming: Dict):
        # Merge network
        if self.network != ipaddress.ip_network(incoming.get("network")):
            # TODO: Need to define the behaviour for network change
            raise NotImplementedError()

        # Merge master nodes
        for name, endpoint in incoming.get("master_nodes", []).items():
            candidate = WeightedEndpoint(**endpoint)
            if name not in self.master_nodes or candidate != self.master_nodes[name]:
                self.master_nodes[name] = candidate

        # Merge management groups
        for name, endpoint in incoming.get("management", []).items():
            candidate = WeightedEndpoint(**endpoint)
            if name not in self.management or candidate != self.management[name]:
                self.management[name] = candidate

        # Merge keys
        for k, v in incoming.get("node_keys", {}).items():
            if k not in self.node_keys:
                self.node_keys[k] = WireguardKey(**v)
