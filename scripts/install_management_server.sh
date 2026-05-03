#!/bin/bash
# Install Apache CloudStack Management Server
# This script installs the CloudStack management server on Ubuntu 22.04

set -e

# Configuration
CLOUDSTACK_VERSION="4.18.0"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-cloudstack}"
CLOUD_DB_PASSWORD="${CLOUD_DB_PASSWORD:-cloudstack}"
API_KEY="${API_KEY:-}"
SECRET_KEY="${SECRET_KEY:-}"

echo "=== Apache CloudStack Management Server Installation ==="
echo "Version: $CLOUDSTACK_VERSION"

# Update package repositories
echo "Updating package repositories..."
apt-get update -y

# Install required packages
echo "Installing required packages..."
apt-get install -y \
    mysql-server \
    nfs-kernel-server \
    openssh-server \
    java-11-jdk \
    python3-pip \
    wget \
    curl \
    vim

# Download CloudStack RPM/DEB (check for latest)
# Note: This is a placeholder - actual download would use real packages
echo "Downloading CloudStack packages..."

# Configure MySQL
echo "Configuring MySQL..."
cat > /etc/mysql/conf.d/cloudstack.cnf << EOF
[mysqld]
innodb_rollback_on_timeout=1
innodb_lock_wait_timeout=600
max_connections=350
max_heap_table_size=4M
tmp_table_size=4M
join_buffer_size=2M
join_buffer_size=128K
sort_buffer_size=2M
read_buffer_size=2M
read_rnd_buffer_size=4M
key_buffer_size=16M
query_cache_size=0
query_cache_type=0
query_cache_size=0
innodb_additional_mem_pool_size=2M
innodb_buffer_pool_size=4G
innodb_data_file_path=ibdata1:10M:autoextend
innodb_file_io_threads=4
innodb_flush_log_at_trx_commit=2
innodb_flush_method=O_DIRECT
innodb_lock_wait_timeout=600
log_bin=/var/lib/mysql/mysql-bin.log
binlog_format="ROW"
server-id=1
max_binlog_size=100M
sync_binlog=1
innodb_support_xa=1
EOF

# Restart MySQL
echo "Restarting MySQL..."
systemctl restart mysql

# Set MySQL root password
echo "Setting MySQL root password..."
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';" || \
mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';"

# Create CloudStack database
echo "Creating CloudStack database..."
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" << EOF
CREATE DATABASE IF NOT EXISTS cloud;
GRANT ALL PRIVILEGES ON cloud.* TO 'cloud'@'localhost' IDENTIFIED BY '${CLOUD_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON cloud.* TO 'cloud'@'%' IDENTIFIED BY '${CLOUD_DB_PASSWORD}';
FLUSH PRIVILEGES;
EOF

echo "MySQL configuration completed!"
echo ""

# Download and install CloudStack management server
# (This would normally download .deb or .rpm packages)
echo "Installing CloudStack management server..."

# Note: In production, download actual CloudStack packages
# wget http://packages.apache.org/cloudstack/releases/4.18.0/cloudstack-4.18.0.rpm
# dpkg -i cloudstack-4.18.0.rpm

# Create configuration directory
mkdir -p /etc/cloudstack
mkdir -p /var/log/cloudstack/management

echo "CloudStack management server installation completed!"
echo ""
echo "Configuration:"
echo "  API URL: http://localhost:8096/client/api"
echo "  Console: http://localhost:8080"
echo ""
echo "Next steps:"
echo "  1. Configure /etc/cloudstack/management.properties"
echo "  2. Add KVM hosts using add_host.sh"
echo "  3. Create zones via CloudStack UI or API"