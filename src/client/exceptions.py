"""Custom exceptions for Apache CloudStack hybrid cloud platform."""

from typing import Optional, Any


class CloudStackException(Exception):
    """Base exception for CloudStack operations."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code or "CLOUDSTACK_ERROR"
        self.details = details


class APIException(CloudStackException):
    """Exception raised for CloudStack API errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[int] = None, 
        api_response: Optional[dict] = None
    ):
        super().__init__(message, code="API_ERROR")
        self.error_code = error_code
        self.api_response = api_response


class AuthenticationException(CloudStackException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str, api_key: Optional[str] = None):
        super().__init__(message, code="AUTH_ERROR")
        self.api_key = api_key


class ValidationException(CloudStackException):
    """Exception raised for configuration validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field


class InfrastructureException(CloudStackException):
    """Exception raised for infrastructure operations."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(message, code="INFRA_ERROR")
        self.resource_type = resource_type


class NetworkException(CloudStackException):
    """Exception raised for network configuration errors."""
    
    def __init__(self, message: str, network_id: Optional[str] = None):
        super().__init__(message, code="NETWORK_ERROR")
        self.network_id = network_id


class HybridCloudException(CloudStackException):
    """Exception raised for hybrid cloud operations."""
    
    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message, code="HYBRID_CLOUD_ERROR")
        self.provider = provider


class DeploymentException(CloudStackException):
    """Exception raised for deployment operations."""
    
    def __init__(self, message: str, deployment_id: Optional[str] = None):
        super().__init__(message, code="DEPLOYMENT_ERROR")
        self.deployment_id = deployment_id


class StorageException(CloudStackException):
    """Exception raised for storage operations."""
    
    def __init__(self, message: str, storage_type: Optional[str] = None):
        super().__init__(message, code="STORAGE_ERROR")
        self.storage_type = storage_type


class TimeoutException(CloudStackException):
    """Exception raised for timeout errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, timeout: Optional[int] = None):
        super().__init__(message, code="TIMEOUT_ERROR")
        self.operation = operation
        self.timeout = timeout


class ConnectionException(CloudStackException):
    """Exception raised for connection errors."""
    
    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None):
        super().__init__(message, code="CONNECTION_ERROR")
        self.host = host
        self.port = port