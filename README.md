# Hybrid Cloud Platform using Apache CloudStack

A comprehensive Python platform for building and managing hybrid cloud environments that seamlessly integrate on-premises Apache CloudStack infrastructure with public cloud providers (AWS, Azure, GCP).

## Overview

This platform provides:

- **CloudStack API Client** - Full-featured Python client for Apache CloudStack API
- **Infrastructure Management** - Manage zones, pods, clusters, hosts, and storage
- **Network Configuration** - Physical networks, VLANs, and network offerings
- **Hybrid Cloud Integration** - Connect with AWS Direct Connect, Azure ExpressRoute, and GCP Cloud Interconnect
- **Deployment Automation** - Infrastructure as Code (IaC) templates and deployment engine
- **Monitoring** - Metrics collection, alerts, and logging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Hybrid Cloud Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Client    │  │Infrastructure│  │   Network  │       │
│  │   Layer    │  │   Manager    │  │   Manager  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Hybrid   │  │ Deployment │  │ Monitoring │       │
│  │   Cloud    │  │   Engine   │  │  Service   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/cloudstack-hybrid-cloud.git
cd cloudstack-hybrid-cloud

# Install dependencies
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure CloudStack

Create a configuration file (`config.yaml`):

```yaml
cloudstack:
  version: "4.18.0"
  management_server:
    host: "cloudstack.local"
    port: 8096
    api_key: "${CLOUDSTACK_API_KEY}"
    secret_key: "${CLOUDSTACK_SECRET_KEY}"
```

### 2. Create a Client

```python
from src.client.cloudstack_client import CloudStackClient, CloudStackConfig
from src.utils.config import CloudStackConfig, load_config

# Load configuration
config = load_config("config.yaml")

# Create client
client = CloudStackClient(config)
```

### 3. Manage Infrastructure

```python
from src.infrastructure import InfrastructureManager

infra = InfrastructureManager(client)

# Create a zone
zone = infra.zones.create(
    name="Production Zone",
    dns1="8.8.8.8",
    dns2="8.8.4.4",
    internaldns1="10.0.0.1",
    network_type="Advanced"
)

# Add a pod
pod = infra.pods.create(
    name="Pod 1",
    zone_id=zone.id,
    start_ip="10.0.1.100",
    end_ip="10.0.1.200",
    gateway="10.0.1.1",
    netmask="255.255.255.0"
)
```

### 4. Deploy Hybrid Cloud

```python
from src.hybrid import HybridCloudManager
from src.hybrid.connector import HybridConnectionConfig

# Configure AWS Direct Connect
aws_config = HybridConnectionConfig(
    provider="aws",
    enabled=True,
    connection_type="direct",
    vlan_id=100,
    bgp_asn=65001,
)

# Create connector
hybrid = HybridCloudManager()
aws_connector = hybrid.register_aws(aws_config)

# Connect
if aws_connector.connect():
    print("Connected to AWS!")
```

## Configuration

### Base Configuration

See `configs/base_config.yaml` for the base configuration template.

### Hybrid Cloud Configuration

- `configs/hybrid/aws.yaml` - AWS Direct Connect configuration
- `configs/hybrid/azure.yaml` - Azure ExpressRoute configuration
- `configs/hybrid/gcp.yaml` - GCP Cloud Interconnect configuration

## API Reference

### Client Methods

- `list_zones()` - List all zones
- `list_pods(zone_id)` - List pods in a zone
- `list_clusters(pod_id)` - List clusters in a pod
- `list_hosts(cluster_id)` - List hosts in a cluster
- `list_virtual_machines(zone_id)` - List VMs in a zone
- `deploy_virtual_machine(...)` - Deploy a new VM
- `start_vm(vm_id)` - Start a VM
- `stop_vm(vm_id)` - Stop a VM
- And many more...

### Infrastructure Manager

- `zones.create(...)` - Create a new zone
- `pods.create(...)` - Create a new pod
- `clusters.create(...)` - Create a new cluster
- `hosts.add(...)` - Add a host to a cluster
- `storage.add_primary(...)` - Add primary storage
- `storage.add_secondary(...)` - Add secondary storage

### Hybrid Cloud Manager

- `register_aws(config)` - Register AWS connector
- `register_azure(config)` - Register Azure connector
- `register_gcp(config)` - Register GCP connector
- `connect_all()` - Connect all providers
- `disconnect_all()` - Disconnect all providers

## Development

### Running Tests

```bash
# Run tests
pytest

# With coverage
pytest --cov=src
```

### Code Quality

```bash
# Format code
black src/

# Lint
flake8 src/

# Type check
mypy src/
```

## Deployment

### Deploying Infrastructure

```bash
# Using deployment script
./scripts/deploy_infrastructure.sh -c configs/deployment.yaml

# Or using Python
python -m src.deployment.engine deploy -c configs/deployment.yaml
```

### Adding KVM Hosts

```bash
# Add KVM host
./scripts/add_host.sh \
    --host 192.168.1.100 \
    --zone zone-1 \
    --pod pod-1 \
    --cluster cluster-1 \
    --password <host_password>
```

## Documentation

- [Architecture Documentation](docs/architecture.md)
- [Deployment Guide](docs/deployment_guide.md)
- [Hybrid Cloud Setup Guide](docs/hybrid_cloud_guide.md)
- [Apache CloudStack Official Docs](https://docs.cloudstack.apache.org/)

## Requirements

### Management Server

- CPU: 4 cores
- RAM: 8 GB
- Disk: 100 GB
- OS: Ubuntu 22.04 LTS / CentOS 8

### KVM Hosts

- CPU: 8 cores
- RAM: 32 GB
- Disk: 500 GB
- OS: Ubuntu 22.04 LTS / CentOS 8

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- Issue Tracker: [GitHub Issues](https://github.com/yourorg/cloudstack-hybrid-cloud/issues)
- Documentation: [Read the Docs](https://cloudstack-hybrid-cloud.readthedocs.io/)
- Apache CloudStack: [Official Website](https://cloudstack.apache.org/)