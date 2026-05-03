"""Base hybrid cloud connector for Apache CloudStack."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..client.exceptions import HybridCloudException


logger = logging.getLogger(__name__)


@dataclass
class HybridConnectionConfig:
    """Configuration for hybrid cloud connection."""
    
    provider: str
    enabled: bool = True
    connection_type: str = "direct"
    
    # Direct Connect settings
    vlan_id: Optional[int] = None
    bgp_asn: Optional[int] = None
    partner_name: Optional[str] = None
    
    # VPN settings
    vpn_enabled: bool = False
    peer_ip: Optional[str] = None
    psk: Optional[str] = None
    
    # Routing settings
    prefix_lists: List[Dict[str, Any]] = field(default_factory=list)
    route_tables: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class HybridCloudStatus:
    """Status of hybrid cloud connection."""
    
    provider: str
    connected: bool = False
    state: str = "disconnected"
    last_sync: Optional[str] = None
    bandwidth_available: bool = True
    error: Optional[str] = None
    
    @property
    def is_healthy(self) -> bool:
        return self.connected and self.bandwidth_available


class HybridCloudConnector(ABC):
    """Base class for hybrid cloud connectors.
    
    Provides an interface for connecting CloudStack with public cloud providers
    like AWS, Azure, and GCP.
    """
    
    def __init__(self, config: HybridConnectionConfig):
        """Initialize the connector.
        
        Args:
            config: Hybrid cloud connection configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name (e.g., 'aws', 'azure', 'gcp')."""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to public cloud.
        
        Returns:
            True if connection successful
            
        Raises:
            HybridCloudException: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from public cloud.
        
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def sync_routes(self, routes: List[Dict[str, Any]]) -> bool:
        """Sync routing tables.
        
        Args:
            routes: List of routes to sync
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_status(self) -> HybridCloudStatus:
        """Get connection status.
        
        Returns:
            HybridCloudStatus object
        """
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate cloud credentials.
        
        Returns:
            True if credentials are valid
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name}, config={self.config.enabled})"


class HybridCloudManager:
    """Manages multiple hybrid cloud connections."""
    
    def __init__(self):
        self.connectors: Dict[str, HybridCloudConnector] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_connector(
        self, 
        provider: str, 
        connector: HybridCloudConnector
    ) -> None:
        """Register a hybrid cloud connector.
        
        Args:
            provider: Provider name
            connector: Connector instance
        """
        self.connectors[provider] = connector
        self.logger.info(f"Registered connector for provider: {provider}")
    
    def register_aws(self, config: HybridConnectionConfig) -> "AWSConnector":
        """Register AWS connector."""
        from .aws_connector import AWSConnector
        connector = AWSConnector(config)
        self.register_connector("aws", connector)
        return connector
    
    def register_azure(self, config: HybridConnectionConfig) -> "AzureConnector":
        """Register Azure connector."""
        from .azure_connector import AzureConnector
        connector = AzureConnector(config)
        self.register_connector("azure", connector)
        return connector
    
    def register_gcp(self, config: HybridConnectionConfig) -> "GCPConnector":
        """Register GCP connector."""
        from .gcp_connector import GCPConnector
        connector = GCPConnector(config)
        self.register_connector("gcp", connector)
        return connector
    
    def get_connector(self, provider: str) -> Optional[HybridCloudConnector]:
        """Get connector for a provider."""
        return self.connectors.get(provider)
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all registered providers."""
        results = {}
        for provider, connector in self.connectors.items():
            try:
                results[provider] = connector.connect()
            except HybridCloudException as e:
                self.logger.error(f"Failed to connect {provider}: {e}")
                results[provider] = False
        return results
    
    def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect all providers."""
        results = {}
        for provider, connector in self.connectors.items():
            try:
                results[provider] = connector.disconnect()
            except HybridCloudException as e:
                self.logger.error(f"Failed to disconnect {provider}: {e}")
                results[provider] = False
        return results
    
    def get_all_status(self) -> Dict[str, HybridCloudStatus]:
        """Get status of all connectors."""
        return {
            provider: connector.get_status() 
            for provider, connector in self.connectors.items()
        }
    
    def __repr__(self) -> str:
        return f"HybridCloudManager(providers={list(self.connectors.keys())})"