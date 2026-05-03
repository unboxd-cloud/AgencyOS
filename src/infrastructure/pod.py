"""Pod management for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..client.cloudstack_client import CloudStackClient
from ..client.exceptions import ValidationException, InfrastructureException


logger = logging.getLogger(__name__)


@dataclass
class Pod:
    """Represents a CloudStack pod."""
    
    id: str
    name: str
    zone_id: str
    gateway: str
    netmask: str
    start_ip: str
    end_ip: str
    cluster_id: Optional[str] = None
    allocation_state: str = "Enabled"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pod":
        """Create Pod from API response dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            zone_id=data.get("zoneid", ""),
            gateway=data.get("gateway", ""),
            netmask=data.get("netmask", ""),
            start_ip=data.get("startip", ""),
            end_ip=data.get("endip", ""),
            cluster_id=data.get("clusterid"),
            allocation_state=data.get("allocationstate", "Enabled"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "zoneid": self.zone_id,
            "gateway": self.gateway,
            "netmask": self.netmask,
            "startip": self.start_ip,
            "endip": self.end_ip,
            "clusterid": self.cluster_id,
            "allocationstate": self.allocation_state,
        }
    
    def __repr__(self) -> str:
        return f"Pod(id={self.id}, name={self.name}, zone_id={self.zone_id})"


class PodManager:
    """Manages CloudStack pods."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def create(
        self,
        name: str,
        zone_id: str,
        start_ip: str,
        end_ip: str,
        gateway: str,
        netmask: str,
        cluster_id: Optional[str] = None,
    ) -> Pod:
        """Create a new pod.
        
        Args:
            name: Pod name
            zone_id: Zone ID
            start_ip: Start IP range
            end_ip: End IP range
            gateway: Gateway
            netmask: Netmask
            cluster_id: Cluster ID (optional)
            
        Returns:
            Created Pod object
            
        Raises:
            ValidationException: If validation fails
            InfrastructureException: If pod creation fails
        """
        if not name:
            raise ValidationException("Pod name is required", field="name")
        if not zone_id:
            raise ValidationException("Zone ID is required", field="zone_id")
        if not start_ip or not end_ip:
            raise ValidationException("IP range is required")
        if not gateway or not netmask:
            raise ValidationException("Gateway and netmask are required")
        
        logger.info(f"Creating pod: {name} in zone {zone_id}")
        
        response = self.client.create_pod(
            name=name,
            zone_id=zone_id,
            start_ip=start_ip,
            end_ip=end_ip,
            gateway=gateway,
            netmask=netmask,
            cluster_id=cluster_id,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to create pod",
                resource_type="pod"
            )
        
        pod_data = response.get_result("pod", {})
        return Pod.from_dict(pod_data)
    
    def get(self, pod_id: str) -> Optional[Pod]:
        """Get pod by ID."""
        try:
            pods = self.list(pod_id=pod_id)
            if pods:
                return pods[0]
        except Exception as e:
            logger.error(f"Failed to get pod {pod_id}: {e}")
        return None
    
    def list(
        self, 
        zone_id: Optional[str] = None,
        pod_id: Optional[str] = None,
    ) -> List[Pod]:
        """List pods."""
        try:
            pod_list = self.client.list_pods(zone_id=zone_id, pod_id=pod_id)
            return [Pod.from_dict(p) for p in pod_list]
        except Exception as e:
            logger.error(f"Failed to list pods: {e}")
            return []
    
    def update(
        self, 
        pod_id: str,
        name: Optional[str] = None,
        start_ip: Optional[str] = None,
        end_ip: Optional[str] = None,
    ) -> Pod:
        """Update a pod."""
        logger.info(f"Updating pod: {pod_id}")
        
        response = self.client.update_pod(
            pod_id=pod_id,
            name=name,
            start_ip=start_ip,
            end_ip=end_ip,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to update pod",
                resource_type="pod"
            )
        
        pod_data = response.get_result("pod", {})
        return Pod.from_dict(pod_data)
    
    def delete(self, pod_id: str) -> bool:
        """Delete a pod."""
        logger.info(f"Deleting pod: {pod_id}")
        
        response = self.client.delete_pod(pod_id)
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to delete pod",
                resource_type="pod"
            )
        
        return True
    
    def __repr__(self) -> str:
        pods = self.list()
        return f"PodManager(pods={len(pods)})"