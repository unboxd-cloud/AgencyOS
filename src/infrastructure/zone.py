"""Zone management for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..client.cloudstack_client import CloudStackClient
from ..client.api_response import CloudStackResponse
from ..client.exceptions import ValidationException, InfrastructureException


logger = logging.getLogger(__name__)


@dataclass
class NetworkType:
    """Network type enumeration."""
    BASIC = "Basic"
    ADVANCED = "Advanced"


@dataclass
class Zone:
    """Represents a CloudStack zone."""
    
    id: str
    name: str
    dns1: str
    dns2: Optional[str] = None
    internaldns1: str
    internaldns2: Optional[str] = None
    network_type: str = "Basic"
    domain: Optional[str] = None
    domain_id: Optional[str] = None
    guest_cidr: Optional[str] = None
    local_storage_enabled: bool = False
    security_group_enabled: bool = False
    allocation_state: str = "Enabled"
    tags: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Zone":
        """Create Zone from API response dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            dns1=data.get("dns1", ""),
            dns2=data.get("dns2"),
            internaldns1=data.get("internaldns1", ""),
            internaldns2=data.get("internaldns2"),
            network_type=data.get("networktype", "Basic"),
            domain=data.get("domain"),
            domain_id=data.get("domainid"),
            guest_cidr=data.get("guestcidraddress"),
            local_storage_enabled=data.get("localstorageenabled", False),
            security_group_enabled=data.get("securitygroupenabled", False),
            allocation_state=data.get("allocationstate", "Enabled"),
            tags=data.get("tags", []),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "dns1": self.dns1,
            "dns2": self.dns2,
            "internaldns1": self.internaldns1,
            "internaldns2": self.internaldns2,
            "networktype": self.network_type,
            "domain": self.domain,
            "domainid": self.domain_id,
            "guestcidraddress": self.guest_cidr,
            "localstorageenabled": self.local_storage_enabled,
            "securitygroupenabled": self.security_group_enabled,
            "allocationstate": self.allocation_state,
            "tags": self.tags,
        }
    
    def __repr__(self) -> str:
        return f"Zone(id={self.id}, name={self.name}, network_type={self.network_type})"


class ZoneManager:
    """Manages CloudStack zones."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def create(
        self,
        name: str,
        dns1: str,
        internaldns1: str,
        network_type: str = "Basic",
        dns2: Optional[str] = None,
        dns3: Optional[str] = None,
        internaldns2: Optional[str] = None,
        domain: Optional[str] = None,
        domain_id: Optional[str] = None,
        guest_cidr: Optional[str] = None,
    ) -> Zone:
        """Create a new zone.
        
        Args:
            name: Zone name
            dns1: Primary DNS server
            internaldns1: Primary internal DNS server
            network_type: Network type (Basic or Advanced)
            dns2: Secondary DNS server (optional)
            dns3: Tertiary DNS server (optional)
            internaldns2: Secondary internal DNS server (optional)
            domain: Domain name (optional)
            domain_id: Domain ID (optional)
            guest_cidr: Guest network CIDR (optional)
            
        Returns:
            Created Zone object
            
        Raises:
            ValidationException: If validation fails
            InfrastructureException: If zone creation fails
        """
        # Validate inputs
        if not name:
            raise ValidationException("Zone name is required", field="name")
        if not dns1:
            raise ValidationException("Primary DNS is required", field="dns1")
        if not internaldns1:
            raise ValidationException("Primary internal DNS is required", field="internaldns1")
        if network_type not in ["Basic", "Advanced"]:
            raise ValidationException(f"Invalid network type: {network_type}", field="network_type")
        
        logger.info(f"Creating zone: {name}")
        
        response = self.client.create_zone(
            name=name,
            dns1=dns1,
            internaldns1=internaldns1,
            network_type=network_type,
            dns2=dns2,
            dns3=dns3,
            internaldns2=internaldns2,
            domain=domain,
            domainid=domain_id,
            guest_cidr=guest_cidr,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to create zone",
                resource_type="zone"
            )
        
        # Parse the response to get zone data
        zone_data = response.get_result("zone", {})
        if not zone_data:
            # Try to find zone in list
            zones = self.list()
            zone = next((z for z in zones if z.name == name), None)
            if zone:
                return zone
            raise InfrastructureException("Zone created but not found", resource_type="zone")
        
        return Zone.from_dict(zone_data)
    
    def get(self, zone_id: str) -> Optional[Zone]:
        """Get zone by ID.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            Zone object or None
        """
        try:
            zones = self.list(zone_id=zone_id)
            if zones:
                return zones[0]
        except Exception as e:
            logger.error(f"Failed to get zone {zone_id}: {e}")
        return None
    
    def list(
        self, 
        zone_id: Optional[str] = None,
        available: Optional[bool] = None,
    ) -> List[Zone]:
        """List zones.
        
        Args:
            zone_id: Zone ID filter (optional)
            available: Available filter (optional)
            
        Returns:
            List of Zone objects
        """
        try:
            zone_list = self.client.list_zones(zone_id=zone_id, available=available)
            return [Zone.from_dict(z) for z in zone_list]
        except Exception as e:
            logger.error(f"Failed to list zones: {e}")
            return []
    
    def update(
        self, 
        zone_id: str,
        name: Optional[str] = None,
        dns1: Optional[str] = None,
        dns2: Optional[str] = None,
    ) -> Zone:
        """Update a zone.
        
        Args:
            zone_id: Zone ID
            name: New name (optional)
            dns1: New primary DNS (optional)
            dns2: New secondary DNS (optional)
            
        Returns:
            Updated Zone object
        """
        logger.info(f"Updating zone: {zone_id}")
        
        response = self.client.update_zone(
            zone_id=zone_id,
            name=name,
            dns1=dns1,
            dns2=dns2,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to update zone",
                resource_type="zone"
            )
        
        zone_data = response.get_result("zone", {})
        return Zone.from_dict(zone_data)
    
    def delete(self, zone_id: str) -> bool:
        """Delete a zone.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting zone: {zone_id}")
        
        response = self.client.delete_zone(zone_id)
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to delete zone",
                resource_type="zone"
            )
        
        return True
    
    def enable(self, zone_id: str) -> bool:
        """Enable a zone.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            True if successful
        """
        return self.update(zone_id).allocation_state == "Enabled"
    
    def disable(self, zone_id: str) -> bool:
        """Disable a zone.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            True if successful
        """
        self.update(zone_id, name=self.get(zone_id).name)
        return self.get(zone_id).allocation_state == "Disabled"
    
    def get_statistics(self, zone_id: str) -> Dict[str, Any]:
        """Get zone statistics.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "zone_id": zone_id,
            "vm_count": 0,
            "cpu_total": 0,
            "memory_total": 0,
            "storage_total": 0,
            "hosts": 0,
        }
        
        # Get hosts in zone
        try:
            hosts = self.client.list_hosts(zone_id=zone_id)
            stats["hosts"] = len(hosts)
            
            for host in hosts:
                stats["cpu_total"] += host.get("cpunumber", 0) * host.get("cpuspeed", 0)
                stats["memory_total"] += host.get("memorytotal", 0)
        except Exception as e:
            logger.error(f"Failed to get zone statistics: {e}")
        
        return stats
    
    def __repr__(self) -> str:
        zones = self.list()
        return f"ZoneManager(zones={len(zones)})"