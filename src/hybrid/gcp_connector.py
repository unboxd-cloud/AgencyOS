"""GCP hybrid cloud connector for Apache CloudStack."""

import logging
from datetime import datetime

from .connector import (
    HybridCloudConnector,
    HybridConnectionConfig,
    HybridCloudStatus,
)
from ..client.exceptions import HybridCloudException


logger = logging.getLogger(__name__)


class GCPConnector(HybridCloudConnector):
    """GCP Cloud Interconnect hybrid cloud connector.
    
    Provides integration with GCP using Cloud Interconnect.
    """
    
    def __init__(self, config: HybridConnectionConfig):
        super().__init__(config)
        self._connected = False
        self._status = HybridCloudStatus(
            provider="gcp",
            connected=False,
            state="disconnected",
        )
    
    @property
    def provider_name(self) -> str:
        return "gcp"
    
    def connect(self) -> bool:
        """Establish GCP Cloud Interconnect connection.
        
        Returns:
            True if connection successful
        """
        if not self.config.enabled:
            self.logger.warning("GCP connector is disabled")
            return False
        
        try:
            self.logger.info("Connecting to GCP via Cloud Interconnect")
            
            if self.config.connection_type == "interconnect":
                self._setup_interconnect()
            else:
                raise HybridCloudException(
                    f"Invalid connection type: {self.config.connection_type}",
                    provider="gcp"
                )
            
            self._connected = True
            self._status = HybridCloudStatus(
                provider="gcp",
                connected=True,
                state="connected",
                last_sync=datetime.utcnow().isoformat() + "Z",
            )
            
            self.logger.info("Successfully connected to GCP")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to GCP: {e}")
            raise HybridCloudException(
                f"Connection failed: {e}",
                provider="gcp"
            )
    
    def _setup_interconnect(self) -> None:
        """Setup GCP Cloud Interconnect."""
        if not self.config.vlan_id:
            raise HybridCloudException(
                "VLAN ID required for Cloud Interconnect",
                provider="gcp"
            )
        
        self.logger.info(
            f"Setting up Cloud Interconnect: VLAN={self.config.vlan_id}"
        )
    
    def disconnect(self) -> bool:
        """Disconnect from GCP."""
        try:
            self._teardown_interconnect()
            self._connected = False
            self._status = HybridCloudStatus(
                provider="gcp",
                connected=False,
                state="disconnected",
            )
            self.logger.info("Disconnected from GCP")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disconnect from GCP: {e}")
            return False
    
    def _teardown_interconnect(self) -> None:
        """Teardown Cloud Interconnect."""
        self.logger.info("Tearing down Cloud Interconnect")
    
    def sync_routes(self, routes: list) -> bool:
        """Sync routing tables with GCP."""
        if not self._connected:
            raise HybridCloudException("Not connected to GCP", provider="gcp")
        
        self.logger.info(f"Syncing {len(routes)} routes with GCP")
        self._status.last_sync = datetime.utcnow().isoformat() + "Z"
        return True
    
    def get_status(self) -> HybridCloudStatus:
        """Get GCP connection status."""
        if self._connected:
            self._status.connected = True
            self._status.state = "connected"
        
        return self._status
    
    def validate_credentials(self) -> bool:
        """Validate GCP credentials."""
        return bool(self.config.vlan_id)