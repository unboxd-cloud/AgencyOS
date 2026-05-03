"""Network configuration for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..client.cloudstack_client import CloudStackClient
from ..client.exceptions import ValidationException, NetworkException


logger = logging.getLogger(__name__)


@dataclass
class PhysicalNetwork:
    """Represents a physical network in CloudStack."""
    
    id: str
    name: str
    zone_id: str
    isolation_method: str = "VLAN"
    broadcast_domain_range: Optional[Dict[str, int]] = None
    state: str = "Setup"
    tags: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhysicalNetwork":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            zone_id=data.get("zoneid", ""),
            isolation_method=data.get("isolationmethod", "VLAN"),
            broadcast_domain_range=data.get("broadcastdomainrange"),
            state=data.get("state", "Setup"),
            tags=data.get("tags", []),
        )
    
    def __repr__(self):
        return f"PhysicalNetwork(id={self.id}, name={self.name}, zone_id={self.zone_id})"


class PhysicalNetworkManager:
    """Manages physical networks."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def create(
        self,
        zone_id: str,
        name: str,
        isolation_method: str = "VLAN",
    ) -> PhysicalNetwork:
        """Create a physical network."""
        if not zone_id:
            raise ValidationException("Zone ID is required", field="zone_id")
        if not name:
            raise ValidationException("Network name is required", field="name")
        
        logger.info(f"Creating physical network: {name}")
        
        response = self.client.create_physical_network(
            zone_id=zone_id,
            name=name,
            isolation_method=isolation_method,
        )
        
        if not response.is_success:
            raise NetworkException(
                message=response.error_text or "Failed to create physical network",
            )
        
        network_data = response.get_result("physicalnetwork", {})
        return PhysicalNetwork.from_dict(network_data)
    
    def list(
        self, 
        zone_id: Optional[str] = None,
        network_id: Optional[str] = None,
    ) -> List[PhysicalNetwork]:
        try:
            networks = self.client.list_physical_networks(
                zone_id=zone_id,
                network_id=network_id,
            )
            return [PhysicalNetwork.from_dict(n) for n in networks]
        except Exception as e:
            logger.error(f"Failed to list physical networks: {e}")
            return []
    
    def __repr__(self):
        return f"PhysicalNetworkManager(networks={len(self.list())})"


@dataclass
class NetworkOffering:
    """Represents a network offering."""
    
    id: str
    name: str
    display_text: str
    guest_type: str
    isolation_method: str = "VLAN"
    supported_services: List[str] = field(default_factory=list)
    state: str = "Enabled"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkOffering":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            display_text=data.get("displaytext", ""),
            guest_type=data.get("guestiptype", ""),
            isolation_method=data.get("isolationmethod", "VLAN"),
            supported_services=data.get("supportedservices", []),
            state=data.get("state", "Enabled"),
        )
    
    def __repr__(self):
        return f"NetworkOffering(id={self.id}, name={self.name})"


class NetworkOfferingManager:
    """Manages network offerings."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def create(
        self,
        name: str,
        display_text: str,
        guest_type: str,
        supported_services: List[str],
        service_offering_id: str,
        isolation_method: str = "VLAN",
    ) -> NetworkOffering:
        if not name:
            raise ValidationException("Name is required", field="name")
        
        logger.info(f"Creating network offering: {name}")
        
        response = self.client.create_network_offering(
            name=name,
            display_text=display_text,
            guest_type=guest_type,
            supported_services=supported_services,
            service_offering_id=service_offering_id,
            isolation_method=isolation_method,
        )
        
        if not response.is_success:
            raise NetworkException(
                message=response.error_text or "Failed to create network offering",
            )
        
        data = response.get_result("networkoffering", {})
        return NetworkOffering.from_dict(data)
    
    def list(self, name: Optional[str] = None) -> List[NetworkOffering]:
        try:
            response = self.client._make_list_request(
                "listNetworkOfferings", 
                {"name": name} if name else {},
                "networkoffering"
            )
            return [NetworkOffering.from_dict(n) for n in response]
        except Exception as e:
            logger.error(f"Failed to list network offerings: {e}")
            return []
    
    def __repr__(self):
        return f"NetworkOfferingManager(offerings={len(self.list())})"


@dataclass
class VLAN:
    """Represents a VLAN."""
    
    id: str
    vlan_id: str
    network_name: str
    zone_id: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VLAN":
        return cls(
            id=data.get("id", ""),
            vlan_id=data.get("vlan", ""),
            network_name=data.get("networkname", ""),
            zone_id=data.get("zoneid", ""),
        )
    
    def __repr__(self):
        return f"VLAN(id={self.id}, vlan_id={self.vlan_id})"


class NetworkManager:
    """High-level network management."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
        self.physical = PhysicalNetworkManager(client)
        self.offerings = NetworkOfferingManager(client)
    
    def __repr__(self):
        return f"NetworkManager(physical={len(self.physical.list())}, offerings={len(self.offerings.list())})"