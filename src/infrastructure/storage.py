"""Storage management for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..client.cloudstack_client import CloudStackClient
from ..client.exceptions import ValidationException, InfrastructureException


logger = logging.getLogger(__name__)


@dataclass
class StoragePool:
    """Represents a CloudStack storage pool."""
    
    id: str
    name: str
    zone_id: str
    pool_type: str
    path: str
    server: str
    port: int = 0
    cluster_id: Optional[str] = None
    state: str = "Up"
    size_total: int = 0
    size_used: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoragePool":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            zone_id=data.get("zoneid", ""),
            pool_type=data.get("type", ""),
            path=data.get("path", ""),
            server=data.get("server", ""),
            port=data.get("port", 0),
            cluster_id=data.get("clusterid"),
            state=data.get("state", "Up"),
            size_total=data.get("disksizetotal", 0),
            size_used=data.get("disksizeused", 0),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "zoneid": self.zone_id,
            "type": self.pool_type,
            "path": self.path,
            "server": self.server,
            "port": self.port,
            "clusterid": self.cluster_id,
            "state": self.state,
            "disksizetotal": self.size_total,
            "disksizeused": self.size_used,
        }
    
    @property
    def size_available(self) -> int:
        return self.size_total - self.size_used
    
    def __repr__(self):
        return f"StoragePool(id={self.id}, name={self.name}, type={self.pool_type})"


class StorageManager:
    """Manages CloudStack storage pools."""
    
    def __init__(self, client: CloudStackClient):
        self.client = client
    
    def add_primary_storage(
        self,
        name: str,
        zone_id: str,
        pool_type: str,
        path: str,
        cluster_id: Optional[str] = None,
    ) -> StoragePool:
        if not name:
            raise ValidationException("Storage name is required", field="name")
        if not zone_id:
            raise ValidationException("Zone ID is required", field="zone_id")
        if not pool_type:
            raise ValidationException("Pool type is required", field="pool_type")
        if not path:
            raise ValidationException("Path is required", field="path")
        
        logger.info(f"Adding primary storage: {name}")
        
        response = self.client.add_primary_storage(
            name=name,
            zone_id=zone_id,
            pool_type=pool_type,
            path=path,
            cluster_id=cluster_id,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to add primary storage",
                resource_type="storage"
            )
        
        pool_data = response.get_result("storagepool", {})
        return StoragePool.from_dict(pool_data)
    
    def add_secondary_storage(
        self,
        zone_id: str,
        nfs_server: str,
        path: str,
    ) -> bool:
        if not zone_id:
            raise ValidationException("Zone ID is required", field="zone_id")
        if not nfs_server:
            raise ValidationException("NFS server is required", field="nfs_server")
        if not path:
            raise ValidationException("Mount path is required", field="path")
        
        logger.info(f"Adding secondary storage to zone {zone_id}")
        
        response = self.client.add_secondary_storage(
            zone_id=zone_id,
            nfs_server=nfs_server,
            path=path,
        )
        
        if not response.is_success:
            raise InfrastructureException(
                message=response.error_text or "Failed to add secondary storage",
                resource_type="storage"
            )
        
        return True
    
    def list_primary_storage(
        self, 
        zone_id: Optional[str] = None,
        storage_id: Optional[str] = None,
    ) -> List[StoragePool]:
        try:
            pool_list = self.client.list_primary_storage(
                zone_id=zone_id,
                storage_id=storage_id,
            )
            return [StoragePool.from_dict(p) for p in pool_list]
        except Exception as e:
            logger.error(f"Failed to list storage pools: {e}")
            return []
    
    def get(self, storage_id: str) -> Optional[StoragePool]:
        try:
            pools = self.list_primary_storage(storage_id=storage_id)
            if pools:
                return pools[0]
        except Exception as e:
            logger.error(f"Failed to get storage pool {storage_id}: {e}")
        return None
    
    def delete(self, storage_id: str) -> bool:
        logger.info(f"Deleting storage pool: {storage_id}")
        
        try:
            response = self.client._make_request("GET", "deleteStoragePool", {"id": storage_id})
            if response.is_success:
                return True
            raise InfrastructureException(
                message=response.error_text or "Failed to delete storage pool",
                resource_type="storage"
            )
        except Exception as e:
            logger.error(f"Failed to delete storage pool: {e}")
            return False
    
    def __repr__(self):
        pools = self.list_primary_storage()
        return f"StorageManager(storage_pools={len(pools)})"