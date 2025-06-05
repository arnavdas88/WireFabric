import asyncio
import ipaddress
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
import json
import base64
import hashlib
import hmac

import pyroute2
import wireguard_py
from wireguard_py.wireguard_common import Endpoint
from wireguard_py.contrib.WireguardKey import WireguardKey
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship
from pydantic import BaseModel
import uvicorn

# Database Models
class VirtualNetwork(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    interface_name: str = Field(unique=True)
    subnet: str  # CIDR notation
    port: int
    private_key: str
    public_key: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Relationships
    routes: List["Route"] = Relationship(back_populates="virtual_network")
    client_networks: List["ClientVirtualNetwork"] = Relationship(back_populates="virtual_network")

class Route(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    virtual_network_id: int = Field(foreign_key="virtualnetwork.id")
    destination: str  # CIDR notation
    description: Optional[str] = None
    priority: int = Field(default=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    virtual_network: Optional[VirtualNetwork] = Relationship(back_populates="routes")

class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unique_id: str = Field(unique=True, index=True)
    api_key: str
    name: str
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    client_networks: List["ClientVirtualNetwork"] = Relationship(back_populates="client")

class NetworkPolicy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    rules: str  # JSON string containing policy rules
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    client_networks: List["ClientVirtualNetwork"] = Relationship(back_populates="network_policy")

class ClientVirtualNetwork(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    virtual_network_id: int = Field(foreign_key="virtualnetwork.id")
    network_policy_id: Optional[int] = Field(foreign_key="networkpolicy.id", default=None)
    client_private_key: str
    client_public_key: str
    assigned_ip: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    client: Optional[Client] = Relationship(back_populates="client_networks")
    virtual_network: Optional[VirtualNetwork] = Relationship(back_populates="client_networks")
    network_policy: Optional[NetworkPolicy] = Relationship(back_populates="client_networks")

class ClientHealth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    virtual_network_id: int = Field(foreign_key="virtualnetwork.id")
    status: str  # connected, disconnected, error
    rx_bytes: int = Field(default=0)
    tx_bytes: int = Field(default=0)
    last_handshake: Optional[datetime] = None
    endpoint: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Pydantic Models for API
class VirtualNetworkCreate(BaseModel):
    name: str
    subnet: str
    port: int
    description: Optional[str] = None

class VirtualNetworkResponse(BaseModel):
    id: int
    name: str
    interface_name: str
    subnet: str
    port: int
    public_key: str
    description: Optional[str]
    is_active: bool
    routes: List[Dict]

class RouteCreate(BaseModel):
    destination: str
    description: Optional[str] = None
    priority: int = 100

class RouteResponse(BaseModel):
    id: int
    destination: str
    description: Optional[str]
    priority: int
    is_active: bool

class ClientCreate(BaseModel):
    name: str
    description: Optional[str] = None
    virtual_network_ids: List[int]
    network_policy_id: Optional[int] = None

class ClientResponse(BaseModel):
    id: int
    unique_id: str
    name: str
    description: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    networks: List[Dict]

class NetworkPolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules: Dict[str, Any]

class ClientConfigResponse(BaseModel):
    virtual_networks: List[Dict]
    routes: List[Dict]
    policies: List[Dict]

# Database setup
DATABASE_URL = "sqlite:///./wireguard_server.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# Security
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # In production, implement proper API key validation
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return token

# WireGuard Management Class
class WireGuardManager:
    def __init__(self):
        self.ipr = pyroute2.IPRoute()
        self.active_interfaces: Dict[str, Dict] = {}
    
    def generate_keypair(self):
        """Generate WireGuard key pair"""
        key_pair = WireguardKey.generate()
        private_key = key_pair.keydata
        public_key = key_pair.public_key().keydata
        # return base64.b64encode(private_key).decode(), base64.b64encode(public_key).decode()
        return private_key, public_key
    
    async def create_interface(self, interface_name: str, subnet: str, port: int, private_key: str):
        """Create and configure WireGuard interface"""
        try:
            # Create interface
            async with pyroute2.AsyncIPRoute() as ipr:
                await ipr.link("add", ifname=interface_name, kind="wireguard")
                wg_ifc = await ipr.link_lookup(ifname=interface_name)[0]
                
                # Assign IP
                network = ipaddress.ip_network(subnet)
                interface_ip = str(list(network.hosts())[0])
                await ipr.addr("add", index=wg_ifc, address=interface_ip, prefixlen=network.prefixlen)
                await ipr.link("set", index=wg_ifc, state="up")
            
            # Configure WireGuard
            priv_key_bytes = base64.b64decode(private_key)
            wireguard_py.set_device(
                device_name=interface_name.encode(),
                priv_key=priv_key_bytes,
                port=port,
            )
            
            self.active_interfaces[interface_name] = {
                "subnet": subnet,
                "port": port,
                "interface_ip": interface_ip
            }
            
            return True
        except Exception as e:
            print(f"Error creating interface {interface_name}: {e}")
            return False
    
    def add_peer(self, interface_name: str, public_key: str, allowed_ips: List[str], endpoint: Optional[str] = None):
        """Add peer to WireGuard interface"""
        try:
            pub_key_bytes = base64.b64decode(public_key)
            allowed_networks = [ipaddress.ip_network(ip) for ip in allowed_ips]
            
            endpoint_obj = None
            if endpoint:
                ip, port = endpoint.split(":")
                endpoint_obj = Endpoint(ip=ipaddress.ip_address(ip), port=int(port))
            
            wireguard_py.set_peer(
                device_name=interface_name.encode(),
                pub_key=pub_key_bytes,
                endpoint=endpoint_obj,
                allowed_ips=set(allowed_networks),
                replace_allowed_ips=True,
            )
            return True
        except Exception as e:
            print(f"Error adding peer to {interface_name}: {e}")
            return False
    
    def remove_peer(self, interface_name: str, public_key: str):
        """Remove peer from WireGuard interface"""
        try:
            pub_key_bytes = base64.b64decode(public_key)
            wireguard_py.remove_peer(
                device_name=interface_name.encode(),
                pub_key=pub_key_bytes
            )
            return True
        except Exception as e:
            print(f"Error removing peer from {interface_name}: {e}")
            return False
    
    def interface_exists(self, interface_name: str) -> bool:
        """Check if WireGuard interface exists"""
        try:
            self.ipr.link_lookup(ifname=interface_name)
            return True
        except:
            return False
    
    def delete_interface(self, interface_name: str):
        """Delete WireGuard interface"""
        try:
            if self.interface_exists(interface_name):
                wg_ifc = self.ipr.link_lookup(ifname=interface_name)[0]
                self.ipr.link("del", index=wg_ifc)
                if interface_name in self.active_interfaces:
                    del self.active_interfaces[interface_name]
                return True
        except Exception as e:
            print(f"Error deleting interface {interface_name}: {e}")
        return False

# FastAPI App
app = FastAPI(title="WireGuard Management Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
wg_manager = WireGuardManager()
active_connections: Dict[str, WebSocket] = {}

async def restore_wireguard_from_database():
    """Restore WireGuard interfaces and peers from database on startup"""
    print("🔄 Restoring WireGuard configuration from database...")
    
    with Session(engine) as session:
        try:
            # Get all active virtual networks
            virtual_networks = session.exec(
                select(VirtualNetwork).where(VirtualNetwork.is_active == True)
            ).all()
            
            if not virtual_networks:
                print("📋 No virtual networks found in database")
                return
            
            print(f"🔍 Found {len(virtual_networks)} virtual networks to restore")
            
            for vnet in virtual_networks:
                print(f"⚙️  Restoring virtual network: {vnet.name} ({vnet.interface_name})")
                
                # Clean up existing interface if it exists
                if wg_manager.interface_exists(vnet.interface_name):
                    print(f"🧹 Cleaning up existing interface: {vnet.interface_name}")
                    wg_manager.delete_interface(vnet.interface_name)
                    import time
                    time.sleep(1)  # Brief pause to ensure cleanup
                
                # Restore WireGuard interface
                success = await wg_manager.create_interface(
                    vnet.interface_name,
                    vnet.subnet,
                    vnet.port,
                    vnet.private_key
                )
                
                if not success:
                    print(f"❌ Failed to restore interface: {vnet.interface_name}")
                    continue
                
                print(f"✅ Interface restored: {vnet.interface_name} (Port: {vnet.port}, Subnet: {vnet.subnet})")
                
                # Restore peers (active client connections)
                client_networks = session.exec(
                    select(ClientVirtualNetwork, Client)
                    .join(Client)
                    .where(
                        ClientVirtualNetwork.virtual_network_id == vnet.id,
                        ClientVirtualNetwork.is_active == True,
                        Client.is_active == True
                    )
                ).all()
                
                print(f"👥 Found {len(client_networks)} clients to restore for {vnet.name}")
                
                for cn in client_networks:
                    client_net = cn.ClientVirtualNetwork
                    client = cn.Client
                    
                    # Add peer to WireGuard interface
                    peer_success = wg_manager.add_peer(
                        vnet.interface_name,
                        client_net.client_public_key,
                        [f"{client_net.assigned_ip}/32"]
                    )
                    
                    if peer_success:
                        print(f"  ✅ Restored peer: {client.name} ({client_net.assigned_ip})")
                    else:
                        print(f"  ❌ Failed to restore peer: {client.name} ({client_net.assigned_ip})")
                
                # Get and display current interface stats
                try:
                    stats = wg_manager.get_interface_stats(vnet.interface_name)
                    print(f"📊 Interface {vnet.interface_name} now has {len(stats)} active peers")
                except Exception as e:
                    print(f"⚠️  Could not get stats for {vnet.interface_name}: {e}")
            
            print("🎉 WireGuard restoration completed!")
            
            # Display summary
            total_interfaces = len([iface for iface in wg_manager.active_interfaces.keys()])
            print(f"📈 Summary: {total_interfaces} active interfaces restored")
            
        except Exception as e:
            print(f"💥 Error during WireGuard restoration: {e}")
            import traceback
            traceback.print_exc()

# Helper functions
def generate_client_credentials():
    """Generate unique client ID and API key"""
    unique_id = str(uuid.uuid4())
    api_key = secrets.token_urlsafe(32)
    return unique_id, api_key

def get_next_available_ip(subnet: str, session: Session, virtual_network_id: int) -> str:
    """Get next available IP in subnet for client"""
    network = ipaddress.ip_network(subnet)
    hosts = list(network.hosts())
    
    # Get assigned IPs
    assigned_ips = session.exec(
        select(ClientVirtualNetwork.assigned_ip)
        .where(ClientVirtualNetwork.virtual_network_id == virtual_network_id)
    ).all()
    
    assigned_addresses = {ipaddress.ip_address(ip) for ip in assigned_ips}
    
    # Find first available IP (skip network IP)
    for host in hosts[1:]:  # Skip first IP (usually gateway)
        if host not in assigned_addresses:
            return str(host)
    
    raise ValueError("No available IPs in subnet")

# API Routes

@app.on_event("startup")
async def startup():
    create_db_and_tables()
    await restore_wireguard_from_database()

# Virtual Network Management
@app.post("/api/v1/virtual-networks", response_model=VirtualNetworkResponse)
async def create_virtual_network(
    network_data: VirtualNetworkCreate,
    session: Session = Depends(get_session)
):
    """Create a new virtual network"""
    # Generate keypair
    private_key, public_key = wg_manager.generate_keypair()
    
    # Generate interface name
    interface_name = f"wg-{network_data.name.lower().replace(' ', '-')}"
    
    # Create database entry
    virtual_network = VirtualNetwork(
        name=network_data.name,
        interface_name=interface_name,
        subnet=network_data.subnet,
        port=network_data.port,
        private_key=private_key,
        public_key=public_key,
        description=network_data.description
    )
    
    session.add(virtual_network)
    session.commit()
    session.refresh(virtual_network)
    
    # Create WireGuard interface
    if await wg_manager.create_interface(interface_name, network_data.subnet, network_data.port, private_key):
        return VirtualNetworkResponse(
            id=virtual_network.id,
            name=virtual_network.name,
            interface_name=virtual_network.interface_name,
            subnet=virtual_network.subnet,
            port=virtual_network.port,
            public_key=virtual_network.public_key,
            description=virtual_network.description,
            is_active=virtual_network.is_active,
            routes=[]
        )
    else:
        session.delete(virtual_network)
        session.commit()
        raise HTTPException(status_code=400, detail="Failed to create WireGuard interface")

@app.get("/api/v1/virtual-networks", response_model=List[VirtualNetworkResponse])
async def list_virtual_networks(session: Session = Depends(get_session)):
    """List all virtual networks"""
    networks = session.exec(select(VirtualNetwork)).all()
    result = []
    
    for network in networks:
        routes = session.exec(
            select(Route).where(Route.virtual_network_id == network.id)
        ).all()
        
        result.append(VirtualNetworkResponse(
            id=network.id,
            name=network.name,
            interface_name=network.interface_name,
            subnet=network.subnet,
            port=network.port,
            public_key=network.public_key,
            description=network.description,
            is_active=network.is_active,
            routes=[{
                "id": route.id,
                "destination": route.destination,
                "description": route.description,
                "priority": route.priority,
                "is_active": route.is_active
            } for route in routes]
        ))
    
    return result

@app.get("/api/v1/virtual-networks/{network_id}", response_model=VirtualNetworkResponse)
async def get_virtual_network(network_id: int, session: Session = Depends(get_session)):
    """Get specific virtual network"""
    network = session.get(VirtualNetwork, network_id)
    if not network:
        raise HTTPException(status_code=404, detail="Virtual network not found")
    
    routes = session.exec(
        select(Route).where(Route.virtual_network_id == network_id)
    ).all()
    
    return VirtualNetworkResponse(
        id=network.id,
        name=network.name,
        interface_name=network.interface_name,
        subnet=network.subnet,
        port=network.port,
        public_key=network.public_key,
        description=network.description,
        is_active=network.is_active,
        routes=[{
            "id": route.id,
            "destination": route.destination,
            "description": route.description,
            "priority": route.priority,
            "is_active": route.is_active
        } for route in routes]
    )

@app.delete("/api/v1/virtual-networks/{network_id}")
async def delete_virtual_network(network_id: int, session: Session = Depends(get_session)):
    """Delete virtual network and clean up WireGuard interface"""
    network = session.get(VirtualNetwork, network_id)
    if not network:
        raise HTTPException(status_code=404, detail="Virtual network not found")
    
    # Remove all peers first
    client_networks = session.exec(
        select(ClientVirtualNetwork).where(ClientVirtualNetwork.virtual_network_id == network_id)
    ).all()
    
    for client_net in client_networks:
        wg_manager.remove_peer(network.interface_name, client_net.client_public_key)
    
    # Delete WireGuard interface
    wg_manager.delete_interface(network.interface_name)
    
    # Delete from database (cascade will handle related records)
    session.delete(network)
    session.commit()
    
    return {"message": f"Virtual network {network.name} deleted successfully"}

@app.post("/api/v1/virtual-networks/{network_id}/restart")
async def restart_virtual_network(network_id: int, session: Session = Depends(get_session)):
    """Restart a virtual network (recreate interface and restore peers)"""
    network = session.get(VirtualNetwork, network_id)
    if not network:
        raise HTTPException(status_code=404, detail="Virtual network not found")
    
    # Delete existing interface
    wg_manager.delete_interface(network.interface_name)
    
    # Recreate interface
    success = await wg_manager.create_interface(
        network.interface_name,
        network.subnet,
        network.port,
        network.private_key
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to recreate interface")
    
    # Restore all active peers
    client_networks = session.exec(
        select(ClientVirtualNetwork, Client)
        .join(Client)
        .where(
            ClientVirtualNetwork.virtual_network_id == network_id,
            ClientVirtualNetwork.is_active == True,
            Client.is_active == True
        )
    ).all()
    
    restored_peers = 0
    for cn in client_networks:
        client_net = cn.ClientVirtualNetwork
        if wg_manager.add_peer(
            network.interface_name,
            client_net.client_public_key,
            [f"{client_net.assigned_ip}/32"]
        ):
            restored_peers += 1
    
    return {
        "message": f"Virtual network {network.name} restarted successfully",
        "restored_peers": restored_peers
    }
@app.post("/api/v1/virtual-networks/{network_id}/routes", response_model=RouteResponse)
async def create_route(
    network_id: int,
    route_data: RouteCreate,
    session: Session = Depends(get_session)
):
    """Add route to virtual network"""
    network = session.get(VirtualNetwork, network_id)
    if not network:
        raise HTTPException(status_code=404, detail="Virtual network not found")
    
    route = Route(
        virtual_network_id=network_id,
        destination=route_data.destination,
        description=route_data.description,
        priority=route_data.priority
    )
    
    session.add(route)
    session.commit()
    session.refresh(route)
    
    return RouteResponse(
        id=route.id,
        destination=route.destination,
        description=route.description,
        priority=route.priority,
        is_active=route.is_active
    )

@app.get("/api/v1/virtual-networks/{network_id}/routes", response_model=List[RouteResponse])
async def list_routes(network_id: int, session: Session = Depends(get_session)):
    """List routes for virtual network"""
    routes = session.exec(
        select(Route).where(Route.virtual_network_id == network_id)
    ).all()
    
    return [RouteResponse(
        id=route.id,
        destination=route.destination,
        description=route.description,
        priority=route.priority,
        is_active=route.is_active
    ) for route in routes]

# Network Policy Management
@app.post("/api/v1/network-policies")
async def create_network_policy(
    policy_data: NetworkPolicyCreate,
    session: Session = Depends(get_session)
):
    """Create network policy"""
    policy = NetworkPolicy(
        name=policy_data.name,
        description=policy_data.description,
        rules=json.dumps(policy_data.rules)
    )
    
    session.add(policy)
    session.commit()
    session.refresh(policy)
    
    return {"id": policy.id, "name": policy.name, "description": policy.description}

@app.get("/api/v1/network-policies")
async def list_network_policies(session: Session = Depends(get_session)):
    """List all network policies"""
    policies = session.exec(select(NetworkPolicy)).all()
    return [{"id": p.id, "name": p.name, "description": p.description, "rules": json.loads(p.rules)} for p in policies]

# Client Management
@app.post("/api/v1/clients", response_model=ClientResponse)
async def create_client(
    client_data: ClientCreate,
    session: Session = Depends(get_session)
):
    """Create new client and assign to virtual networks"""
    unique_id, api_key = generate_client_credentials()
    
    # Create client
    client = Client(
        unique_id=unique_id,
        api_key=api_key,
        name=client_data.name,
        description=client_data.description
    )
    
    session.add(client)
    session.commit()
    session.refresh(client)
    
    # Assign to virtual networks
    networks = []
    for network_id in client_data.virtual_network_ids:
        network = session.get(VirtualNetwork, network_id)
        if not network:
            continue
        
        # Generate client keypair
        client_private_key, client_public_key = wg_manager.generate_keypair()
        
        # Get available IP
        assigned_ip = get_next_available_ip(network.subnet, session, network_id)
        
        # Create client-network association
        client_network = ClientVirtualNetwork(
            client_id=client.id,
            virtual_network_id=network_id,
            network_policy_id=client_data.network_policy_id,
            client_private_key=client_private_key,
            client_public_key=client_public_key,
            assigned_ip=assigned_ip
        )
        
        session.add(client_network)
        
        # Add peer to WireGuard interface
        wg_manager.add_peer(
            network.interface_name,
            client_public_key,
            [f"{assigned_ip}/32"]
        )
        
        networks.append({
            "network_id": network_id,
            "network_name": network.name,
            "assigned_ip": assigned_ip,
            "subnet": network.subnet
        })
    
    session.commit()
    
    return ClientResponse(
        id=client.id,
        unique_id=client.unique_id,
        name=client.name,
        description=client.description,
        is_active=client.is_active,
        last_seen=client.last_seen,
        networks=networks
    )

@app.get("/api/v1/clients", response_model=List[ClientResponse])
async def list_clients(session: Session = Depends(get_session)):
    """List all clients"""
    clients = session.exec(select(Client)).all()
    result = []
    
    for client in clients:
        client_networks = session.exec(
            select(ClientVirtualNetwork, VirtualNetwork)
            .join(VirtualNetwork)
            .where(ClientVirtualNetwork.client_id == client.id)
        ).all()
        
        networks = [{
            "network_id": cn.ClientVirtualNetwork.virtual_network_id,
            "network_name": cn.VirtualNetwork.name,
            "assigned_ip": cn.ClientVirtualNetwork.assigned_ip,
            "subnet": cn.VirtualNetwork.subnet
        } for cn in client_networks]
        
        result.append(ClientResponse(
            id=client.id,
            unique_id=client.unique_id,
            name=client.name,
            description=client.description,
            is_active=client.is_active,
            last_seen=client.last_seen,
            networks=networks
        ))
    
    return result

@app.delete("/api/v1/clients/{client_id}")
async def delete_client(client_id: int, session: Session = Depends(get_session)):
    """Delete client and remove from all WireGuard interfaces"""
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Remove from all WireGuard interfaces
    client_networks = session.exec(
        select(ClientVirtualNetwork, VirtualNetwork)
        .join(VirtualNetwork)
        .where(ClientVirtualNetwork.client_id == client_id)
    ).all()
    
    for cn in client_networks:
        client_net = cn.ClientVirtualNetwork
        vnet = cn.VirtualNetwork
        wg_manager.remove_peer(vnet.interface_name, client_net.client_public_key)
    
    # Close WebSocket connection if active
    if client.unique_id in active_connections:
        try:
            await active_connections[client.unique_id].close()
            del active_connections[client.unique_id]
        except:
            pass
    
    # Delete from database (cascade will handle related records)
    session.delete(client)
    session.commit()
    
    return {"message": f"Client {client.name} deleted successfully"}

@app.post("/api/v1/clients/{client_id}/reconnect")
async def reconnect_client(client_id: int, session: Session = Depends(get_session)):
    """Force client to reconnect and refresh configuration"""
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Send reconnect command via WebSocket if client is connected
    if client.unique_id in active_connections:
        try:
            await active_connections[client.unique_id].send_json({
                "type": "reconnect",
                "message": "Server requested reconnection"
            })
            return {"message": f"Reconnect command sent to {client.name}"}
        except:
            return {"message": f"Client {client.name} is not currently connected"}
    else:
        return {"message": f"Client {client.name} is not currently connected"}

@app.get("/api/v1/system/interfaces")
async def list_system_interfaces():
    """List all active WireGuard interfaces on the system"""
    interfaces = []
    
    for interface_name, config in wg_manager.active_interfaces.items():
        try:
            stats = wg_manager.get_interface_stats(interface_name)
            interfaces.append({
                "name": interface_name,
                "subnet": config["subnet"],
                "port": config["port"],
                "interface_ip": config["interface_ip"],
                "peer_count": len(stats),
                "peers": [
                    {
                        "public_key": base64.b64encode(peer.public_key).decode() if hasattr(peer, 'public_key') else "unknown",
                        "endpoint": str(peer.endpoint) if hasattr(peer, 'endpoint') and peer.endpoint else None,
                        "last_handshake": peer.last_handshake.isoformat() if hasattr(peer, 'last_handshake') and peer.last_handshake else None,
                        "rx_bytes": getattr(peer, 'rx_bytes', 0),
                        "tx_bytes": getattr(peer, 'tx_bytes', 0)
                    } for peer in stats
                ]
            })
        except Exception as e:
            interfaces.append({
                "name": interface_name,
                "subnet": config["subnet"],
                "port": config["port"],
                "interface_ip": config["interface_ip"],
                "error": str(e)
            })
    
    return {
        "interfaces": interfaces,
        "total_count": len(interfaces)
    }
@app.get("/api/v1/client/{unique_id}/config", response_model=ClientConfigResponse)
async def get_client_config(unique_id: str, session: Session = Depends(get_session)):
    """Get client configuration"""
    client = session.exec(select(Client).where(Client.unique_id == unique_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get client's virtual networks
    client_networks = session.exec(
        select(ClientVirtualNetwork, VirtualNetwork, NetworkPolicy)
        .join(VirtualNetwork)
        .join(NetworkPolicy, isouter=True)
        .where(ClientVirtualNetwork.client_id == client.id)
    ).all()
    
    virtual_networks = []
    routes = []
    policies = []
    
    for cn in client_networks:
        client_net = cn.ClientVirtualNetwork
        vnet = cn.VirtualNetwork
        policy = cn.NetworkPolicy
        
        # Get server endpoint (this should be configurable)
        server_endpoint = f"YOUR_SERVER_IP:{vnet.port}"
        
        virtual_networks.append({
            "id": vnet.id,
            "name": vnet.name,
            "interface_name": f"wg-client-{vnet.id}",
            "client_private_key": client_net.client_private_key,
            "server_public_key": vnet.public_key,
            "server_endpoint": server_endpoint,
            "assigned_ip": client_net.assigned_ip,
            "subnet": vnet.subnet
        })
        
        # Get routes for this virtual network
        network_routes = session.exec(
            select(Route).where(
                Route.virtual_network_id == vnet.id,
                Route.is_active == True
            )
        ).all()
        
        for route in network_routes:
            routes.append({
                "virtual_network_id": vnet.id,
                "destination": route.destination,
                "priority": route.priority,
                "interface_name": f"wg-client-{vnet.id}"
            })
        
        # Add policy if exists
        if policy:
            policies.append({
                "virtual_network_id": vnet.id,
                "name": policy.name,
                "rules": json.loads(policy.rules)
            })
    
    return ClientConfigResponse(
        virtual_networks=virtual_networks,
        routes=routes,
        policies=policies
    )

# WebSocket endpoint for client communication
@app.websocket("/ws/client/{unique_id}")
async def websocket_endpoint(websocket: WebSocket, unique_id: str):
    await websocket.accept()
    active_connections[unique_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "health_update":
                await handle_health_update(unique_id, data.get("data", {}))
            elif data.get("type") == "config_request":
                config = await get_client_config_ws(unique_id)
                await websocket.send_json({
                    "type": "config_update",
                    "data": config
                })
            
            # Echo confirmation
            await websocket.send_json({"type": "ack", "message": "received"})
            
    except WebSocketDisconnect:
        if unique_id in active_connections:
            del active_connections[unique_id]

async def handle_health_update(unique_id: str, health_data: Dict):
    """Handle health update from client"""
    with Session(engine) as session:
        client = session.exec(select(Client).where(Client.unique_id == unique_id)).first()
        if not client:
            return
        
        # Update client last seen
        client.last_seen = datetime.utcnow()
        session.add(client)
        
        # Store health data for each virtual network
        for network_health in health_data.get("networks", []):
            health_record = ClientHealth(
                client_id=client.id,
                virtual_network_id=network_health.get("virtual_network_id"),
                status=network_health.get("status", "unknown"),
                rx_bytes=network_health.get("rx_bytes", 0),
                tx_bytes=network_health.get("tx_bytes", 0),
                last_handshake=datetime.fromisoformat(network_health["last_handshake"]) if network_health.get("last_handshake") else None,
                endpoint=network_health.get("endpoint")
            )
            session.add(health_record)
        
        session.commit()

async def get_client_config_ws(unique_id: str) -> Dict:
    """Get client configuration for WebSocket"""
    with Session(engine) as session:
        client = session.exec(select(Client).where(Client.unique_id == unique_id)).first()
        if not client:
            return {}
        
        # Same logic as HTTP endpoint but return dict
        client_networks = session.exec(
            select(ClientVirtualNetwork, VirtualNetwork, NetworkPolicy)
            .join(VirtualNetwork)
            .join(NetworkPolicy, isouter=True)
            .where(ClientVirtualNetwork.client_id == client.id)
        ).all()
        
        virtual_networks = []
        routes = []
        policies = []
        
        for cn in client_networks:
            client_net = cn.ClientVirtualNetwork
            vnet = cn.VirtualNetwork
            policy = cn.NetworkPolicy
            
            server_endpoint = f"YOUR_SERVER_IP:{vnet.port}"
            
            virtual_networks.append({
                "id": vnet.id,
                "name": vnet.name,
                "interface_name": f"wg-client-{vnet.id}",
                "client_private_key": client_net.client_private_key,
                "server_public_key": vnet.public_key,
                "server_endpoint": server_endpoint,
                "assigned_ip": client_net.assigned_ip,
                "subnet": vnet.subnet
            })
            
            network_routes = session.exec(
                select(Route).where(
                    Route.virtual_network_id == vnet.id,
                    Route.is_active == True
                )
            ).all()
            
            for route in network_routes:
                routes.append({
                    "virtual_network_id": vnet.id,
                    "destination": route.destination,
                    "priority": route.priority,
                    "interface_name": f"wg-client-{vnet.id}"
                })
            
            if policy:
                policies.append({
                    "virtual_network_id": vnet.id,
                    "name": policy.name,
                    "rules": json.loads(policy.rules)
                })
        
        return {
            "virtual_networks": virtual_networks,
            "routes": routes,
            "policies": policies
        }

# Health and Statistics
@app.get("/api/v1/health")
async def get_system_health():
    """Get system health and statistics"""
    with Session(engine) as session:
        total_clients = session.exec(select(Client)).all()
        active_clients = [c for c in total_clients if c.last_seen and c.last_seen > datetime.utcnow() - timedelta(minutes=5)]
        total_networks = session.exec(select(VirtualNetwork)).all()
        
        return {
            "total_clients": len(total_clients),
            "active_clients": len(active_clients),
            "total_virtual_networks": len(total_networks),
            "active_connections": len(active_connections),
            "server_time": datetime.utcnow().isoformat()
        }

@app.get("/api/v1/clients/{client_id}/health")
async def get_client_health(client_id: int, session: Session = Depends(get_session)):
    """Get client health statistics"""
    health_records = session.exec(
        select(ClientHealth)
        .where(ClientHealth.client_id == client_id)
        .order_by(ClientHealth.timestamp.desc())
        .limit(10)
    ).all()
    
    return [
        {
            "virtual_network_id": h.virtual_network_id,
            "status": h.status,
            "rx_bytes": h.rx_bytes,
            "tx_bytes": h.tx_bytes,
            "last_handshake": h.last_handshake.isoformat() if h.last_handshake else None,
            "endpoint": h.endpoint,
            "timestamp": h.timestamp.isoformat()
        }
        for h in health_records
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)