import sys
import json
import os
import requests
import uuid
from io import BytesIO
from PIL import Image
from applitools.images import Eyes, Target
from applitools.images import BatchInfo as images_BatchInfo
from applitools.common.config import Configuration
from applitools.common import RectangleSize

print("-" * 75, file=sys.stderr)
print("\n", file=sys.stderr)
print("LoadFromFigma.py - Starting script execution", file=sys.stderr)

# Parse arguments
FIGMA_TOKEN = sys.argv[1]
FIGMA_FILE_KEY = sys.argv[2]
FIGMA_NODE_ID = sys.argv[3]
APPLITOOLS_SERVER_URL = sys.argv[4]
APPLITOOLS_API_KEY = sys.argv[5]
IMAGES_BATCH_NAME_SUFFIX = sys.argv[6] if len(sys.argv) > 6 else "NOT_SET"
IMAGES_BATCH_ID = sys.argv[7] if len(sys.argv) > 7 else str(uuid.uuid4())
VIEWPORT_SIZE = sys.argv[8]

print(f"Loading file FIGMA_FILE_KEY={FIGMA_FILE_KEY} from FIGMA_NODE_ID={FIGMA_NODE_ID} and uploading to Applitools server: {APPLITOOLS_SERVER_URL} with view port: {VIEWPORT_SIZE}", file=sys.stderr)

# ─── Configuration ─────────────────────────────────────────────────────────────
file_endpoint = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}"
file_resp     = requests.get(
    file_endpoint,
    headers={"X-Figma-Token": FIGMA_TOKEN}
)
file_resp.raise_for_status()
# — READ the top-level "name", not the document.name
app_name = file_resp.json().get("name", "<unnamed project>")
print(f"App Name      : {app_name}", file=sys.stderr)

# ─── 1. Get node dimensions ────────────────────────────────────────────────────
nodes_endpoint = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}/nodes"
resp = requests.get(
    nodes_endpoint,
    headers={"X-Figma-Token": FIGMA_TOKEN},
    params={"ids": FIGMA_NODE_ID}
)
resp.raise_for_status()
node_doc = resp.json()["nodes"][FIGMA_NODE_ID]["document"]
test_name     = node_doc.get("name", "<unnamed>")
print(f"Test Name: {test_name}\n", file=sys.stderr)
if VIEWPORT_SIZE.strip().upper() == "USE_SOURCE":
    bbox     = node_doc["absoluteBoundingBox"]
    width, height = bbox["width"], bbox["height"]
else:
    width, height = map(int, VIEWPORT_SIZE.lower().strip().split('x'))

print(f"Node {FIGMA_NODE_ID} dimensions → width: {width}px, height: {height}px", file=sys.stderr)
baselineEnvName = str(app_name) + "_" + str(test_name) + "_" + str(str(width).split('.', 1)[0])
print(f"Basline Env Name      : {baselineEnvName}", file=sys.stderr)

# ─── 2. Get the export URL for the node as PNG ────────────────────────────────
images_endpoint = f"https://api.figma.com/v1/images/{FIGMA_FILE_KEY}"
resp = requests.get(
    images_endpoint,
    headers={"X-Figma-Token": FIGMA_TOKEN},
    params={"ids": FIGMA_NODE_ID, "format": "png", "scale": 2}
)
resp.raise_for_status()
image_url = resp.json()["images"].get(FIGMA_NODE_ID)
if not image_url:
    raise RuntimeError(f"No image URL returned for node {FIGMA_NODE_ID}")

# ─── 3. Download and load into PIL ────────────────────────────────────────────
img_resp = requests.get(image_url)
img_resp.raise_for_status()
figma_image = Image.open(BytesIO(img_resp.content))

# ─── Initialise and configure Eyes ─────────────────────────────────────────
eyes                     = Eyes()
config                   = Configuration()
images_batchInfo         = images_BatchInfo()
images_batchInfo.name    = app_name + IMAGES_BATCH_NAME_SUFFIX
images_batchInfo.id      = IMAGES_BATCH_ID
config.batch             = images_batchInfo
config.api_key           = APPLITOOLS_API_KEY
config.server_url        = APPLITOOLS_SERVER_URL
config.app_name          = app_name
config.test_name         = test_name
config.host_app          = "figma"
config.baseline_env_name = baselineEnvName
config.viewport_size     = RectangleSize(width=(width), height=(height))
eyes.set_configuration(config)

# ─── Run the visual check ─────────────────────────────────────────────────
try:
    eyes.open()
    eyes.check("Figma Node Image", Target.image(figma_image))
    results = eyes.close(False)
except Exception as e:
    print(f"Abort the test: {e}", file=sys.stderr)
    eyes.abort()

print("-" * 75, file=sys.stderr)
print("\n", file=sys.stderr)

# Return values in the expected format
figma_output = {
    "appName": app_name,
    "testName": test_name,
    "viewPortSize": {"width": width, "height": height},
    "baselineEnvName": baselineEnvName,
    "uploadFromFigmaResults": {
        "name": results.name if 'results' in locals() else "N/A",
        "status": results.status.value if 'results' in locals() else "N/A",
        "url": results.url
    }
}
print(json.dumps(figma_output))
