"""Apache CloudStack API client for hybrid cloud platform."""

import hashlib
import hmac
import base64
import time
import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode, quote
from dataclasses import dataclass, field
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    APIException,
    AuthenticationException,
    ConnectionException,
    TimeoutException,
    ValidationException,
)
from .api_response import (
    CloudStackResponse,
    parse_response,
    parse_list_response,
)


logger = logging.getLogger(__name__)


@dataclass
class CloudStackConfig:
    """Configuration for CloudStack client."""
    
    api_url: str
    api_key: str
    secret_key: str
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    pool_connections: int = 10
    pool_maxsize: int = 10
    
    # Async job polling settings
    async_poll_interval: int = 2
    async_poll_timeout: int = 300
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "CloudStackConfig":
        """Create config from dictionary."""
        mgmt = config.get("management_server", {})
        return cls(
            api_url=f"{mgmt.get('scheme', 'http')}://{mgmt.get('host', 'localhost')}:{mgmt.get('port', 8096)}/api",
            api_key=mgmt.get("api_key", ""),
            secret_key=mgmt.get("secret_key", ""),
            timeout=mgmt.get("timeout", 30),
            verify_ssl=mgmt.get("verify_ssl", True),
        )


class CloudStackClient:
    """Apache CloudStack API client."""
    
    def __init__(self, config: CloudStackConfig):
        """Initialize CloudStack client.
        
        Args:
            config: CloudStack configuration
        """
        self.config = config
        self.session = self._create_session()
        self._signature_version = "3"
        self._nonce = 0
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(
            pool_connections=self.config.pool_connections,
            pool_maxsize=self.config.pool_maxsize,
            max_retries=retry_strategy,
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _generate_signature(
        self, 
        method: str, 
        params: Dict[str, Any]
    ) -> str:
        """Generate CloudStack API signature.
        
        Args:
            method: HTTP method
            params: API parameters
            
        Returns:
            Signature string
        """
        # Build the signature base string
        params_sorted = sorted(params.items())
        query_string = "&".join([
            f"{quote(str(k), safe='')}={quote(str(v), safe='')}"
            for k, v in params_sorted
        ])
        
        signature_base = f"{method.lower()}&{quote(self.config.api_url, safe='')}&{quote(query_string, safe='')}"
        
        # Generate HMAC-SHA1 signature
        key = self.config.secret_key.encode()
        message = signature_base.encode()
        
        signature = hmac.new(key, message, hashlib.sha1).digest()
        signature_b64 = base64.b64encode(signature).decode()
        
        return signature_b64
    
    def _build_request(
        self, 
        command: str, 
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True
    ) -> Dict[str, Any]:
        """Build API request parameters.
        
        Args:
            command: API command
            params: Additional parameters
            signed: Whether to sign the request
            
        Returns:
            Request parameters dictionary
        """
        request_params = {
            "command": command,
            "response": "json",
            "apiKey": self.config.api_key,
        }
        
        if params:
            request_params.update(params)
        
        if signed:
            request_params["signature"] = self._generate_signature(
                "GET", 
                {k: v for k, v in request_params.items() if v is not None}
            )
        
        return request_params
    
    def _make_request(
        self, 
        method: str, 
        command: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> CloudStackResponse:
        """Make an API request.
        
        Args:
            method: HTTP method
            command: API command
            params: Request parameters
            
        Returns:
            CloudStackResponse object
        """
        request_params = self._build_request(command, params)
        url = self.config.api_url
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=request_params,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            response.raise_for_status()
            
            # Parse JSON response
            json_response = response.json()
            
            # Handle CloudStack error responses
            if "errorcode" in json_response:
                error = json_response.get("error", {})
                raise APIException(
                    message=error.get("errortext", "Unknown error"),
                    error_code=json_response.get("errorcode"),
                    api_response=json_response
                )
            
            return parse_response(json_response)
            
        except requests.exceptions.Timeout as e:
            raise TimeoutException(
                message=f"Request timeout: {e}",
                operation=command,
                timeout=self.config.timeout
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionException(
                message=f"Connection error: {e}",
                host=self.config.api_url.split("://")[1].split(":")[0],
                port=8096
            )
        except requests.exceptions.HTTPError as e:
            raise APIException(
                message=f"HTTP error: {e}",
                error_code=response.status_code
            )
        except json.JSONDecodeError as e:
            raise APIException(
                message=f"Invalid JSON response: {e}"
            )
    
    def _make_list_request(
        self, 
        command: str, 
        params: Optional[Dict[str, Any]] = None,
        list_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Make a list API request.
        
        Args:
            command: API command
            params: Request parameters
            list_key: Key for the list in response
            
        Returns:
            List of items
        """
        if list_key is None:
            # Derive list key from command (e.g., listZones -> zone)
            command_lower = command.lower()
            if command_lower.startswith("list"):
                list_key = command_lower[4:-1].lower()
            else:
                list_key = command
        
        response = self._make_request("GET", command, params)
        
        if not response.is_success:
            raise APIException(
                message=response.error_text or "Request failed",
                error_code=response.error_code
            )
        
        return parse_list_response(response.response_data, list_key)
    
    def _poll_async_job(self, job_id: str) -> CloudStackResponse:
        """Poll for async job completion.
        
        Args:
            job_id: Async job ID
            
        Returns:
            CloudStackResponse object
        """
        start_time = time.time()
        
        while True:
            response = self._make_request(
                "GET", 
                "queryAsyncJobResult",
                {"jobid": job_id}
            )
            
            if response.is_complete:
                return response
            
            elapsed = time.time() - start_time
            if elapsed > self.config.async_poll_timeout:
                raise TimeoutException(
                    message=f"Async job timeout after {self.config.async_poll_timeout}s",
                    operation=f"queryAsyncJobResult({job_id})",
                    timeout=self.config.async_poll_timeout
                )
            
            time.sleep(self.config.async_poll_interval)
    
    # ========== API Methods ==========
    
    def test_connection(self) -> bool:
        """Test connection to CloudStack API.
        
        Returns:
            True if connection successful
        """
        try:
            response = self._make_request("GET", "listApis")
            return response.is_success
        except Exception:
            return False
    
    def get_api_version(self) -> str:
        """Get CloudStack API version.
        
        Returns:
            Version string
        """
        response = self._make_request("GET", "listApis", {"name": "info"})
        if response.is_success:
            api_info = response.get_first("apidescription")
            if api_info:
                return api_info.get("apiversion", "unknown")
        return "unknown"
    
    # ========== Domain Operations ==========
    
    def create_domain(self, name: str, parent_domain: Optional[str] = None) -> CloudStackResponse:
        """Create a domain.
        
        Args:
            name: Domain name
            parent_domain: Parent domain ID (optional)
            
        Returns:
            CloudStackResponse object
        """
        params = {"name": name}
        if parent_domain:
            params["parentdomainid"] = parent_domain
        
        return self._make_request("GET", "createDomain", params)
    
    def list_domains(self, domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List domains.
        
        Args:
            domain_id: Domain ID filter (optional)
            
        Returns:
            List of domains
        """
        params = {}
        if domain_id:
            params["id"] = domain_id
        
        return self._make_list_request("listDomains", params, "domain")
    
    def delete_domain(self, domain_id: str) -> CloudStackResponse:
        """Delete a domain.
        
        Args:
            domain_id: Domain ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "deleteDomain", {"id": domain_id})
    
    # ========== Account Operations ==========
    
    def create_account(
        self, 
        account_name: str, 
        account_type: int,
        domain_id: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        password: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> CloudStackResponse:
        """Create an account.
        
        Args:
            account_name: Account name
            account_type: Account type (0=user, 1=admin, 2=domain admin)
            domain_id: Domain ID
            email: Email address
            first_name: First name
            last_name: Last name
            password: Password
            user_name: Username
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "account": account_name,
            "accounttype": account_type,
            "domainid": domain_id,
        }
        
        if email:
            params["email"] = email
        if first_name:
            params["firstname"] = first_name
        if last_name:
            params["lastname"] = last_name
        if password:
            params["password"] = password
        if user_name:
            params["username"] = user_name
        
        return self._make_request("GET", "createAccount", params)
    
    def list_accounts(
        self, 
        domain_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List accounts.
        
        Args:
            domain_id: Domain ID filter
            name: Account name filter
            
        Returns:
            List of accounts
        """
        params = {}
        if domain_id:
            params["domainid"] = domain_id
        if name:
            params["name"] = name
        
        return self._make_list_request("listAccounts", params, "account")
    
    # ========== Zone Operations ==========
    
    def create_zone(
        self,
        name: str,
        dns1: str,
        internaldns1: str,
        network_type: str = "Basic",
        dns2: Optional[str] = None,
        dns3: Optional[str] = None,
        internaldns2: Optional[str] = None,
        domain: Optional[str] = None,
        domainid: Optional[str] = None,
        guest_cidr: Optional[str] = None,
    ) -> CloudStackResponse:
        """Create a zone.
        
        Args:
            name: Zone name
            dns1: Primary DNS
            internaldns1: Primary internal DNS
            network_type: Network type (Basic/Advanced)
            dns2: Secondary DNS (optional)
            dns3: Tertiary DNS (optional)
            internaldns2: Secondary internal DNS (optional)
            domain: Domain name (optional)
            domainid: Domain ID (optional)
            guest_cidr: Guest CIDR (optional)
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "name": name,
            "dns1": dns1,
            "internaldns1": internaldns1,
            "networktype": network_type,
        }
        
        if dns2:
            params["dns2"] = dns2
        if dns3:
            params["dns3"] = dns3
        if internaldns2:
            params["internaldns2"] = internaldns2
        if domain:
            params["domain"] = domain
        if domainid:
            params["domainid"] = domainid
        if guest_cidr:
            params["guestcidraddress"] = guest_cidr
        
        return self._make_request("GET", "createZone", params)
    
    def list_zones(
        self, 
        zone_id: Optional[str] = None,
        available: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List zones.
        
        Args:
            zone_id: Zone ID filter
            available: Available filter
            
        Returns:
            List of zones
        """
        params = {}
        if zone_id:
            params["id"] = zone_id
        if available is not None:
            params["available"] = str(available).lower()
        
        return self._make_list_request("listZones", params, "zone")
    
    def update_zone(
        self, 
        zone_id: str,
        name: Optional[str] = None,
        dns1: Optional[str] = None,
        dns2: Optional[str] = None,
    ) -> CloudStackResponse:
        """Update a zone.
        
        Args:
            zone_id: Zone ID
            name: New name
            dns1: New primary DNS
            dns2: New secondary DNS
            
        Returns:
            CloudStackResponse object
        """
        params = {"id": zone_id}
        
        if name:
            params["name"] = name
        if dns1:
            params["dns1"] = dns1
        if dns2:
            params["dns2"] = dns2
        
        return self._make_request("GET", "updateZone", params)
    
    def delete_zone(self, zone_id: str) -> CloudStackResponse:
        """Delete a zone.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "deleteZone", {"id": zone_id})
    
    # ========== Pod Operations ==========
    
    def create_pod(
        self,
        name: str,
        zone_id: str,
        start_ip: str,
        end_ip: str,
        gateway: str,
        netmask: str,
        cluster_id: Optional[str] = None,
    ) -> CloudStackResponse:
        """Create a pod.
        
        Args:
            name: Pod name
            zone_id: Zone ID
            start_ip: Start IP range
            end_ip: End IP range
            gateway: Gateway
            netmask: Netmask
            cluster_id: Cluster ID (optional)
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "name": name,
            "zoneid": zone_id,
            "startip": start_ip,
            "endip": end_ip,
            "gateway": gateway,
            "netmask": netmask,
        }
        
        if cluster_id:
            params["clusterid"] = cluster_id
        
        return self._make_request("GET", "createPod", params)
    
    def list_pods(
        self, 
        zone_id: Optional[str] = None,
        pod_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List pods.
        
        Args:
            zone_id: Zone ID filter
            pod_id: Pod ID filter
            
        Returns:
            List of pods
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        if pod_id:
            params["id"] = pod_id
        
        return self._make_list_request("listPods", params, "pod")
    
    def update_pod(
        self, 
        pod_id: str,
        name: Optional[str] = None,
        start_ip: Optional[str] = None,
        end_ip: Optional[str] = None,
    ) -> CloudStackResponse:
        """Update a pod.
        
        Args:
            pod_id: Pod ID
            name: New name
            start_ip: New start IP
            end_ip: New end IP
            
        Returns:
            CloudStackResponse object
        """
        params = {"id": pod_id}
        
        if name:
            params["name"] = name
        if start_ip:
            params["startip"] = start_ip
        if end_ip:
            params["endip"] = end_ip
        
        return self._make_request("GET", "updatePod", params)
    
    def delete_pod(self, pod_id: str) -> CloudStackResponse:
        """Delete a pod.
        
        Args:
            pod_id: Pod ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "deletePod", {"id": pod_id})
    
    # ========== Cluster Operations ==========
    
    def create_cluster(
        self,
        name: str,
        zone_id: str,
        pod_id: str,
        cluster_type: str = "KVM",
        hypervisor: str = "KVM",
        vsm_ip: Optional[str] = None,
    ) -> CloudStackResponse:
        """Create a cluster.
        
        Args:
            name: Cluster name
            zone_id: Zone ID
            pod_id: Pod ID
            cluster_type: Cluster type
            hypervisor: Hypervisor type
            vsm_ip: VSM IP address (optional)
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "clustername": name,
            "zoneid": zone_id,
            "podid": pod_id,
            "clustertype": cluster_type,
            "hypervisor": hypervisor,
        }
        
        if vsm_ip:
            params["vsmipaddress"] = vsm_ip
        
        return self._make_request("GET", "createCluster", params)
    
    def list_clusters(
        self, 
        zone_id: Optional[str] = None,
        pod_id: Optional[str] = None,
        cluster_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List clusters.
        
        Args:
            zone_id: Zone ID filter
            pod_id: Pod ID filter
            cluster_id: Cluster ID filter
            
        Returns:
            List of clusters
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        if pod_id:
            params["podid"] = pod_id
        if cluster_id:
            params["id"] = cluster_id
        
        return self._make_list_request("listClusters", params, "cluster")
    
    def delete_cluster(self, cluster_id: str) -> CloudStackResponse:
        """Delete a cluster.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "deleteCluster", {"id": cluster_id})
    
    # ========== Host Operations ==========
    
    def add_host(
        self,
        zone_id: str,
        pod_id: str,
        cluster_id: str,
        host_name: str,
        password: str,
        hypervisor: str = "KVM",
        host_type: str = "Routing",
    ) -> CloudStackResponse:
        """Add a host.
        
        Args:
            zone_id: Zone ID
            pod_id: Pod ID
            cluster_id: Cluster ID
            host_name: Host IP or name
            password: Host password
            hypervisor: Hypervisor type
            host_type: Host type
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "zoneid": zone_id,
            "podid": pod_id,
            "clusterid": cluster_id,
            "hostname": host_name,
            "password": password,
            "hypervisor": hypervisor,
            "hosttype": host_type,
        }
        
        return self._make_request("GET", "addHost", params)
    
    def list_hosts(
        self, 
        zone_id: Optional[str] = None,
        pod_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
        host_id: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List hosts.
        
        Args:
            zone_id: Zone ID filter
            pod_id: Pod ID filter
            cluster_id: Cluster ID filter
            host_id: Host ID filter
            type: Host type filter
            
        Returns:
            List of hosts
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        if pod_id:
            params["podid"] = pod_id
        if cluster_id:
            params["clusterid"] = cluster_id
        if host_id:
            params["id"] = host_id
        if type:
            params["type"] = type
        
        return self._make_list_request("listHosts", params, "host")
    
    def delete_host(
        self, 
        host_id: str,
        force: bool = False
    ) -> CloudStackResponse:
        """Delete a host.
        
        Args:
            host_id: Host ID
            force: Force removal
            
        Returns:
            CloudStackResponse object
        """
        params = {"id": host_id}
        if force:
            params["forced"] = str(force).lower()
        
        return self._make_request("GET", "deleteHost", params)
    
    # ========== Storage Operations ==========
    
    def add_primary_storage(
        self,
        name: str,
        zone_id: str,
        pool_type: str,
        path: str,
        cluster_id: Optional[str] = None,
    ) -> CloudStackResponse:
        """Add primary storage.
        
        Args:
            name: Storage name
            zone_id: Zone ID
            pool_type: Pool type (NFS, LVM, etc.)
            path: Storage path
            cluster_id: Cluster ID (optional)
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "name": name,
            "zoneid": zone_id,
            "protocol": pool_type,
            "server": path,
        }
        
        if cluster_id:
            params["clusterid"] = cluster_id
        
        return self._make_request("GET", "addPrimaryStorage", params)
    
    def list_primary_storage(
        self, 
        zone_id: Optional[str] = None,
        storage_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List primary storage pools.
        
        Args:
            zone_id: Zone ID filter
            storage_id: Storage ID filter
            
        Returns:
            List of storage pools
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        if storage_id:
            params["id"] = storage_id
        
        return self._make_list_request("listStoragePools", params, "storagepool")
    
    def add_secondary_storage(
        self,
        zone_id: str,
        nfs_server: str,
        path: str,
    ) -> CloudStackResponse:
        """Add secondary storage.
        
        Args:
            zone_id: Zone ID
            nfs_server: NFS server
            path: Mount path
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "zoneid": zone_id,
            "url": f"nfs://{nfs_server}:{path}",
        }
        
        return self._make_request("GET", "addSecondaryStorage", params)
    
    # ========== Network Operations ==========
    
    def create_physical_network(
        self,
        zone_id: str,
        name: str,
        isolation_method: str = "VLAN",
        broadcast_domain_range: Optional[Dict[str, int]] = None,
    ) -> CloudStackResponse:
        """Create a physical network.
        
        Args:
            zone_id: Zone ID
            name: Network name
            isolation_method: Isolation method (VLAN, GRE, etc.)
            broadcast_domain_range: Broadcast domain range
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "zoneid": zone_id,
            "name": name,
            "isolationmethod": isolation_method,
        }
        
        if broadcast_domain_range:
            params["broadcastdomainrange"] = broadcast_domain_range
        
        return self._make_request("GET", "createPhysicalNetwork", params)
    
    def list_physical_networks(
        self, 
        zone_id: Optional[str] = None,
        network_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List physical networks.
        
        Args:
            zone_id: Zone ID filter
            network_id: Network ID filter
            
        Returns:
            List of physical networks
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        if network_id:
            params["id"] = network_id
        
        return self._make_list_request("listPhysicalNetworks", params, "physicalnetwork")
    
    def create_network_offering(
        self,
        name: str,
        display_text: str,
        guest_type: str,
        supported_services: List[str],
        service_offering_id: str,
        isolation_method: str = "VLAN",
    ) -> CloudStackResponse:
        """Create a network offering.
        
        Args:
            name: Offering name
            display_text: Display text
            guest_type: Guest network type
            supported_services: List of supported services
            service_offering_id: Service offering ID
            isolation_method: Isolation method
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "name": name,
            "displaytext": display_text,
            "guestiptype": guest_type,
            "supportednetworktypes": supported_services,
            "serviceofferingid": service_offering_id,
            "isolationmethod": isolation_method,
        }
        
        return self._make_request("GET", "createNetworkOffering", params)
    
    # ========== Template/ISO Operations ==========
    
    def register_template(
        self,
        name: str,
        os_type_id: str,
        url: str,
        zone_id: str,
        hypervisor: str = "KVM",
        format: str = "QCOW2",
        bootable: bool = True,
        is_public: bool = True,
    ) -> CloudStackResponse:
        """Register a template.
        
        Args:
            name: Template name
            os_type_id: OS type ID
            url: Template URL
            zone_id: Zone ID
            hypervisor: Hypervisor type
            format: Format
            bootable: Bootable
            is_public: Public
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "name": name,
            "osTypeId": os_type_id,
            "url": url,
            "zoneid": zone_id,
            "hypervisor": hypervisor,
            "format": format,
            "bootable": str(bootable).lower(),
            "ispublic": str(is_public).lower(),
        }
        
        return self._make_request("GET", "registerTemplate", params)
    
    def list_templates(
        self, 
        template_filter: str = "executable",
        zone_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List templates.
        
        Args:
            template_filter: Template filter
            zone_id: Zone ID filter
            
        Returns:
            List of templates
        """
        params = {"templatefilter": template_filter}
        if zone_id:
            params["zoneid"] = zone_id
        
        return self._make_list_request("listTemplates", params, "template")
    
    def list_os_types(self) -> List[Dict[str, Any]]:
        """List OS types.
        
        Returns:
            List of OS types
        """
        return self._make_list_request("listOsTypes", {}, "ostype")
    
    # ========== VM Instance Operations ==========
    
    def deploy_virtual_machine(
        self,
        template_id: str,
        service_offering_id: str,
        zone_id: str,
        network_ids: Optional[List[str]] = None,
        group: Optional[str] = None,
        name: Optional[str] = None,
        account: Optional[str] = None,
        domain_id: Optional[str] = None,
        userdata: Optional[str] = None,
    ) -> CloudStackResponse:
        """Deploy a virtual machine.
        
        Args:
            template_id: Template ID
            service_offering_id: Service offering ID
            zone_id: Zone ID
            network_ids: Network IDs (optional)
            group: VM group (optional)
            name: VM name (optional)
            account: Account (optional)
            domain_id: Domain ID (optional)
            userdata: User data (optional)
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "templateid": template_id,
            "serviceofferingid": service_offering_id,
            "zoneid": zone_id,
        }
        
        if network_ids:
            params["networkids"] = ",".join(network_ids)
        if group:
            params["group"] = group
        if name:
            params["name"] = name
        if account:
            params["account"] = account
        if domain_id:
            params["domainid"] = domain_id
        if userdata:
            params["userdata"] = userdata
        
        return self._make_request("GET", "deployVirtualMachine", params)
    
    def list_virtual_machines(
        self, 
        zone_id: Optional[str] = None,
        account: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List virtual machines.
        
        Args:
            zone_id: Zone ID filter
            account: Account filter
            state: State filter
            
        Returns:
            List of VMs
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        if account:
            params["account"] = account
        if state:
            params["state"] = state
        
        return self._make_list_request("listVirtualMachines", params, "virtualmachine")
    
    def start_virtual_machine(self, vm_id: str) -> CloudStackResponse:
        """Start a virtual machine.
        
        Args:
            vm_id: VM ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "startVirtualMachine", {"id": vm_id})
    
    def stop_virtual_machine(
        self, 
        vm_id: str,
        force: bool = False
    ) -> CloudStackResponse:
        """Stop a virtual machine.
        
        Args:
            vm_id: VM ID
            force: Force stop
            
        Returns:
            CloudStackResponse object
        """
        params = {"id": vm_id}
        if force:
            params["forced"] = str(force).lower()
        
        return self._make_request("GET", "stopVirtualMachine", params)
    
    def reboot_virtual_machine(self, vm_id: str) -> CloudStackResponse:
        """Reboot a virtual machine.
        
        Args:
            vm_id: VM ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "rebootVirtualMachine", {"id": vm_id})
    
    def destroy_virtual_machine(
        self, 
        vm_id: str,
        expunge: bool = True
    ) -> CloudStackResponse:
        """Destroy a virtual machine.
        
        Args:
            vm_id: VM ID
            expunge: Expunge on delete
            
        Returns:
            CloudStackResponse object
        """
        params = {"id": vm_id, "expunge": str(expunge).lower()}
        return self._make_request("GET", "destroyVirtualMachine", params)
    
    # ========== Service Offering Operations ==========
    
    def list_service_offerings(
        self, 
        service_offering_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List service offerings.
        
        Args:
            service_offering_id: Service offering ID filter
            
        Returns:
            List of service offerings
        """
        params = {}
        if service_offering_id:
            params["id"] = service_offering_id
        
        return self._make_list_request("listServiceOfferings", params, "serviceoffering")
    
    def create_service_offering(
        self,
        name: str,
        display_text: str,
        cpu_number: int,
        cpu_speed: int,
        memory: int,
       Offeringtype: str = "General",
    ) -> CloudStackResponse:
        """Create a service offering.
        
        Args:
            name: Offering name
            display_text: Display text
            cpu_number: Number of CPUs
            cpu_speed: CPU speed in MHz
            memory: Memory in MB
            offering_type: Offering type
            
        Returns:
            CloudStackResponse object
        """
        params = {
            "name": name,
            "displaytext": display_text,
            "cpunumber": cpu_number,
            "cpuspeed": cpu_speed,
            "memory": memory,
            "offeringtype": offering_type,
        }
        
        return self._make_request("GET", "createServiceOffering", params)
    
    # ========== Async Job Operations ==========
    
    def query_async_job(self, job_id: str) -> CloudStackResponse:
        """Query async job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            CloudStackResponse object
        """
        return self._make_request("GET", "queryAsyncJobResult", {"jobid": job_id})
    
    def list_async_jobs(self) -> List[Dict[str, Any]]:
        """List async jobs.
        
        Returns:
            List of async jobs
        """
        return self._make_list_request("listAsyncJobs", {}, "asynjob")
    
    # ========== Metrics Operations ==========
    
    def get_metrics(
        self, 
        zone_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get system metrics.
        
        Args:
            zone_id: Zone ID filter
            
        Returns:
            Metrics dictionary
        """
        params = {}
        if zone_id:
            params["zoneid"] = zone_id
        
        response = self._make_request("GET", "listHostMetrics", params)
        
        if response.is_success:
            return response.response_data.get("host", [])
        return []
    
    def get_usage_stats(
        self,
        start_date: str,
        end_date: str,
        account: Optional[str] = None,
        domain_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get usage statistics.
        
        Args:
            start_date: Start date
            end_date: End date
            account: Account filter
            domain_id: Domain ID filter
            
        Returns:
            List of usage records
        """
        params = {
            "startdate": start_date,
            "enddate": end_date,
        }
        
        if account:
            params["account"] = account
        if domain_id:
            params["domainid"] = domain_id
        
        return self._make_list_request("listUsageRecords", params, "usagerecord")
    
    # ========== Alert Operations ==========
    
    def list_alerts(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List alerts.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of alerts
        """
        params = {}
        if start_date:
            params["startdate"] = start_date
        if end_date:
            params["enddate"] = end_date
        
        return self._make_list_request("listAlerts", params, "alert")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"CloudStackClient(url={self.config.api_url})"