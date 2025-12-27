#!/bin/bash
set -e

echo "=== Installing Neo4j in Dev Container ==="

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install prerequisites
echo "Installing prerequisites..."
sudo apt-get install -y wget gnupg software-properties-common apt-transport-https ca-certificates curl

# Add Neo4j GPG key
echo "Adding Neo4j repository key..."
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -

# Add Neo4j repository
echo "Adding Neo4j repository..."
echo "deb https://debian.neo4j.com stable latest" | sudo tee /etc/apt/sources.list.d/neo4j.list

# Update package list again
sudo apt-get update

# Install Neo4j
echo "Installing Neo4j..."
sudo apt-get install -y neo4j

# Set initial password
echo "Setting initial Neo4j password..."
sudo neo4j-admin dbms set-initial-password password123

# Enable and start Neo4j service
echo "Enabling and starting Neo4j service..."
sudo systemctl enable neo4j
sudo systemctl start neo4j

# Wait for Neo4j to start
echo "Waiting for Neo4j to start..."
sleep 10

# Check Neo4j status
sudo systemctl status neo4j --no-pager || true

echo ""
echo "=== Neo4j Installation Complete ==="
echo "URL: http://localhost:7474"
echo "Bolt: bolt://localhost:7687"
echo "Username: neo4j"
echo "Password: password123"
echo ""
echo "To check status: sudo systemctl status neo4j"
echo "To view logs: sudo journalctl -u neo4j -f"
