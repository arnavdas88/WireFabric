import os, socket, json, ipaddress
from typing import List, Dict, Optional, Generator
from wireguard_py.keys import WireguardKey
from wireguard_py.peers import Endpoint, Peer
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import StrEnum

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if type(o) is bytes:
            return o.decode()
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
class NodeInformation:
    name: str
    management: Optional[WeightedEndpoint]
    data: Optional[WeightedEndpoint]
    vip: Optional[IPv4Address | IPv6Address]
    node_keys: Optional[WireguardKey]

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
        # print(incoming)
        # Merge network
        if self.network != ipaddress.ip_network(incoming.get("network")):
            # TODO: Need to define the behaviour for network change
            raise NotImplementedError()

        # Merge master nodes
        for name, endpoint in incoming.get("master_nodes", []).items():
            if name == self.name:
                # Skip its own information from rewriting
                continue
            candidate = WeightedEndpoint(**endpoint)
            if name not in self.master_nodes or candidate != self.master_nodes[name]:
                # Rewrite if the name doesnot exist or the data does not match
                self.master_nodes[name] = candidate

        # Merge management groups
        for name, endpoint in incoming.get("management", []).items():
            if name == self.name:
                # Skip its own information from rewriting
                continue
            candidate = WeightedEndpoint(**endpoint)
            if name not in self.management or candidate != self.management[name]:
                # Rewrite if the name doesnot exist or the data does not match
                self.management[name] = candidate

        # Merge keys
        for vip, wg_key in incoming.get("node_keys", {}).items():
            if vip == self.private_ip.ip:
                # Skip its own information from rewriting
                continue
            if vip not in self.node_keys or self.node_keys[vip] != WireguardKey(**wg_key):
                # print(f"{type(wg_key) = }, {wg_key}")
                self.node_keys[vip] = WireguardKey(**wg_key)

    def get_by_node_name(self, name) -> NodeInformation:
        vip = None
        wg_key = None
        master_node = self.master_nodes.get(name)
        management_node = self.management.get(name)

        if management_node and master_node.ip:
            vip = master_node.ip
            wg_key = self.node_keys.get(vip) or self.node_keys.get(str(vip))
        
        return NodeInformation(
            name=name,
            management=management_node,
            data=master_node,
            vip=vip,
            node_keys=wg_key,
        )

    def get_by_vip(self, ip: IPv4Address | IPv6Address):
        # TODO: Validate for if vip in self.network
        for node_name, node_endpoint in self.master_nodes.items():
            if ip == node_endpoint.ip:
                return self.get_by_node_name(node_name)
        raise Exception(f"Virtual IP Address `{ip}` do not exist.")
    
    def get_other_operational_masters(self, ) -> List[NodeInformation]:
        nodes = list(self.master_nodes.items())
        sorted_nodes = sorted(nodes, key = lambda x:(x[1].weight, x[0]))
        sorted_node_names = [ node_name for node_name, node_attributes in sorted_nodes ]
        for node_name in sorted_node_names:
            yield self.get_by_node_name(node_name)