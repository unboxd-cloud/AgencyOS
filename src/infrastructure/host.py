"""Host management for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..client.cloudstack_client import CloudStackClient
from ..client.exceptions import ValidationException, InfrastructureException


logger = logging.getLogger(__name__)


@dataclass
class Host:
    """Represents a CloudStack host."""
    
    id: str
    name: str
    ip: str
    zone_id: str
    pod_id: str
    cluster_id: str
    hypervisor: str = "KVM"
    state: str = "Up"
    cpu_count: int = 0
    cpu_speed: int = 0
    cpu_total: int = 0
    memory_total: int = 0
    memory_used: int = 0
    cluster_name: str = ""
    host_type: str = "Routing"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Host":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            ip=data.get("ip", ""),
            zone_id=data.get("zoneid", ""),
            pod_id=data.get("podid", ""),
            cluster_id=data.get("clusterid", ""),
            hypervisor=data.get("hypervisor", "KVM"),
            state=data.get("state", "Up"),
            cpu_count=data.get("cpunumber", 0),
            cpu_speed=data.get("cpuspeed", 0),
            cpu_total=data.get("cputotal", 0),
            memory_total=data.get("memorytotal", 0),
            memory_used=data.get("memoryused", 0),
            cluster_name=data.get("clustername", ""),
            host_type=data.get("hosttype", "Routing"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "ip": self.ip,
            "zoneid": self.zone_id,
            "podid": self.pod_id,
            "clusterid": self.cluster_id,
            "hypervisor": self.hypervisor,
            "state": self.state,
            "cpunumber": self.cpu_count,
            "cpuspeed": self.cpu_speed,
            "cputotal": self.cpu_total,
            "memorytotal": self.memory_total,
            "memoryused": self.memory_used,
            "clustername": self.cluster_name,
            "hosttype": self.host_type,
        }
    
    @property
    def memory_available(self) -> int:
        return self.memory_total - self.memory_used
    
    @property
    def cpu_available(self) -> int:
        return self.cpu_total - (self.cpu_count * self.cpu_speed)
    
    def __repr__(self):
        return f"Host(id={self.id}, name={self.name}, ip={self.ip}, state={self.state})"


class HostManager:
    """Manages CloudStack hosts."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def add(
        self,
        zone_id: str,
        pod_id: str,
        cluster_id: str,
        host_name: str,
        password: str,
        hypervisor: str = "KVM",
        host_type: str = "Routing",
    ) -> Host:
        if not zone_id:
            raise ValidationException("Zone ID is required", field="zone_id")
        if not pod_id:
            raise ValidationException("Pod ID is required", field="pod_id")
        if not cluster_id:
            raise ValidationException("Cluster ID is required", field="cluster_id")
        if not host_name:
            raise ValidationException("Host name is required", field="host_name")
        if not password:
            raise ValidationException("Host password is required", field="password")
        
        logger.info(f"Adding host: {host_name}")
        
        response = self.client.add_host(
            zone_id=zone_id,
            pod_id=pod_id,
            cluster_id=cluster_id,
            host_name=host_name,
            password=password,
            hypervisor=hypervisor,
            host_type=host_type,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to add host",
                resource_type="host"
            )
        
        host_data = response.get_result("host", {})
        return Host.from_dict(host_data)
    
    def get(self, host_id: str) -> Optional[Host]:
        try:
            hosts = self.list(host_id=host_id)
            if hosts:
                return hosts[0]
        except Exception as e:
            logger.error(f"Failed to get host {host_id}: {e}")
        return None
    
    def list(
        self, 
        zone_id: Optional[str] = None,
        pod_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
        host_id: Optional[str] = None,
        type: Optional[str] = None,
    ) -> List[Host]:
        try:
            host_list = self.client.list_hosts(
                zone_id=zone_id,
                pod_id=pod_id,
                cluster_id=cluster_id,
                host_id=host_id,
                type=type,
            )
            return [Host.from_dict(h) for h in host_list]
        except Exception as e:
            logger.error(f"Failed to list hosts: {e}")
            return []
    
    def delete(self, host_id: str, force: bool = False) -> bool:
        logger.info(f"Deleting host: {host_id}")
        
        response = self.client.delete_host(host_id, force=force)
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to delete host",
                resource_type="host"
            )
        
        return True
    
    def enable(self, host_id: str) -> bool:
        """Enable a host."""
        try:
            response = self.client._make_request("GET", "enableHost", {"id": host_id})
            return response.is_success
        except Exception as e:
            logger.error(f"Failed to enable host {host_id}: {e}")
            return False
    
    def disable(self, host_id: str) -> bool:
        """Disable a host."""
        try:
            response = self.client._make_request("GET", "disableHost", {"id": host_id})
            return response.is_success
        except Exception as e:
            logger.error(f"Failed to disable host {host_id}: {e}")
            return False
    
    def get_capacity(self, host_id: str) -> Dict[str, Any]:
        """Get host capacity."""
        try:
            response = self.client._make_request(
                "GET", 
                "listHostCapacity",
                {"hostid": host_id}
            )
            return response.response_data.get("hostcapacity", {})
        except Exception as e:
            logger.error(f"Failed to get host capacity: {e}")
            return {}
    
    def __repr__(self):
        hosts = self.list()
        return f"HostManager(hosts={len(hosts)})"