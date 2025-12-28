import json
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.join(os.getcwd(), 'apps/backend/src'))

from kashat.api import create_app

app = create_app()

with open('apps/web/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)

print("OpenAPI spec generated at apps/web/openapi.json")
