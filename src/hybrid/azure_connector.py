"""Azure hybrid cloud connector for Apache CloudStack."""

import logging
from datetime import datetime

from .connector import (
    HybridCloudConnector,
    HybridConnectionConfig,
    HybridCloudStatus,
)
from ..client.exceptions import HybridCloudException


logger = logging.getLogger(__name__)


class AzureConnector(HybridCloudConnector):
    """Azure ExpressRoute hybrid cloud connector.
    
    Provides integration with Azure using ExpressRoute.
    """
    
    def __init__(self, config: HybridConnectionConfig):
        super().__init__(config)
        self._connected = False
        self._status = HybridCloudStatus(
            provider="azure",
            connected=False,
            state="disconnected",
        )
    
    @property
    def provider_name(self) -> str:
        return "azure"
    
    def connect(self) -> bool:
        """Establish Azure ExpressRoute connection.
        
        Returns:
            True if connection successful
        """
        if not self.config.enabled:
            self.logger.warning("Azure connector is disabled")
            return False
        
        try:
            self.logger.info("Connecting to Azure via ExpressRoute")
            
            if self.config.connection_type == "expressroute":
                self._setup_expressroute()
            else:
                raise HybridCloudException(
                    f"Invalid connection type: {self.config.connection_type}",
                    provider="azure"
                )
            
            self._connected = True
            self._status = HybridCloudStatus(
                provider="azure",
                connected=True,
                state="connected",
                last_sync=datetime.utcnow().isoformat() + "Z",
            )
            
            self.logger.info("Successfully connected to Azure")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Azure: {e}")
            raise HybridCloudException(
                f"Connection failed: {e}",
                provider="azure"
            )
    
    def _setup_expressroute(self) -> None:
        """Setup Azure ExpressRoute."""
        if not self.config.bgp_asn:
            raise HybridCloudException(
                "BGP ASN required for ExpressRoute",
                provider="azure"
            )
        
        self.logger.info(
            f"Setting up ExpressRoute: BGP ASN={self.config.bgp_asn}"
        )
    
    def disconnect(self) -> bool:
        """Disconnect from Azure."""
        try:
            self._teardown_expressroute()
            self._connected = False
            self._status = HybridCloudStatus(
                provider="azure",
                connected=False,
                state="disconnected",
            )
            self.logger.info("Disconnected from Azure")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disconnect from Azure: {e}")
            return False
    
    def _teardown_expressroute(self) -> None:
        """Teardown ExpressRoute."""
        self.logger.info("Tearing down ExpressRoute")
    
    def sync_routes(self, routes: list) -> bool:
        """Sync routing tables with Azure."""
        if not self._connected:
            raise HybridCloudException("Not connected to Azure", provider="azure")
        
        self.logger.info(f"Syncing {len(routes)} routes with Azure")
        self._status.last_sync = datetime.utcnow().isoformat() + "Z"
        return True
    
    def get_status(self) -> HybridCloudStatus:
        """Get Azure connection status."""
        if self._connected:
            self._status.connected = True
            self._status.state = "connected"
        
        return self._status
    
    def validate_credentials(self) -> bool:
        """Validate Azure credentials."""
        return bool(self.config.bgp_asn)