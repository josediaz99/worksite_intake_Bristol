"""
gunicorn.conf.py
workers, bind address, og paths for production
"""
bind         = "127.0.0.1:8000"
workers      = 4                  # 2 × CPU cores + 1 is a common rule
worker_class = "sync"
timeout      = 30
keepalive    = 5
accesslog    = "/var/log/gunicorn/access.log"
errorlog     = "/var/log/gunicorn/error.log"
loglevel     = "info"