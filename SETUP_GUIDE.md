# PrimalCore-DataHub Setup Guide

Quick guide to get all 10 databases running and test the connector layer.

## Prerequisites

- Docker or Podman installed
- Python 3.9+ with pip
- 8-12 GB available RAM
- 50-100 GB disk space

## Step 1: Start All 10 Databases

```bash
cd /home/user/PrimalCore-DataHub

# Start all containers
podman-compose up -d

# Or with Docker:
docker-compose up -d

# Verify all containers are running
podman ps
```

You should see 10 containers running:
1. primal_redis (port 6379)
2. primal_timescaledb (port 5433)
3. primal_influxdb (port 8086)
4. primal_neo4j (ports 7474, 7687)
5. primal_clickhouse (ports 8123, 9009)
6. primal_qdrant (port 6333)
7. primal_postgres (port 5432)
8. primal_mongodb (port 27017)
9. primal_elasticsearch (ports 9200, 9300)
10. primal_prometheus (port 9090)

## Step 2: Initialize Databases

### PostgreSQL (Core)
```bash
# Initialize PostgreSQL schema
podman exec -i primal_postgres psql -U primal_user -d primal_core < init_postgres.sql

# Verify
podman exec primal_postgres psql -U primal_user -d primal_core -c "SELECT COUNT(*) FROM events;"
```

### TimescaleDB
```bash
# Create hypertable for time-series data
podman exec primal_timescaledb psql -U postgres -d telemetry -c "
CREATE TABLE IF NOT EXISTS readings (
    ts TIMESTAMP NOT NULL,
    k VARCHAR(255) NOT NULL,
    v DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('readings', 'ts', if_not_exists => TRUE);
"
```

### InfluxDB
```bash
# Get InfluxDB setup token
podman exec primal_influxdb influx setup \
  --org Primal_Pipe_Line \
  --bucket default \
  --username admin \
  --password primalpass123 \
  --force

# Get the auth token
TOKEN=$(podman exec primal_influxdb influx auth list --json | grep -o '"token":"[^"]*' | head -1 | cut -d'"' -f4)
echo "InfluxDB Token: $TOKEN"
echo "Update this in connectors.py line 45!"
```

### ClickHouse
```bash
# Create database and table
podman exec primal_clickhouse clickhouse-client --query "
CREATE DATABASE IF NOT EXISTS logs;
CREATE TABLE IF NOT EXISTS logs.events (
    ts DateTime,
    k String,
    v Float64
) ENGINE = MergeTree()
ORDER BY ts;
"
```

### Qdrant
```bash
# Create vector collection
curl -X PUT http://localhost:6333/collections/smoke \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 4,
      "distance": "Cosine"
    }
  }'
```

### MongoDB
```bash
# MongoDB auto-creates databases and collections on first write
# Verify connection:
podman exec primal_mongodb mongosh -u primal_admin -p mongopass --eval "db.adminCommand('listDatabases')"
```

### Elasticsearch
```bash
# Verify Elasticsearch is running
curl -X GET http://localhost:9200/_cluster/health?pretty

# Create index template
curl -X PUT http://localhost:9200/primal-events \
  -H 'Content-Type: application/json' \
  -d '{
    "mappings": {
      "properties": {
        "ts": {"type": "date"},
        "key": {"type": "keyword"},
        "value": {"type": "float"},
        "ts_unix": {"type": "long"},
        "metadata": {"type": "object"}
      }
    }
  }'
```

## Step 3: Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

## Step 4: Configure Connectors

1. **Update InfluxDB token** in `connectors.py` line 45:
   ```python
   token='YOUR_INFLUX_TOKEN_FROM_STEP_2',
   ```

2. **Verify .env credentials** match your setup (should be fine if using defaults)

## Step 5: Test the Pipeline

### Basic Test
```bash
# Run the built-in test
python3 connectors.py
```

Expected output:
```
=== PrimalCore-DataHub: 10-Database Write Test ===

Writing event to all 10 databases...

Write results:
{
  "redis": "ok",
  "timescale": "ok",
  "influx": "ok",
  "neo4j": "ok",
  "clickhouse": "ok",
  "qdrant": "ok",
  "postgres": "ok",
  "mongodb": "ok",
  "elasticsearch": "ok",
  "prometheus": "ok (pull-based, no push needed)"
}

✓ Successfully wrote to 10/10 databases
```

### Custom Test
```python
from connectors import PrimalDataMesh
import json

# Initialize
mesh = PrimalDataMesh()

# Write Primal Logic event
results = mesh.write_event(
    key='primal_alpha',
    value=0.55,  # α parameter
    metadata={
        'lambda': 0.115,
        'K': 1.47,
        'experiment': 'kernel_v4',
        'researcher': 'STLNFTART'
    }
)

print(json.dumps(results, indent=2))

# Query back
recent = mesh.query_recent_events('primal_alpha', limit=10)
print(json.dumps(recent, indent=2, default=str))

mesh.close()
```

## Step 6: Verify Data in Each Database

### Redis
```bash
podman exec primal_redis redis-cli -a redispw GET temperature
```

### PostgreSQL
```bash
podman exec primal_postgres psql -U primal_user -d primal_core -c "SELECT * FROM events ORDER BY ts DESC LIMIT 5;"
```

### MongoDB
```bash
podman exec primal_mongodb mongosh -u primal_admin -p mongopass primal_core --eval "db.events.find().sort({ts:-1}).limit(5)"
```

### Elasticsearch
```bash
curl -X GET "http://localhost:9200/primal-events/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match_all": {}}, "size": 5}'
```

### Neo4j
```bash
# Open Neo4j Browser: http://localhost:7474
# Login: neo4j / neo4jpass
# Query: MATCH (e:Event) RETURN e ORDER BY e.ts DESC LIMIT 5
```

### ClickHouse
```bash
podman exec primal_clickhouse clickhouse-client --query "SELECT * FROM logs.events ORDER BY ts DESC LIMIT 5"
```

### TimescaleDB
```bash
podman exec primal_timescaledb psql -U postgres -d telemetry -c "SELECT * FROM readings ORDER BY ts DESC LIMIT 5;"
```

### InfluxDB
```bash
podman exec primal_influxdb influx query 'from(bucket:"default") |> range(start:-1h) |> limit(n:5)'
```

## Troubleshooting

### Container won't start
```bash
# Check logs
podman logs primal_<container_name>

# Restart specific container
podman restart primal_<container_name>

# Rebuild if needed
podman-compose down
podman-compose up -d
```

### Port conflicts
```bash
# Check what's using a port
sudo lsof -i :6379  # Example for Redis port

# Kill conflicting process or change port in docker-compose.yml
```

### Connection errors in connectors.py
- Verify all containers are running: `podman ps`
- Check .env credentials match docker-compose.yml
- Ensure ports aren't blocked by firewall
- Try `localhost` instead of `127.0.0.1` (or vice versa)

### Out of memory
```bash
# Set memory limits in docker-compose.yml
services:
  redis:
    deploy:
      resources:
        limits:
          memory: 512M
```

## Performance Testing

### Load Test Script
```python
from connectors import PrimalDataMesh
import time
import random

mesh = PrimalDataMesh()

print("Starting load test: 1000 events...")
start = time.time()

for i in range(1000):
    mesh.write_event(
        key=f'load_test_{i % 10}',
        value=random.uniform(0, 100),
        metadata={'batch': i // 100}
    )

    if i % 100 == 0:
        print(f"  {i} events written...")

elapsed = time.time() - start
print(f"\n✓ Completed in {elapsed:.2f}s")
print(f"  Throughput: {1000/elapsed:.2f} events/sec")

mesh.close()
```

## Monitoring

### Check All Database Sizes
```bash
# PostgreSQL
podman exec primal_postgres psql -U primal_user -d primal_core -c "\l+"

# MongoDB
podman exec primal_mongodb mongosh -u primal_admin -p mongopass --eval "db.stats()"

# Redis
podman exec primal_redis redis-cli -a redispw INFO memory

# Check disk usage
du -sh volumes/*
```

### Prometheus Metrics
Open http://localhost:9090 and query:
- `up` - See all targets
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage

### Grafana Dashboard (Optional)
```bash
# Add Grafana to docker-compose.yml
podman run -d -p 3000:3000 grafana/grafana

# Open http://localhost:3000
# Add Prometheus as data source: http://primal_prometheus:9090
```

## Next Steps

1. ✅ All 10 databases running
2. ✅ Connector layer tested
3. 🔄 Run end-to-end performance tests
4. ⏭️ Plan Batch 3: Kafka + DuckDB + event sourcing
5. ⏭️ Build data catalog
6. ⏭️ Scale to 50+ databases

## Resources

- Docker Compose docs: https://docs.docker.com/compose/
- Podman Compose: https://github.com/containers/podman-compose
- Database-specific docs in SCALING_ROADMAP.md

## Support

Issues or questions? Check:
1. Container logs: `podman logs <container_name>`
2. Network connectivity: `podman network inspect primal-network`
3. Resource usage: `podman stats`
