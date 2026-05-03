"""Cluster management for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..client.cloudstack_client import CloudStackClient
from ..client.exceptions import ValidationException, InfrastructureException


logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """Represents a CloudStack cluster."""
    
    id: str
    name: str
    zone_id: str
    pod_id: str
    cluster_type: str = "KVM"
    hypervisor: str = "KVM"
    vsm_ip: Optional[str] = None
    vsm_state: Optional[str] = None
    allocation_state: str = "Enabled"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cluster":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            zone_id=data.get("zoneid", ""),
            pod_id=data.get("podid", ""),
            cluster_type=data.get("clustertype", "KVM"),
            hypervisor=data.get("hypervisor", "KVM"),
            vsm_ip=data.get("vsmipaddress"),
            vsm_state=data.get("vsmstate"),
            allocation_state=data.get("allocationstate", "Enabled"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "zoneid": self.zone_id,
            "podid": self.pod_id,
            "clustertype": self.cluster_type,
            "hypervisor": self.hypervisor,
            "vsmipaddress": self.vsm_ip,
            "vsmstate": self.vsm_state,
            "allocationstate": self.allocation_state,
        }
    
    def __repr__(self):
        return f"Cluster(id={self.id}, name={self.name}, hypervisor={self.hypervisor})"


class ClusterManager:
    """Manages CloudStack clusters."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def create(
        self,
        name: str,
        zone_id: str,
        pod_id: str,
        cluster_type: str = "KVM",
        hypervisor: str = "KVM",
        vsm_ip: Optional[str] = None,
    ) -> Cluster:
        if not name:
            raise ValidationException("Cluster name is required", field="name")
        if not zone_id:
            raise ValidationException("Zone ID is required", field="zone_id")
        if not pod_id:
            raise ValidationException("Pod ID is required", field="pod_id")
        
        logger.info(f"Creating cluster: {name}")
        
        response = self.client.create_cluster(
            name=name,
            zone_id=zone_id,
            pod_id=pod_id,
            cluster_type=cluster_type,
            hypervisor=hypervisor,
            vsm_ip=vsm_ip,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to create cluster",
                resource_type="cluster"
            )
        
        cluster_data = response.get_result("cluster", {})
        return Cluster.from_dict(cluster_data)
    
    def get(self, cluster_id: str) -> Optional[Cluster]:
        try:
            clusters = self.list(cluster_id=cluster_id)
            if clusters:
                return clusters[0]
        except Exception as e:
            logger.error(f"Failed to get cluster {cluster_id}: {e}")
        return None
    
    def list(
        self, 
        zone_id: Optional[str] = None,
        pod_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
    ) -> List[Cluster]:
        try:
            cluster_list = self.client.list_clusters(
                zone_id=zone_id,
                pod_id=pod_id,
                cluster_id=cluster_id,
            )
            return [Cluster.from_dict(c) for c in cluster_list]
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            return []
    
    def delete(self, cluster_id: str) -> bool:
        logger.info(f"Deleting cluster: {cluster_id}")
        
        response = self.client.delete_cluster(cluster_id)
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to delete cluster",
                resource_type="cluster"
            )
        
        return True
    
    def __repr__(self):
        clusters = self.list()
        return f"ClusterManager(clusters={len(clusters)})"