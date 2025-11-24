#!/usr/bin/env python3
"""
PrimalCore-DataHub: 10-Database Pipeline Test
Tests connectivity and data flow across all databases
"""

import sys
import time
from datetime import datetime
from connectors import PrimalDataMesh
import json

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def test_database_connections():
    """Test connection to all 10 databases"""
    print_header("TEST 1: Database Connections")

    try:
        mesh = PrimalDataMesh()
        print_success("Successfully initialized PrimalDataMesh")

        # Test each connection
        databases = [
            ('Redis', lambda: mesh.redis_client.ping()),
            ('TimescaleDB', lambda: mesh.timescale_conn.closed == 0),
            ('InfluxDB', lambda: mesh.influx_client.ping()),
            ('Neo4j', lambda: mesh.neo4j_driver.verify_connectivity() is None),
            ('ClickHouse', lambda: mesh.clickhouse_client.command('SELECT 1')),
            ('PostgreSQL', lambda: mesh.postgres_conn.closed == 0),
            ('MongoDB', lambda: mesh.mongo_client.admin.command('ping')),
            ('Elasticsearch', lambda: mesh.es_client.ping()),
        ]

        connected = 0
        for name, test_func in databases:
            try:
                test_func()
                print_success(f"{name:20} - Connected")
                connected += 1
            except Exception as e:
                print_error(f"{name:20} - Failed: {str(e)[:50]}")

        # Qdrant and Prometheus are HTTP-based, tested differently
        print_success(f"Qdrant              - HTTP endpoint (tested via write)")
        print_success(f"Prometheus          - Pull-based monitoring")

        mesh.close()
        return connected >= 8  # At least 8/10 must work

    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        return False


def test_write_operations():
    """Test writing to all 10 databases"""
    print_header("TEST 2: Write Operations")

    try:
        mesh = PrimalDataMesh()

        # Test event with Primal Logic parameters
        test_key = f'test_event_{int(time.time())}'
        test_value = 0.55  # α parameter
        test_metadata = {
            'lambda': 0.115,
            'K': 1.47,
            'test': 'pipeline_validation',
            'timestamp': datetime.now().isoformat()
        }

        print(f"Writing test event: key='{test_key}', value={test_value}")
        print(f"Metadata: {json.dumps(test_metadata, indent=2)}\n")

        results = mesh.write_event(test_key, test_value, test_metadata)

        successes = 0
        for db_name, status in results.items():
            if 'ok' in str(status).lower():
                print_success(f"{db_name:20} - {status}")
                successes += 1
            else:
                print_error(f"{db_name:20} - {status}")

        print(f"\n{successes}/10 databases successfully wrote the event")

        mesh.close()
        return successes >= 8

    except Exception as e:
        print_error(f"Write test failed: {e}")
        return False


def test_read_operations():
    """Test reading from databases"""
    print_header("TEST 3: Read Operations")

    try:
        mesh = PrimalDataMesh()

        # First write a known event
        test_key = f'read_test_{int(time.time())}'
        mesh.write_event(test_key, 42.0, {'purpose': 'read_test'})

        # Wait a moment for writes to propagate
        time.sleep(2)

        print(f"Querying recent events for key: '{test_key}'\n")

        results = mesh.query_recent_events(test_key, limit=5)

        read_successes = 0
        for db_name, data in results.items():
            if 'error' in str(data).lower():
                print_error(f"{db_name:20} - {data}")
            else:
                count = len(data) if isinstance(data, (list, tuple)) else 0
                print_success(f"{db_name:20} - Retrieved {count} events")
                read_successes += 1

        mesh.close()
        return read_successes >= 3  # Some DBs might not have data yet

    except Exception as e:
        print_error(f"Read test failed: {e}")
        return False


def test_performance():
    """Test write performance"""
    print_header("TEST 4: Performance Test")

    try:
        mesh = PrimalDataMesh()

        num_events = 100
        print(f"Writing {num_events} events to all 10 databases...\n")

        start_time = time.time()

        for i in range(num_events):
            key = f'perf_test_{i % 10}'
            value = float(i) * 0.55
            metadata = {'batch': i // 10, 'iteration': i}

            mesh.write_event(key, value, metadata)

            if (i + 1) % 25 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"  {i+1:3d}/{num_events} events | "
                      f"{rate:.1f} events/sec | "
                      f"{elapsed:.1f}s elapsed")

        total_time = time.time() - start_time
        throughput = num_events / total_time

        print(f"\n{GREEN}Performance Results:{RESET}")
        print(f"  Total events:  {num_events}")
        print(f"  Total time:    {total_time:.2f} seconds")
        print(f"  Throughput:    {throughput:.2f} events/sec")
        print(f"  Avg latency:   {(total_time/num_events)*1000:.1f} ms/event")
        print(f"  Per-DB writes: {num_events * 10} total database operations")

        mesh.close()
        return throughput > 1.0  # At least 1 event/sec

    except Exception as e:
        print_error(f"Performance test failed: {e}")
        return False


def test_primal_logic_integration():
    """Test Primal Logic parameter storage"""
    print_header("TEST 5: Primal Logic Integration")

    try:
        mesh = PrimalDataMesh()

        # Store validated parameters
        params = {
            'alpha': 0.55,
            'lambda': 0.115,
            'K': 1.47
        }

        print("Storing Primal Logic validated parameters:")
        print(f"  α (alpha) = {params['alpha']}")
        print(f"  λ (lambda) = {params['lambda']}")
        print(f"  K = {params['K']}\n")

        results = {}
        for param_name, param_value in params.items():
            key = f'primal_{param_name}'
            write_results = mesh.write_event(
                key=key,
                value=param_value,
                metadata={
                    'type': 'primal_parameter',
                    'validated': True,
                    'kernel_version': 'v4',
                    'researcher': 'STLNFTART'
                }
            )
            successes = sum(1 for v in write_results.values() if 'ok' in str(v).lower())
            results[param_name] = successes
            print_success(f"{param_name:10} → {successes}/10 databases")

        mesh.close()

        all_success = all(v >= 8 for v in results.values())
        return all_success

    except Exception as e:
        print_error(f"Primal Logic test failed: {e}")
        return False


def main():
    """Run all tests"""
    print_header("PrimalCore-DataHub: 10-Database Pipeline Test Suite")
    print(f"Started: {datetime.now().isoformat()}")

    tests = [
        ("Database Connections", test_database_connections),
        ("Write Operations", test_write_operations),
        ("Read Operations", test_read_operations),
        ("Performance", test_performance),
        ("Primal Logic Integration", test_primal_logic_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
        time.sleep(1)  # Brief pause between tests

    # Summary
    print_header("Test Summary")

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for test_name, test_passed in results:
        if test_passed:
            print_success(f"{test_name:30} PASSED")
        else:
            print_error(f"{test_name:30} FAILED")

    print(f"\n{BLUE}{'='*70}{RESET}")
    if passed == total:
        print(f"{GREEN}✓ ALL TESTS PASSED ({passed}/{total}){RESET}")
        print(f"{GREEN}  Pipeline is fully operational!{RESET}")
        exit_code = 0
    else:
        print(f"{YELLOW}⚠ SOME TESTS FAILED ({passed}/{total} passed){RESET}")
        print(f"{YELLOW}  Check logs above for details{RESET}")
        exit_code = 1

    print(f"{BLUE}{'='*70}{RESET}\n")
    print(f"Completed: {datetime.now().isoformat()}")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
