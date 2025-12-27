# Neo4j Setup Guide

**Version**: 0.1.0
**Last Updated**: 2025-12-27

This guide covers installing, configuring, and optimizing Neo4j for Kernel-GraphRAG Sentinel.

---

## Table of Contents

1. [Installation Options](#installation-options)
2. [Configuration](#configuration)
3. [Database Initialization](#database-initialization)
4. [Performance Tuning](#performance-tuning)
5. [Troubleshooting](#troubleshooting)
6. [Backup and Restore](#backup-and-restore)

---

## Installation Options

### Option 1: Using the Installation Script (Recommended for Ubuntu/Debian)

The project includes an automated installation script:

```bash
# Make the script executable
chmod +x scripts/install_neo4j.sh

# Run with sudo
sudo ./scripts/install_neo4j.sh
```

**What it does**:
1. Adds Neo4j APT repository
2. Installs Neo4j Community Edition
3. Sets initial password to `password123`
4. Enables Neo4j to start on boot
5. Starts the Neo4j service

**Verify installation**:

```bash
# Check Neo4j status
sudo systemctl status neo4j

# Check version
neo4j version

# Test connection
python3 -c "from neo4j import GraphDatabase; print('✅ Neo4j driver works')"
```

---

### Option 2: Docker (Recommended for Development)

Use Docker for an isolated Neo4j instance:

```bash
# Pull and run Neo4j container
docker run -d \
  --name kernel-graphrag-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_PLUGINS='["apoc"]' \
  -v $HOME/neo4j/data:/data \
  -v $HOME/neo4j/logs:/logs \
  neo4j:5.14

# Check container status
docker ps | grep neo4j

# View logs
docker logs kernel-graphrag-neo4j

# Stop container
docker stop kernel-graphrag-neo4j

# Start container
docker start kernel-graphrag-neo4j

# Remove container (WARNING: deletes data)
docker rm -f kernel-graphrag-neo4j
```

**Persistent Data**:
- Data stored in `$HOME/neo4j/data`
- Logs stored in `$HOME/neo4j/logs`
- Container can be removed and recreated without losing data

---

### Option 3: Manual Installation (Linux)

#### Ubuntu/Debian

```bash
# Add Neo4j repository
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | \
  sudo tee /etc/apt/sources.list.d/neo4j.list

# Update and install
sudo apt-get update
sudo apt-get install neo4j

# Set initial password
sudo neo4j-admin dbms set-initial-password password123

# Enable and start service
sudo systemctl enable neo4j
sudo systemctl start neo4j
```

#### macOS (Homebrew)

```bash
# Install Neo4j
brew install neo4j

# Start Neo4j
neo4j start

# Set password via browser (http://localhost:7474)
```

#### Windows

1. Download Neo4j Community Edition from https://neo4j.com/download/
2. Extract to `C:\neo4j`
3. Run `C:\neo4j\bin\neo4j.bat console`
4. Open browser to http://localhost:7474
5. Login with `neo4j/neo4j`, set new password to `password123`

---

## Configuration

### Default Ports

- **HTTP**: 7474 (Web UI)
- **Bolt**: 7687 (Driver protocol)
- **HTTPS**: 7473 (Secure Web UI, disabled by default)

### Configuration File

**Location**:
- Ubuntu/Debian: `/etc/neo4j/neo4j.conf`
- macOS: `/usr/local/etc/neo4j/neo4j.conf`
- Docker: Mount custom config with `-v /path/to/neo4j.conf:/var/lib/neo4j/conf/neo4j.conf`

### Recommended Settings for Kernel Analysis

Edit `neo4j.conf`:

```conf
# Memory Settings
# ================

# Heap memory (initial and max)
server.memory.heap.initial_size=1G
server.memory.heap.max_size=2G

# Page cache for graph storage
server.memory.pagecache.size=1G

# Transaction log memory
db.tx_log.preallocate=true


# Network Settings
# ================

# Listen on all interfaces (for remote access)
server.default_listen_address=0.0.0.0

# Or restrict to localhost only
# server.default_listen_address=127.0.0.1


# Security Settings
# ================

# Disable authentication (ONLY for local dev, NOT for production)
# dbms.security.auth_enabled=false

# Enable bolt connector
server.bolt.enabled=true
server.bolt.listen_address=:7687

# Enable HTTP connector
server.http.enabled=true
server.http.listen_address=:7474


# Performance Settings
# ====================

# Number of threads for bolt transactions
server.bolt.thread_pool_min_size=5
server.bolt.thread_pool_max_size=400

# Query timeout (in seconds, 0 = no timeout)
db.transaction.timeout=60s

# Maximum concurrent transactions
dbms.transaction.concurrent.maximum=1000


# Logging
# =======

# Log query execution time
dbms.logs.query.enabled=INFO
dbms.logs.query.threshold=1s

# Log level
server.logs.user.level=INFO
```

**Apply changes**:

```bash
# Restart Neo4j
sudo systemctl restart neo4j

# Or for Docker
docker restart kernel-graphrag-neo4j
```

---

## Database Initialization

### 1. Access Neo4j Browser

Open http://localhost:7474 in your browser.

**Default Credentials**:
- Username: `neo4j`
- Password: `password123` (if you used our scripts)

### 2. Verify Connection

Run in Neo4j Browser:

```cypher
// Check server status
CALL dbms.components() YIELD name, versions, edition
RETURN name, versions, edition;

// Check database
SHOW DATABASES;
```

Expected output:
```
name: "neo4j"
edition: "community"
```

### 3. Create Indexes and Constraints

The application automatically creates these during first run, but you can create them manually:

```cypher
// Function node constraints and indexes
CREATE CONSTRAINT func_id_unique IF NOT EXISTS
FOR (f:Function) REQUIRE f.id IS UNIQUE;

CREATE INDEX func_name_idx IF NOT EXISTS
FOR (f:Function) ON (f.name);

CREATE INDEX func_subsystem_idx IF NOT EXISTS
FOR (f:Function) ON (f.subsystem);

// TestCase constraints
CREATE CONSTRAINT test_id_unique IF NOT EXISTS
FOR (t:TestCase) REQUIRE t.id IS UNIQUE;

// File constraints
CREATE CONSTRAINT file_id_unique IF NOT EXISTS
FOR (f:File) REQUIRE f.id IS UNIQUE;

// Subsystem constraints
CREATE CONSTRAINT subsys_id_unique IF NOT EXISTS
FOR (s:Subsystem) REQUIRE s.id IS UNIQUE;
```

**Verify indexes**:

```cypher
SHOW INDEXES;
SHOW CONSTRAINTS;
```

### 4. Initial Database Setup via CLI

```bash
# Set environment variables
export KERNEL_ROOT=/path/to/linux-6.13
export NEO4J_PASSWORD=password123

# Run first analysis (creates schema automatically)
python3 src/main.py pipeline fs/ext4

# Verify data was ingested
python3 src/main.py stats
```

---

## Performance Tuning

### Memory Configuration

**Rule of Thumb**:
- **Heap memory**: 25-50% of available RAM (1-2GB for typical use)
- **Page cache**: 50-75% of remaining RAM (1-4GB recommended)
- **Reserve**: 1GB for OS

**Example for 8GB RAM system**:

```conf
server.memory.heap.initial_size=2G
server.memory.heap.max_size=2G
server.memory.pagecache.size=4G
```

**Check current memory usage**:

```cypher
CALL dbms.queryJmx('java.lang:type=Memory')
YIELD attributes
RETURN attributes.HeapMemoryUsage.value.used / 1024 / 1024 AS heapUsedMB,
       attributes.HeapMemoryUsage.value.max / 1024 / 1024 AS heapMaxMB;
```

### Query Optimization

**1. Use PROFILE to analyze queries**:

```cypher
PROFILE
MATCH (caller:Function)-[:CALLS]->(f:Function {name: 'ext4_map_blocks'})
RETURN count(caller);
```

Look for:
- **Rows**: Fewer is better
- **DB Hits**: Lower is better
- **Index usage**: Should say "NodeIndexSeek" not "AllNodesScan"

**2. Add indexes for frequent queries**:

```cypher
// If you query by file_path often
CREATE INDEX func_file_idx IF NOT EXISTS
FOR (f:Function) ON (f.file_path);

// If you query static functions often
CREATE INDEX func_static_idx IF NOT EXISTS
FOR (f:Function) ON (f.is_static);
```

**3. Limit result sets**:

```cypher
// Always use LIMIT for large result sets
MATCH (f:Function)
RETURN f
LIMIT 100;
```

**4. Use parameters** (faster than string interpolation):

```python
# Good
query = "MATCH (f:Function {name: $name}) RETURN f"
result = store.execute_query(query, {"name": "ext4_map_blocks"})

# Bad (slower, security risk)
query = f"MATCH (f:Function {{name: '{func_name}'}}) RETURN f"
```

### Batch Operations

**Always batch writes**:

```python
# Good: Batch 1000 at a time (what we do)
store.upsert_nodes_batch(nodes, batch_size=1000)

# Bad: One at a time (100x slower)
for node in nodes:
    store.upsert_node(node)
```

### Connection Pooling

The Neo4j driver automatically pools connections. Configure in `graph_store.py`:

```python
driver = GraphDatabase.driver(
    uri,
    auth=(user, password),
    max_connection_pool_size=50,
    connection_timeout=30.0,
    max_transaction_retry_time=15.0
)
```

---

## Troubleshooting

### Issue: Neo4j Won't Start

**Check logs**:

```bash
# Ubuntu/Debian
sudo journalctl -u neo4j -n 50

# Docker
docker logs kernel-graphrag-neo4j

# Manual installation
tail -50 /var/log/neo4j/neo4j.log
```

**Common causes**:
1. **Port already in use**:
   ```bash
   # Check if port 7687 is in use
   sudo lsof -i :7687

   # Kill conflicting process or change Neo4j port
   ```

2. **Insufficient memory**:
   - Reduce heap/pagecache in `neo4j.conf`
   - Close other applications

3. **Permission errors**:
   ```bash
   # Fix ownership
   sudo chown -R neo4j:neo4j /var/lib/neo4j
   sudo chown -R neo4j:neo4j /var/log/neo4j
   ```

### Issue: Connection Refused

**Verify Neo4j is running**:

```bash
# Check status
sudo systemctl status neo4j

# Check listening ports
sudo netstat -tlnp | grep 7687
```

**Test connection**:

```bash
# Using Cypher Shell
cypher-shell -u neo4j -p password123 "RETURN 1 AS test;"

# Using Python
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))
driver.verify_connectivity()
print('✅ Connected')
"
```

**Check firewall**:

```bash
# Ubuntu/Debian
sudo ufw allow 7687/tcp
sudo ufw allow 7474/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=7687/tcp --permanent
sudo firewall-cmd --reload
```

### Issue: Slow Queries

**1. Check if indexes exist**:

```cypher
SHOW INDEXES;
```

If missing, create them (see Database Initialization section).

**2. Analyze query plan**:

```cypher
PROFILE
MATCH (f:Function {name: 'ext4_map_blocks'})
RETURN f;
```

Look for "NodeIndexSeek" (good) vs "AllNodesScan" (bad).

**3. Check memory settings**:

```bash
# View current settings
grep "memory" /etc/neo4j/neo4j.conf
```

**4. Monitor active queries**:

```cypher
CALL dbms.listQueries()
YIELD query, elapsedTimeMillis, queryId
WHERE elapsedTimeMillis > 1000
RETURN queryId, query, elapsedTimeMillis
ORDER BY elapsedTimeMillis DESC;
```

**5. Kill slow queries**:

```cypher
CALL dbms.killQuery('query-123');
```

### Issue: Out of Memory

**Symptoms**:
- Neo4j crashes
- "java.lang.OutOfMemoryError" in logs

**Solutions**:

1. **Increase heap memory** (neo4j.conf):
   ```conf
   server.memory.heap.max_size=4G
   ```

2. **Clear database** (if too large):
   ```cypher
   // Delete all data
   MATCH (n) DETACH DELETE n;
   ```

3. **Reduce batch size** (in code):
   ```python
   # Instead of 1000
   store.upsert_nodes_batch(nodes, batch_size=500)
   ```

---

## Backup and Restore

### Backup Database

**Option 1: Neo4j Admin (Offline Backup)**

```bash
# Stop Neo4j
sudo systemctl stop neo4j

# Create backup
sudo neo4j-admin database dump neo4j \
  --to-path=/backup/neo4j-$(date +%Y%m%d).dump

# Restart Neo4j
sudo systemctl start neo4j
```

**Option 2: Docker Volume Backup**

```bash
# Stop container
docker stop kernel-graphrag-neo4j

# Backup data directory
tar -czf neo4j-backup-$(date +%Y%m%d).tar.gz $HOME/neo4j/data

# Restart container
docker start kernel-graphrag-neo4j
```

**Option 3: Cypher Export (Small databases)**

```cypher
// Export all nodes and relationships to CSV
CALL apoc.export.csv.all('/var/lib/neo4j/import/export.csv', {})
YIELD file, source, format, nodes, relationships
RETURN file, nodes, relationships;
```

### Restore Database

**From dump file**:

```bash
# Stop Neo4j
sudo systemctl stop neo4j

# Delete existing database
sudo rm -rf /var/lib/neo4j/data/databases/neo4j

# Restore from dump
sudo neo4j-admin database load neo4j \
  --from-path=/backup/neo4j-20250127.dump

# Start Neo4j
sudo systemctl start neo4j
```

**From Docker volume**:

```bash
# Stop and remove container
docker stop kernel-graphrag-neo4j
docker rm kernel-graphrag-neo4j

# Restore data directory
tar -xzf neo4j-backup-20250127.tar.gz -C $HOME/neo4j/

# Recreate container
docker run -d \
  --name kernel-graphrag-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -v $HOME/neo4j/data:/data \
  neo4j:5.14
```

---

## Database Maintenance

### Clear All Data

**⚠️ WARNING: This deletes everything!**

```cypher
// Delete all nodes and relationships
MATCH (n) DETACH DELETE n;
```

**Or via CLI**:

```bash
python3 src/main.py ingest fs/ext4 --clear-db
```

### Vacuum Database

```bash
# Stop Neo4j
sudo systemctl stop neo4j

# Compact database (removes deleted records)
sudo neo4j-admin database migrate neo4j

# Start Neo4j
sudo systemctl start neo4j
```

### Check Database Size

```bash
# Ubuntu/Debian
du -sh /var/lib/neo4j/data/databases/neo4j

# Docker
docker exec kernel-graphrag-neo4j du -sh /data/databases/neo4j
```

---

## Security Best Practices

### 1. Change Default Password

```bash
# Set strong password
sudo neo4j-admin dbms set-initial-password "YourStrongPasswordHere"
```

### 2. Restrict Network Access

In `neo4j.conf`:

```conf
# Listen only on localhost (not accessible remotely)
server.default_listen_address=127.0.0.1
```

### 3. Enable HTTPS

```conf
# Enable HTTPS
server.https.enabled=true
server.https.listen_address=:7473

# Specify certificate
server.ssl.policy.https.enabled=true
server.ssl.policy.https.base_directory=/etc/neo4j/certificates
```

### 4. Use Read-Only User for Queries

```cypher
// Create read-only user
CREATE USER analyst SET PASSWORD 'readonly123';
GRANT ROLE reader TO analyst;
```

---

## Resources

- **Neo4j Documentation**: https://neo4j.com/docs/
- **Cypher Manual**: https://neo4j.com/docs/cypher-manual/
- **Performance Guide**: https://neo4j.com/docs/operations-manual/current/performance/
- **Neo4j Community Forum**: https://community.neo4j.com/
