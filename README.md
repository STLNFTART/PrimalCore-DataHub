# PrimalCore-DataHub

A fully realized in-house R&D data integration pipeline leveraging Primal Logic kernels and quantum-inspired algorithms. Connects multiple heterogeneous databases for unified analysis, advanced simulations, and optimized decision-making.

## Overview

This pipeline implements the foundational data infrastructure for the Primal Logic research program, enabling cross-domain analysis and validation of mathematical models with real parameter values.

## Current Configuration: 10 Databases (Batch 1 + Batch 2)

### Batch 1: Foundation (6 Databases)

**1. Redis** - Fast key-value caching
- Port: 6379 | Access: `redis-cli -a redispw`

**2. TimescaleDB** - PostgreSQL + time-series extensions
- Port: 5433 | Database: `telemetry`
- Access: `psql -h localhost -p 5433 -U postgres -d telemetry`

**3. InfluxDB** - High-performance time-series
- Port: 8086 | Org: `Primal_Pipe_Line` | Bucket: `default`

**4. Neo4j** - Graph database
- Ports: 7474 (HTTP), 7687 (Bolt)
- Web UI: `http://localhost:7474`

**5. ClickHouse** - OLAP analytics
- Port: 8123 (HTTP), 9009 (native)
- Database: `logs` | Table: `logs.events`

**6. Qdrant** - Vector embeddings
- Port: 6333 | Collection: `smoke`

### Batch 2: Core Extensions (4 Databases)

**7. PostgreSQL** - Standard relational database
- Port: 5432 | Database: `primal_core`
- Access: `psql -h localhost -U primal_user -d primal_core`

**8. MongoDB** - Document store
- Port: 27017 | Database: `primal_core`
- Access: `mongosh -u primal_admin -p mongopass`

**9. Elasticsearch** - Full-text search
- Port: 9200 (HTTP), 9300 (native)
- Web UI: `http://localhost:9200`

**10. Prometheus** - Metrics monitoring
- Port: 9090
- Web UI: `http://localhost:9090`

## Primal Logic Parameters

The pipeline is configured with the following validated kernel parameters:

- **α (alpha)**: 0.55 - System gain coefficient
- **λ (lambda)**: 0.115 - Decay/damping rate
- **K**: 1.47 - Feedback gain

### Derived Metrics
- **Equilibrium multiplier**: x* ≈ 4.78 × Θ₀
- **2% settling time**: ts ≈ 34.0 time units
- **10-90% rise time**: tr ≈ 19.1 time units
- **Closed-loop pole**: -(λ + αK) ≈ -0.9235 → 8× faster than open-loop

## Quick Start

### Prerequisites
- Docker or Podman installed
- At least 12GB RAM available
- 100GB free disk space
- Python 3.9+ with pip

### Step 1: Launch All 10 Databases

```bash
# Clone and navigate to repository
cd /home/user/PrimalCore-DataHub

# Start all containers
podman-compose up -d  # or docker-compose up -d

# Verify all 10 containers are running
podman ps
```

### Step 2: Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

### Step 3: Initialize Databases

**See SETUP_GUIDE.md for complete initialization instructions.**

Quick initialization:

```bash
# PostgreSQL (core relational)
podman exec -i primal_postgres psql -U primal_user -d primal_core < init_postgres.sql

# TimescaleDB (time-series)
podman exec primal_timescaledb psql -U postgres -d telemetry -c "
  CREATE TABLE IF NOT EXISTS readings(ts TIMESTAMPTZ, k TEXT, v DOUBLE PRECISION);
  SELECT create_hypertable('readings', 'ts', if_not_exists => TRUE);
"

# ClickHouse (analytics)
podman exec primal_clickhouse clickhouse-client --query "
  CREATE DATABASE IF NOT EXISTS logs;
  CREATE TABLE IF NOT EXISTS logs.events(ts DateTime, k String, v Float64)
  ENGINE=MergeTree ORDER BY ts;
"

# Qdrant (vectors)
curl -X PUT http://localhost:6333/collections/smoke \
  -H 'Content-Type: application/json' \
  -d '{"vectors": {"size": 4, "distance": "Cosine"}}'

# Elasticsearch (search)
curl -X PUT http://localhost:9200/primal-events
```

### Step 4: Test the Pipeline

```bash
# Run automated test suite
python3 test_pipeline.py
```

Expected output: "✓ ALL TESTS PASSED (5/5)"

### Step 5: Use the Connector Layer

```python
from connectors import PrimalDataMesh

# Initialize unified interface
mesh = PrimalDataMesh()

# Write to all 10 databases simultaneously
results = mesh.write_event(
    key='primal_alpha',
    value=0.55,
    metadata={'lambda': 0.115, 'K': 1.47}
)

# Query from all databases
recent = mesh.query_recent_events('primal_alpha', limit=10)

mesh.close()
```

## Connection URIs

### Batch 1
- **Redis**: `redis://:redispw@localhost:6379`
- **TimescaleDB**: `postgres://postgres:pgpass@localhost:5433/telemetry`
- **InfluxDB**: `http://localhost:8086` (requires token)
- **Neo4j Bolt**: `bolt://neo4j:neo4jpass@localhost:7687`
- **Neo4j HTTP**: `http://localhost:7474`
- **ClickHouse**: `http://localhost:8123`
- **Qdrant**: `http://localhost:6333`

### Batch 2
- **PostgreSQL**: `postgres://primal_user:primalcorepass@localhost:5432/primal_core`
- **MongoDB**: `mongodb://primal_admin:mongopass@localhost:27017/primal_core`
- **Elasticsearch**: `http://localhost:9200`
- **Prometheus**: `http://localhost:9090`

## Architecture

### Current State (10 Databases - Batch 1 + Batch 2)
```
┌──────────────────────────────────────────────────────────┐
│            Primal Logic Core Engine                      │
│       (α=0.55, λ=0.115, K=1.47)                         │
└────────────────────┬─────────────────────────────────────┘
                     │
            ┌────────▼─────────┐
            │ PrimalDataMesh   │  ← Unified Python Connector
            │  connectors.py   │
            └────────┬─────────┘
                     │
        ┌────────────┴────────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼────────┐
│   BATCH 1 (6)  │          │   BATCH 2 (4)    │
│                │          │                  │
│ • Redis        │          │ • PostgreSQL     │
│ • TimescaleDB  │          │ • MongoDB        │
│ • InfluxDB     │          │ • Elasticsearch  │
│ • Neo4j        │          │ • Prometheus     │
│ • ClickHouse   │          │                  │
│ • Qdrant       │          │                  │
└────────┬───────┘          └─────────┬────────┘
         │                            │
         └──────────┬─────────────────┘
                    │
         ┌──────────▼──────────┐
         │  Analysis Pipeline  │
         │ • Query federation  │
         │ • Cross-DB queries  │
         │ • Kernel v1,v3,v4  │
         └─────────────────────┘
```

### Roadmap (50+ Databases)

**See SCALING_ROADMAP.md for the complete 8-batch expansion plan.**

The architecture scales across 8 batches to 50+ databases:

- **Batch 1-2**: ✅ Complete (10 databases)
- **Batch 3**: Event sourcing (Kafka, Pulsar, RabbitMQ, NATS, DuckDB, SQLite)
- **Batch 4**: Analytics/OLAP (Druid, Pinot, Trino, BigQuery, Greenplum, CrateDB)
- **Batch 5**: Cloud-native (MinIO, Ceph, Cassandra, ScyllaDB, CockroachDB)
- **Batch 6**: Search/Graph (MeiliSearch, Typesense, Dgraph, ArangoDB, OrientDB)
- **Batch 7**: Performance (KeyDB, Memcached, Hazelcast, VictoriaMetrics, QuestDB)
- **Batch 8**: Experimental (SurrealDB, EdgeDB, Neon, FaunaDB, Immudb)

## Project Goals

1. **Unified Discovery Engine**: Enable cross-domain pattern recognition and breakthrough identification
2. **Algorithm Validation**: Stress-test Primal Logic kernels against real and simulated data at scale
3. **Dual-Use Output**: Serve both civilian science and defense/security applications
4. **Scalable Architecture**: Designed for consumer hardware now, scales to HPC clusters
5. **Hidden Couplings**: Reveal invisible links between bio-neural, quantum, and structural systems

## Mathematical Foundation

### Kernel v1 (Linear System)
```
dx/dt = α·Θ(t) - λ·x(t)

Transfer function: G(s) = α/(s + λ)
Equilibrium: x* = (α·Θ₀)/λ
Settling time: ts = ln(50)/λ ≈ 34.0
```

### Kernel v3 (Multivariable)
```
dx/dt = A(t)Θ(t) - Λx(t) + K[yd(t) - Cx(t)]

Stability: Re(λᵢ(Λ + KC)) > 0 for all eigenvalues
```

### Kernel v4 (Reserved for future implementation)

## Development Workflow

1. **Data Collection**: Automated ingestion from all connected databases
2. **Validation**: Cross-reference numeric parameters (α, λ, K) across sources
3. **Transformation**: Convert raw data to LaTeX-ready formats
4. **Analysis**: Run kernel simulations with validated parameters
5. **Export**: Generate PDFs with complete mathematical proofs

## Security Considerations

- All database credentials are stored in `.env` (not committed to git)
- Default passwords should be changed in production
- Network access should be restricted via firewall rules
- Consider enabling TLS/SSL for external access

## Contributing

This is a private research project. For collaboration inquiries, contact the project maintainer.

## License

All rights reserved. Patent pending.

## Authors

- STLNFTART - Primary architect and maintainer
- Primal Logic Research Team

## Acknowledgments

Based on research in quantum-inspired algorithms, bio-neural coupling, and adaptive integral sovereignty frameworks.
