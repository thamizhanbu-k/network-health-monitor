import os
import json
import subprocess
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

# Read config from environment variables (ConfigMap in K8s)
APP_NAME = os.environ.get('APP_NAME', 'Network Health Monitor')
APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
ENV = os.environ.get('ENVIRONMENT', 'development')

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
    return jsonify({
        'status': 'healthy',
        'app': APP_NAME,
        'version': APP_VERSION,
        'environment': ENV,
        'timestamp': datetime.now().isoformat(),
        'disk': get_disk_usage(),
        'memory': get_memory_usage()
    })

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'app': APP_NAME,
        'version': APP_VERSION,
        'environment': ENV,
        'uptime': 'running'})

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': f'Welcome to {APP_NAME}',
        'endpoints': ['/health', '/status']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)