# Gunicorn Configuration for LipanAuto Backend (Production)
# Optimized for handling large user loads with async workers

import multiprocessing
import os

# Server Socket
bind = "0.0.0.0:8000"
backlog = 2048  # Maximum pending connections

# Worker Processes
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000  # Maximum simultaneous clients per worker
max_requests = 1000  # Restart workers after 1000 requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to max_requests
timeout = 120  # Worker timeout (2 minutes for slow CAPTCHA solving)
keepalive = 5  # Seconds to wait for requests on a Keep-Alive connection

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "lipanauto-backend"

# Server Mechanics
daemon = False  # Don't daemonize (for Docker/systemd)
pidfile = None  # No PID file needed
user = None     # Run as current user
group = None    # Run as current group
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Preload app for faster worker spawn
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("🚀 Starting LipanAuto Backend Server")
    print(f"📊 Configuration:")
    print(f"   Workers: {workers}")
    print(f"   Worker Class: {worker_class}")
    print(f"   Max Connections/Worker: {worker_connections}")
    print(f"   Timeout: {timeout}s")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("🔄 Reloading LipanAuto Backend Server")

def when_ready(server):
    """Called just after the server is started."""
    print(f"✅ LipanAuto Backend is ready at {bind}")
    print(f"📡 Health check: http://{bind}/health")

def worker_int(worker):
    """Called when a worker receives an INT or QUIT signal."""
    print(f"⚠️  Worker {worker.pid} interrupted")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    print(f"❌ Worker {worker.pid} aborted")
