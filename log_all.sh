#!/bin/bash
set -e
K=${1:-boot}
V=${2:-1}
TS=$(date +%s)

# Redis
podman exec primal_redis redis-cli -a redispw set "$K" "$V" >/dev/null

# TimescaleDB
podman exec -e PGPASSWORD=pgpass primal_timescaledb \
  psql -U postgres -d telemetry -c "INSERT INTO readings VALUES (to_timestamp($TS),'$K',$V);" >/dev/null

# InfluxDB (integer field v)
TOKEN=$(cat ~/.influx_token 2>/dev/null || echo "")
if [ -n "$TOKEN" ]; then
  podman exec -e INFLUX_TOKEN="$TOKEN" primal_influxdb sh -lc \
    "influx write --org Primal_Pipe_Line --bucket default --precision s \"readings,k=$K v=${V}i ${TS}\"" >/dev/null
fi

# ClickHouse
podman exec primal_clickhouse \
  clickhouse-client -q "INSERT INTO logs.events VALUES (toDateTime($TS),'$K',$V);" >/dev/null

# Neo4j
podman exec primal_neo4j \
  cypher-shell -u neo4j -p neo4jpass "MERGE (e:Event {k:\"$K\"}) SET e.ts=$TS, e.v=$V RETURN 1;" >/dev/null

# Qdrant
curl -s -X POST 'http://127.0.0.1:6333/collections/smoke/points?wait=true' \
  -H 'Content-Type: application/json' \
  -d "{\"points\":[{\"id\":$TS,\"vector\":[0.1,0.2,0.3,0.4]}]}" >/dev/null

echo ok
