from ..logging_config import setup_logging

# Initialize logging before creating app
setup_logging()

from . import create_app

app = create_app()

