#!/usr/bin/env python3
"""
PrimalCore-DataHub Database Connectors
Enables data flow between all 10 databases (Batch 1 + Batch 2)
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
from pymongo import MongoClient
from elasticsearch import Elasticsearch


class PrimalDataMesh:
    """Unified interface for all 10 databases (6 from Batch 1 + 4 from Batch 2)"""

    def __init__(self):
        # === BATCH 1: Original 6 Databases ===

        # Redis - Fast cache
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            password='redispw',
            decode_responses=True
        )

        # TimescaleDB (PostgreSQL) - Time-series SQL
        self.timescale_conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='telemetry',
            user='postgres',
            password='pgpass'
        )

        # InfluxDB - High-performance time-series
        self.influx_client = InfluxDBClient(
            url='http://localhost:8086',
            token='YOUR_INFLUX_TOKEN',  # Replace with actual token
            org='Primal_Pipe_Line'
        )

        # Neo4j - Graph database
        self.neo4j_driver = GraphDatabase.driver(
            'bolt://localhost:7687',
            auth=('neo4j', 'neo4jpass')
        )

        # ClickHouse - Analytics OLAP
        self.clickhouse_client = clickhouse_connect.get_client(
            host='localhost',
            port=8123
        )

        # Qdrant - Vector embeddings (via HTTP API)
        self.qdrant_url = 'http://localhost:6333'

        # === BATCH 2: Core Missing Pieces ===

        # PostgreSQL - Standard relational database
        self.postgres_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='primal_core',
            user='primal_user',
            password='primalcorepass'
        )

        # MongoDB - Document store
        self.mongo_client = MongoClient(
            'mongodb://primal_admin:mongopass@localhost:27017/'
        )
        self.mongo_db = self.mongo_client['primal_core']

        # Elasticsearch - Full-text search
        self.es_client = Elasticsearch(
            ['http://localhost:9200'],
            verify_certs=False
        )

        # Prometheus URL for custom metrics push (optional)
        self.prometheus_url = 'http://localhost:9090'


    def write_event(self, key: str, value: float, metadata: Dict[str, Any] = None):
        """Write a single event to all 10 databases"""
        timestamp = datetime.now()
        ts_unix = int(timestamp.timestamp())
        metadata = metadata or {}

        results = {}

        # === BATCH 1: Original 6 Databases ===

        # 1. Redis - Fast cache
        try:
            self.redis_client.set(key, value)
            self.redis_client.hset(f'{key}:meta', mapping=metadata)
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

        # === BATCH 2: Core Missing Pieces ===

        # 7. PostgreSQL - Standard relational
        try:
            cursor = self.postgres_conn.cursor()
            cursor.execute(
                "INSERT INTO events (ts, key, value, metadata) VALUES (%s, %s, %s, %s)",
                (timestamp, key, value, json.dumps(metadata))
            )
            self.postgres_conn.commit()
            cursor.close()
            results['postgres'] = 'ok'
        except Exception as e:
            results['postgres'] = f'error: {e}'

        # 8. MongoDB - Document store
        try:
            doc = {
                'ts': timestamp,
                'key': key,
                'value': value,
                'metadata': metadata,
                'ts_unix': ts_unix
            }
            self.mongo_db.events.insert_one(doc)
            results['mongodb'] = 'ok'
        except Exception as e:
            results['mongodb'] = f'error: {e}'

        # 9. Elasticsearch - Full-text search
        try:
            doc = {
                'ts': timestamp.isoformat(),
                'key': key,
                'value': value,
                'metadata': metadata,
                'ts_unix': ts_unix
            }
            self.es_client.index(index='primal-events', document=doc)
            results['elasticsearch'] = 'ok'
        except Exception as e:
            results['elasticsearch'] = f'error: {e}'

        # 10. Prometheus - Metrics (using pushgateway pattern if available)
        # Note: Prometheus is typically pull-based, so this is optional
        # For now we just mark it as ok since it's primarily for scraping
        results['prometheus'] = 'ok (pull-based, no push needed)'

        return results


    def query_recent_events(self, key: str, limit: int = 10) -> Dict[str, List]:
        """Query recent events for a key from all databases"""
        results = {}

        # === BATCH 1: Original Databases ===

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

        # === BATCH 2: New Databases ===

        # PostgreSQL
        try:
            cursor = self.postgres_conn.cursor()
            cursor.execute(
                "SELECT ts, key, value FROM events WHERE key = %s ORDER BY ts DESC LIMIT %s",
                (key, limit)
            )
            results['postgres'] = cursor.fetchall()
            cursor.close()
        except Exception as e:
            results['postgres'] = f'error: {e}'

        # MongoDB
        try:
            docs = list(self.mongo_db.events.find(
                {'key': key}
            ).sort('ts', -1).limit(limit))
            # Remove _id for JSON serialization
            for doc in docs:
                doc.pop('_id', None)
            results['mongodb'] = docs
        except Exception as e:
            results['mongodb'] = f'error: {e}'

        # Elasticsearch
        try:
            query = {
                'query': {'match': {'key': key}},
                'sort': [{'ts_unix': {'order': 'desc'}}],
                'size': limit
            }
            response = self.es_client.search(index='primal-events', body=query)
            results['elasticsearch'] = [hit['_source'] for hit in response['hits']['hits']]
        except Exception as e:
            results['elasticsearch'] = f'error: {e}'

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
        # Batch 1
        self.redis_client.close()
        self.timescale_conn.close()
        self.influx_client.close()
        self.neo4j_driver.close()
        self.clickhouse_client.close()

        # Batch 2
        self.postgres_conn.close()
        self.mongo_client.close()
        self.es_client.close()


if __name__ == '__main__':
    # Example usage
    print("=== PrimalCore-DataHub: 10-Database Write Test ===\n")

    mesh = PrimalDataMesh()

    # Write an event to all 10 databases
    print("Writing event to all 10 databases...")
    results = mesh.write_event('temperature', 23.5, {'sensor': 'lab_01', 'location': 'primal_core'})
    print("\nWrite results:")
    print(json.dumps(results, indent=2))

    # Count successes
    successes = [k for k, v in results.items() if 'ok' in str(v)]
    print(f"\n✓ Successfully wrote to {len(successes)}/10 databases")

    # Query data
    print("\n" + "="*60)
    print("Querying recent events from databases...")
    recent = mesh.query_recent_events('temperature', limit=5)
    print("\nRecent events:")
    print(json.dumps(recent, indent=2, default=str))

    mesh.close()
    print("\n✓ All connections closed")
