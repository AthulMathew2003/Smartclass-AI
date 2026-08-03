import logging
import sys
from app.core.config import settings

# Determine log level based on environment
LOG_LEVEL = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

# Logging Configuration
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Reusable Logger Instance
logger = logging.getLogger("smartclass_ai")
