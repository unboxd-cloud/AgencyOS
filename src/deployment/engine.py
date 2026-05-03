"""Deployment engine for Apache CloudStack hybrid cloud platform."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..client.cloudstack_client import CloudStackClient
from ..infrastructure import (
    InfrastructureManager,
    ZoneManager,
    PodManager,
    ClusterManager,
    HostManager,
    StorageManager,
)
from ..network import NetworkManager
from ..hybrid import HybridCloudManager
from ..monitoring import MonitoringService
from ..utils.config import (
    CloudStackConfig,
    RegionConfig,
    ZoneConfig,
    load_config,
)


logger = logging.getLogger(__name__)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    
    success: bool
    resource_type: str
    resource_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


class DeploymentEngine:
    """Deploys and manages CloudStack infrastructure.
    
    Provides automated deployment of zones, pods, clusters, hosts,
    and hybrid cloud connections.
    """
    
    def __init__(self, config: CloudStackConfig):
        self.config = config
        
        # Create CloudStack client
        from ..client import CloudStackClient as Client
        from ..client.cloudstack_client import CloudStackConfig as CSConfig
        
        cs_config = CSConfig(
            api_url=self._build_api_url(),
            api_key=config.management_server.get('api_key', ''),
            secret_key=config.management_server.get('secret_key', ''),
        )
        
        self.client = Client(cs_config)
        
        # Initialize managers
        self.infra = InfrastructureManager(self.client)
        self.network = NetworkManager(self.client)
        self.hybrid = HybridCloudManager()
        self.monitoring = MonitoringService(self.client)
    
    def _build_api_url(self) -> str:
        """Build API URL from config."""
        mgmt = self.config.management_server
        scheme = mgmt.get('scheme', 'http')
        host = mgmt.get('host', 'localhost')
        port = mgmt.get('port', 8096)
        return f"{scheme}://{host}:{port}/api"
    
    def deploy_zone(
        self,
        config: ZoneConfig,
    ) -> DeploymentResult:
        """Deploy a zone."""
        try:
            logger.info(f"Deploying zone: {config.name}")
            
            zone = self.infra.zones.create(
                name=config.name,
                dns1=config.dns1,
                dns2=config.dns2,
                internaldns1=config.internaldns1,
                internaldns2=config.internaldns2,
                network_type=config.network_type,
            )
            
            return DeploymentResult(
                success=True,
                resource_type="zone",
                resource_id=zone.id,
                message=f"Zone {config.name} deployed successfully",
            )
            
        except Exception as e:
            logger.error(f"Zone deployment failed: {e}")
            return DeploymentResult(
                success=False,
                resource_type="zone",
                message="Zone deployment failed",
                error=str(e),
            )
    
    def deploy_infrastructure(
        self,
        config_path: str,
    ) -> List[DeploymentResult]:
        """Deploy full infrastructure from config file."""
        results = []
        
        config = load_config(config_path)
        
        # Deploy zones
        for zone_config in config.get('zones', []):
            zone_cfg = ZoneConfig.from_dict(zone_config)
            result = self.deploy_zone(zone_cfg)
            results.append(result)
            
            if result.success:
                # Deploy pods in zone
                for pod_config in zone_config.get('pods', []):
                    pod_result = self.deploy_pod(zone_cfg.id, pod_config)
                    results.append(pod_result)
        
        return results
    
    def deploy_pod(
        self,
        zone_id: str,
        config: Dict[str, Any],
    ) -> DeploymentResult:
        """Deploy a pod."""
        try:
            pod = self.infra.pods.create(
                name=config['name'],
                zone_id=zone_id,
                start_ip=config['start_ip'],
                end_ip=config['end_ip'],
                gateway=config['gateway'],
                netmask=config['netmask'],
            )
            
            return DeploymentResult(
                success=True,
                resource_type="pod",
                resource_id=pod.id,
                message=f"Pod {config['name']} deployed",
            )
            
        except Exception as e:
            logger.error(f"Pod deployment failed: {e}")
            return DeploymentResult(
                success=False,
                resource_type="pod",
                error=str(e),
            )
    
    def deploy_cluster(
        self,
        zone_id: str,
        pod_id: str,
        config: Dict[str, Any],
    ) -> DeploymentResult:
        """Deploy a cluster."""
        try:
            cluster = self.infra.clusters.create(
                name=config['name'],
                zone_id=zone_id,
                pod_id=pod_id,
                hypervisor=config.get('hypervisor', 'KVM'),
            )
            
            return DeploymentResult(
                success=True,
                resource_type="cluster",
                resource_id=cluster.id,
                message=f"Cluster {config['name']} deployed",
            )
            
        except Exception as e:
            logger.error(f"Cluster deployment failed: {e}")
            return DeploymentResult(
                success=False,
                resource_type="cluster",
                error=str(e),
            )
    
    def add_host(
        self,
        zone_id: str,
        pod_id: str,
        cluster_id: str,
        host_name: str,
        password: str,
    ) -> DeploymentResult:
        """Add a host."""
        try:
            host = self.infra.hosts.add(
                zone_id=zone_id,
                pod_id=pod_id,
                cluster_id=cluster_id,
                host_name=host_name,
                password=password,
            )
            
            return DeploymentResult(
                success=True,
                resource_type="host",
                resource_id=host.id,
                message=f"Host {host_name} added",
            )
            
        except Exception as e:
            logger.error(f"Host addition failed: {e}")
            return DeploymentResult(
                success=False,
                resource_type="host",
                error=str(e),
            )
    
    def connect_hybrid_cloud(
        self,
        provider: str,
        config: Dict[str, Any],
    ) -> DeploymentResult:
        """Connect hybrid cloud provider."""
        try:
            from ..hybrid.connector import HybridConnectionConfig
            
            conn_config = HybridConnectionConfig(
                provider=provider,
                enabled=config.get('enabled', True),
                connection_type=config.get('connection_type', 'direct'),
                vlan_id=config.get('vlan_id'),
                bgp_asn=config.get('bgp_asn'),
                partner_name=config.get('partner_name'),
            )
            
            if provider == 'aws':
                connector = self.hybrid.register_aws(conn_config)
            elif provider == 'azure':
                connector = self.hybrid.register_azure(conn_config)
            elif provider == 'gcp':
                connector = self.hybrid.register_gcp(conn_config)
            else:
                return DeploymentResult(
                    success=False,
                    resource_type="hybrid_cloud",
                    error=f"Unknown provider: {provider}",
                )
            
            # Connect
            connected = connector.connect()
            
            return DeploymentResult(
                success=connected,
                resource_type="hybrid_cloud",
                message=f"{provider} connected" if connected else f"{provider} connection failed",
            )
            
        except Exception as e:
            logger.error(f"Hybrid cloud connection failed: {e}")
            return DeploymentResult(
                success=False,
                resource_type="hybrid_cloud",
                error=str(e),
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get deployment status."""
        return {
            "infrastructure": self.infra.get_status(),
            "network": {
                "physical_networks": len(self.network.physical.list()),
                "offerings": len(self.network.offerings.list()),
            },
            "hybrid": {
                "providers": list(self.hybrid.connectors.keys()),
            },
            "monitoring": self.monitoring.get_status(),
        }
    
    def validate_config(self, config_path: str) -> List[str]:
        """Validate configuration file."""
        errors = []
        
        try:
            config = load_config(config_path)
            
            # Validate required fields
            if 'zones' not in config:
                errors.append("Missing required field: zones")
            
            for zone in config.get('zones', []):
                if 'name' not in zone:
                    errors.append("Zone missing name field")
                if 'dns1' not in zone:
                    errors.append("Zone missing dns1 field")
                if 'internaldns1' not in zone:
                    errors.append("Zone missing internaldns1 field")
                    
        except Exception as e:
            errors.append(f"Config validation error: {e}")
        
        return errors
    
    def __repr__(self) -> str:
        status = self.get_status()
        return f"DeploymentEngine(infrastructure={status['infrastructure']})"