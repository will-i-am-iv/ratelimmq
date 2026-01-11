import logging, sys, queue, threading
import structlog

# 1. Configure a thread-based queue handler to avoid blocking the event loop
log_queue = queue.Queue()
# Define a handler that writes to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(message)s"))
# Define a queue handler that sends log records to the queue
queue_handler = logging.handlers.QueueHandler(log_queue)
# The queue listener will read from the queue and use the console handler to actually log
queue_listener = logging.handlers.QueueListener(log_queue, console_handler)
queue_listener.setDaemon(True)
queue_listener.start()

# 2. Set up the root logger to use the queue handler
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(queue_handler)
# (Optionally disable propagation on third-party loggers if needed)

# 3. Configure structlog to output JSON to the root logger
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,            # Respect logging level
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"), # Add timestamp in ISO format
        structlog.processors.JSONRenderer()          # Output as JSON
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger, 
    cache_logger_on_first_use=True
)

# Create a module-level logger for convenience
logger = structlog.get_logger("ratelimmq")
logger.info("Logging initialized", event="startup")
