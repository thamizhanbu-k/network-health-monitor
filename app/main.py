import os
import json
import subprocess
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

# Config from environment variables (ConfigMap in K8s)
APP_NAME = os.environ.get('APP_NAME', 'Network Health Monitor')
APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
ENV = os.environ.get('ENVIRONMENT', 'development')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
CACHE_TTL = 30  # seconds

# Prometheus metrics
REQUEST_COUNT = Counter(
    'health_monitor_requests_total',
    'Total requests by endpoint',
    ['endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'health_monitor_request_duration_seconds',
    'Request latency',
    ['endpoint']
)
CACHE_HITS = Counter('health_monitor_cache_hits_total', 'Cache hits')
CACHE_MISSES = Counter('health_monitor_cache_misses_total', 'Cache misses')
DISK_USAGE_GAUGE = Gauge('health_monitor_disk_usage_percent', 'Disk usage %')
MEMORY_USED_GAUGE = Gauge('health_monitor_memory_used_gb', 'Memory used')

# Connect to Redis with graceful fallback
def get_redis_client():
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=2
        )
        client.ping()
        return client
    except Exception:
        return None

def get_disk_usage():
    result = subprocess.run(
        ['df', '-h', '/'],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split('\n')
    if len(lines) > 1:
        parts = lines[1].split()
        return {
            'total': parts[1],
            'used': parts[2],
            'available': parts[3],
            'usage_percent': parts[4]
        }
    return {}

def get_memory_usage():
    result = subprocess.run(
        ['free', '-h'],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split('\n')
    if len(lines) > 1:
        parts = lines[1].split()
        return {
            'total': parts[1],
            'used': parts[2],
            'free': parts[3]
        }
    return {}

@app.route('/health', methods=['GET'])
def health():
    start_time = time.time()
    cache_key = 'health_data'
    r = get_redis_client()

    # Try to get from Redis cache first
    if r:
        cached = r.get(cache_key)
        if cached:
            data = json.loads(cached)
            data['cache'] = 'hit'
            CACHE_HITS.inc()
            REQUEST_COUNT.labels(endpoint='/health', status='200').inc()
            REQUEST_LATENCY.labels(endpoint='/health').observe(time.time() - start_time)
            return jsonify(data)

    # Cache miss or Redis unavailable — compute fresh
    disk = get_disk_usage()
    memory = get_memory_usage()

    # Update gauges with numeric values
    try:
        DISK_USAGE_GAUGE.set(float(disk.get('usage_percent', '0%').replace('%', '')))
    except Exception:
        pass
    try:
        MEMORY_USED_GAUGE.set(float(memory.get('used', '0').replace('Gi', '').replace('Mi', '').replace('G', '').replace('M', '')))
    except Exception:
        pass

    data = {
        'status': 'healthy',
        'app': APP_NAME,
        'version': APP_VERSION,
        'environment': ENV,
        'timestamp': datetime.now().isoformat(),
        'disk': disk,
        'memory': memory,
        'cache': 'miss'
    }

    CACHE_MISSES.inc()

    # Store in Redis if available
    if r:
        r.setex(cache_key, CACHE_TTL, json.dumps(data))

    REQUEST_COUNT.labels(endpoint='/health', status='200').inc()
    REQUEST_LATENCY.labels(endpoint='/health').observe(time.time() - start_time)
    return jsonify(data)

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'app': APP_NAME,
        'version': APP_VERSION,
        'environment': ENV,
        'uptime': 'running',
        'redis': 'connected' if get_redis_client() else 'unavailable'
    })

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': f'Welcome to {APP_NAME}',
        'endpoints': ['/health', '/status']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)