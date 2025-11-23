#!/usr/bin/env python3
"""
PrimalCore-DataHub Database Connectors
Enables data flow between all 6 databases
"""

import redis
import psycopg2
from influxdb_client import InfluxDBClient
from neo4j import GraphDatabase
import clickhouse_connect
import requests
from datetime import datetime
from typing import Dict, Any, List
import json


class PrimalDataMesh:
    """Unified interface for all 6 databases"""

    def __init__(self):
        # Redis
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            password='redispw',
            decode_responses=True
        )

        # TimescaleDB (PostgreSQL)
        self.timescale_conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='telemetry',
            user='postgres',
            password='pgpass'
        )

        # InfluxDB
        self.influx_client = InfluxDBClient(
            url='http://localhost:8086',
            token='YOUR_INFLUX_TOKEN',  # Replace with actual token
            org='Primal_Pipe_Line'
        )

        # Neo4j
        self.neo4j_driver = GraphDatabase.driver(
            'bolt://localhost:7687',
            auth=('neo4j', 'neo4jpass')
        )

        # ClickHouse
        self.clickhouse_client = clickhouse_connect.get_client(
            host='localhost',
            port=8123
        )

        # Qdrant (via HTTP API)
        self.qdrant_url = 'http://localhost:6333'


    def write_event(self, key: str, value: float, metadata: Dict[str, Any] = None):
        """Write a single event to all 6 databases"""
        timestamp = datetime.now()
        ts_unix = int(timestamp.timestamp())

        results = {}

        # 1. Redis - Fast cache
        try:
            self.redis_client.set(key, value)
            self.redis_client.hset(f'{key}:meta', mapping=metadata or {})
            results['redis'] = 'ok'
        except Exception as e:
            results['redis'] = f'error: {e}'

        # 2. TimescaleDB - Time-series with SQL
        try:
            cursor = self.timescale_conn.cursor()
            cursor.execute(
                "INSERT INTO readings (ts, k, v) VALUES (%s, %s, %s)",
                (timestamp, key, value)
            )
            self.timescale_conn.commit()
            cursor.close()
            results['timescale'] = 'ok'
        except Exception as e:
            results['timescale'] = f'error: {e}'

        # 3. InfluxDB - High-performance time-series
        try:
            from influxdb_client.client.write_api import SYNCHRONOUS
            write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            point = {
                'measurement': 'readings',
                'tags': {'key': key},
                'fields': {'value': int(value)},
                'time': ts_unix
            }
            write_api.write(bucket='default', record=point)
            results['influx'] = 'ok'
        except Exception as e:
            results['influx'] = f'error: {e}'

        # 4. Neo4j - Graph relationships
        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    "MERGE (e:Event {k: $key}) "
                    "SET e.ts = $ts, e.v = $value "
                    "RETURN e",
                    key=key, ts=ts_unix, value=value
                )
            results['neo4j'] = 'ok'
        except Exception as e:
            results['neo4j'] = f'error: {e}'

        # 5. ClickHouse - Analytics
        try:
            self.clickhouse_client.command(
                f"INSERT INTO logs.events VALUES "
                f"(toDateTime({ts_unix}), '{key}', {value})"
            )
            results['clickhouse'] = 'ok'
        except Exception as e:
            results['clickhouse'] = f'error: {e}'

        # 6. Qdrant - Vector embeddings (mock vector for now)
        try:
            vector = [0.1, 0.2, 0.3, 0.4]  # Replace with real embedding
            response = requests.post(
                f'{self.qdrant_url}/collections/smoke/points?wait=true',
                json={
                    'points': [{
                        'id': ts_unix,
                        'vector': vector,
                        'payload': {'key': key, 'value': value}
                    }]
                }
            )
            results['qdrant'] = 'ok' if response.ok else f'error: {response.status_code}'
        except Exception as e:
            results['qdrant'] = f'error: {e}'

        return results


    def query_recent_events(self, key: str, limit: int = 10) -> Dict[str, List]:
        """Query recent events for a key from all databases"""
        results = {}

        # TimescaleDB
        try:
            cursor = self.timescale_conn.cursor()
            cursor.execute(
                "SELECT ts, k, v FROM readings WHERE k = %s ORDER BY ts DESC LIMIT %s",
                (key, limit)
            )
            results['timescale'] = cursor.fetchall()
            cursor.close()
        except Exception as e:
            results['timescale'] = f'error: {e}'

        # ClickHouse
        try:
            result = self.clickhouse_client.query(
                f"SELECT ts, k, v FROM logs.events WHERE k = '{key}' "
                f"ORDER BY ts DESC LIMIT {limit}"
            )
            results['clickhouse'] = result.result_rows
        except Exception as e:
            results['clickhouse'] = f'error: {e}'

        return results


    def sync_data_cross_database(self, source_db: str, target_db: str, key: str):
        """Synchronize data between two databases"""
        # Example: Sync TimescaleDB → ClickHouse
        if source_db == 'timescale' and target_db == 'clickhouse':
            cursor = self.timescale_conn.cursor()
            cursor.execute("SELECT ts, k, v FROM readings WHERE k = %s", (key,))

            for row in cursor.fetchall():
                ts, k, v = row
                ts_unix = int(ts.timestamp())
                self.clickhouse_client.command(
                    f"INSERT INTO logs.events VALUES "
                    f"(toDateTime({ts_unix}), '{k}', {v})"
                )
            cursor.close()
            return f"Synced {cursor.rowcount} rows"

        return "Sync pattern not implemented"


    def close(self):
        """Close all connections"""
        self.redis_client.close()
        self.timescale_conn.close()
        self.influx_client.close()
        self.neo4j_driver.close()
        self.clickhouse_client.close()


if __name__ == '__main__':
    # Example usage
    mesh = PrimalDataMesh()

    # Write an event to all 6 databases
    results = mesh.write_event('temperature', 23.5, {'sensor': 'lab_01'})
    print("Write results:", json.dumps(results, indent=2))

    # Query data
    recent = mesh.query_recent_events('temperature', limit=5)
    print("\nRecent events:", json.dumps(recent, indent=2, default=str))

    mesh.close()
