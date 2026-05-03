"""Configuration management for Apache CloudStack hybrid cloud platform."""

import os
import yaml
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class CloudStackConfig:
    """Base configuration for CloudStack."""
    
    version: str = "4.18.0"
    management_server: Dict[str, Any] = field(default_factory=dict)
    database: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, file_path: str) -> "CloudStackConfig":
        """Load configuration from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        config = cls()
        if data:
            if 'cloudstack' in data:
                cs_data = data['cloudstack']
                config.version = cs_data.get('version', '4.18.0')
                config.management_server = cs_data.get('management_server', {})
                config.database = cs_data.get('database', {})
                config.security = cs_data.get('security', {})
                config.logging = cs_data.get('logging', {})
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cloudstack': {
                'version': self.version,
                'management_server': self.management_server,
                'database': self.database,
                'security': self.security,
                'logging': self.logging,
            }
        }


@dataclass
class RegionConfig:
    """Configuration for a region."""
    
    id: str
    name: str
    endpoint: str = ""
    zones: list = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegionConfig":
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            endpoint=data.get('endpoint', ''),
            zones=data.get('zones', []),
        )


@dataclass
class ZoneConfig:
    """Configuration for a zone."""
    
    id: str
    name: str
    dns1: str
    dns2: str = ""
    internaldns1: str
    internaldns2: str = ""
    network_type: str = "Basic"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoneConfig":
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            dns1=data.get('dns1', ''),
            dns2=data.get('dns2', ''),
            internaldns1=data.get('internaldns1', ''),
            internaldns2=data.get('internaldns2', ''),
            network_type=data.get('network_type', 'Basic'),
        )


@dataclass
class HybridCloudConfig:
    """Configuration for hybrid cloud."""
    
    provider: str
    enabled: bool = True
    connection: Dict[str, Any] = field(default_factory=dict)
    routing: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, file_path: str) -> "HybridCloudConfig":
        """Load from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        config = cls(
            provider=data.get('hybrid_cloud', {}).get('provider', ''),
            enabled=data.get('hybrid_cloud', {}).get('enabled', True),
        )
        
        if 'connection' in data.get('hybrid_cloud', {}):
            config.connection = data['hybrid_cloud']['connection']
        if 'routing' in data.get('hybrid_cloud', {}):
            config.routing = data['hybrid_cloud']['routing']
        
        return config


def load_config(file_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config: Dict[str, Any], file_path: str) -> None:
    """Save configuration to YAML file."""
    with open(file_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def interpolate_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Interpolate environment variables in configuration."""
    def _interpolate(value):
        if isinstance(value, str):
            if value.startswith('${') and value.endswith('}'):
                return os.environ.get(value[2:-1], value)
        elif isinstance(value, dict):
            return {k: _interpolate(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_interpolate(item) for item in value]
        return value
    
    return _interpolate(config)


__all__ = [
    "CloudStackConfig",
    "RegionConfig",
    "ZoneConfig",
    "HybridCloudConfig",
    "load_config",
    "save_config",
    "interpolate_env_vars",
]