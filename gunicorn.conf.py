# Gunicorn configuration for production deployment
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased timeout for large file processing
keepalive = 5

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 100
max_requests_jitter = 20

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'mutation_analyzer'

# Server mechanics
preload_app = True
daemon = False
pidfile = None
tmp_upload_dir = "/tmp"

# SSL (for production with HTTPS)
keyfile = None
certfile = None

# Worker recycling
worker_tmp_dir = "/dev/shm"

# Graceful timeout for worker shutdown
graceful_timeout = 30

# Environment variables
raw_env = [
    'DATABASE_URL=' + os.environ.get('DATABASE_URL', ''),
    'SESSION_SECRET=' + os.environ.get('SESSION_SECRET', 'change-me'),
]