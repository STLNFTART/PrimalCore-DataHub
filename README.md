# PrimalCore-DataHub

A fully realized in-house R&D data integration pipeline leveraging Primal Logic kernels and quantum-inspired algorithms. Connects multiple heterogeneous databases for unified analysis, advanced simulations, and optimized decision-making.

## Overview

This pipeline implements the foundational data infrastructure for the Primal Logic research program, enabling cross-domain analysis and validation of mathematical models with real parameter values.

## Current Configuration: 6 Core Databases

### 1. Redis
- **Purpose**: Fast key-value caching and real-time data exchange
- **Port**: 6379
- **Access**: `redis-cli -a redispw`

### 2. TimescaleDB (PostgreSQL + time-series extensions)
- **Purpose**: Time-series data storage with SQL capabilities
- **Port**: 5433
- **Database**: `telemetry`
- **Table**: `readings(ts timestamptz, k text, v double precision)`
- **Access**: `psql -h localhost -p 5433 -U postgres -d telemetry`

### 3. InfluxDB 2.x
- **Purpose**: High-performance time-series database
- **Port**: 8086
- **Organization**: `Primal_Pipe_Line`
- **Bucket**: `default`
- **Access**: Via InfluxDB CLI or HTTP API

### 4. Neo4j
- **Purpose**: Graph database for relationship mapping
- **Ports**: 7474 (HTTP), 7687 (Bolt)
- **Access**: `http://localhost:7474` or `cypher-shell -u neo4j -p neo4jpass`

### 5. ClickHouse
- **Purpose**: OLAP database for analytical queries
- **Port**: 8123 (HTTP), 9009 (native)
- **Database**: `logs`
- **Table**: `logs.events(ts DateTime, k String, v Float64)`
- **Access**: `clickhouse-client` or `curl http://localhost:8123`

### 6. Qdrant
- **Purpose**: Vector similarity search for embeddings
- **Port**: 6333
- **Collection**: `smoke` (384-dimensional vectors)
- **Access**: HTTP API at `http://localhost:6333`

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
- At least 8GB RAM available
- 20GB free disk space

### Launch All Databases

```bash
# Using Docker Compose
docker-compose up -d

# Using Podman Compose
podman-compose up -d

# Check status
docker-compose ps
# or
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

### Initialize Databases

```bash
# TimescaleDB setup
docker exec -e PGPASSWORD=pgpass primal_timescaledb psql -U postgres -c "CREATE DATABASE telemetry;"
docker exec -e PGPASSWORD=pgpass primal_timescaledb psql -U postgres -d telemetry -c "CREATE EXTENSION IF NOT EXISTS timescaledb; CREATE TABLE IF NOT EXISTS readings(ts timestamptz, k text, v double precision); SELECT create_hypertable('readings','ts', if_not_exists=>true);"

# InfluxDB setup (first time only)
docker exec primal_influxdb influx setup --username admin --password adminpass --org Primal_Pipe_Line --bucket default --force

# ClickHouse setup
docker exec primal_clickhouse clickhouse-client -q "CREATE DATABASE IF NOT EXISTS logs; CREATE TABLE IF NOT EXISTS logs.events(ts DateTime, k String, v Float64) ENGINE=MergeTree ORDER BY ts;"

# Qdrant collection
curl -X PUT 'http://localhost:6333/collections/vectors' \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"size":384,"distance":"Cosine"}}'
```

### Log Data to All Databases

```bash
# Make script executable
chmod +x log_all.sh

# Log a single event (key, value)
./log_all.sh boot 7

# Log custom data
./log_all.sh temperature 23.5
```

## Connection URIs

- **Redis**: `redis://:redispw@localhost:6379`
- **TimescaleDB**: `postgres://postgres:pgpass@localhost:5433/telemetry`
- **InfluxDB**: `http://localhost:8086` (requires token)
- **Neo4j Bolt**: `bolt://neo4j:neo4jpass@localhost:7687`
- **Neo4j HTTP**: `http://localhost:7474`
- **ClickHouse**: `http://localhost:8123`
- **Qdrant**: `http://localhost:6333`

## Architecture

### Current State (6 Databases)
```
┌─────────────────────────────────────────────────┐
│          Primal Logic Core Engine               │
│     (α=0.55, λ=0.115, K=1.47)                  │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴────────┐
       │   log_all.sh   │  ← Unified data ingestion
       └───────┬────────┘
               │
       ┌───────┴────────────────────────┐
       │                                │
   ┌───▼───┐  ┌────▼────┐  ┌────▼────┐ │
   │ Redis │  │TimescaleDB│ InfluxDB │ │
   └───────┘  └──────────┘ └─────────┘ │
       │                                │
   ┌───▼───┐  ┌────▼────┐  ┌────▼────┐ │
   │ Neo4j │  │ClickHouse│ │ Qdrant  │ │
   └───────┘  └──────────┘ └─────────┘ │
                                        │
                  ┌─────────────────────▼──┐
                  │    Analysis Pipeline    │
                  │  Kernel v1, v3, v4     │
                  └────────────────────────┘
```

### Roadmap (50+ Databases)

The architecture is designed to scale to 50+ heterogeneous databases across multiple categories:

1. **Internal/Proprietary** - Simulation logs, kernel datasets, research notes
2. **Cloud Storage** - Google Drive, AWS S3, OneDrive, Dropbox
3. **Version Control** - GitHub, GitLab repositories
4. **Public/Research** - ArXiv, PubMed, NASA datasets
5. **Transactional/IoT** - Sensor streams, CARLA simulation logs
6. **Experimental** - FPGA outputs, quantum simulator data

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
