import sys
import json
import os
import requests
import uuid

# Ensure the project root (one level above /tests) is in the module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from io import BytesIO
from PIL import Image
from applitools.images import Eyes, Target
from applitools.images import BatchInfo as images_BatchInfo
from applitools.common.config import Configuration
from applitools.common import RectangleSize
from src.utils.applitools_results_serializer import serialize_test_results

print("\n", file=sys.stderr)
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

print(f"\nLoading file FIGMA_FILE_KEY={FIGMA_FILE_KEY} from FIGMA_NODE_ID={FIGMA_NODE_ID} and uploading to Applitools server: {APPLITOOLS_SERVER_URL} with view port: {VIEWPORT_SIZE}", file=sys.stderr)

# ─── Configuration ─────────────────────────────────────────────────────────────
file_endpoint = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}"
file_resp     = requests.get(
    file_endpoint,
    headers={"X-Figma-Token": FIGMA_TOKEN}
)
file_resp.raise_for_status()
# — READ the top-level "name", not the document.name
app_name = file_resp.json().get("name", "<unnamed project>")

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
if VIEWPORT_SIZE.strip().upper() == "USE_SOURCE":
    bbox     = node_doc["absoluteBoundingBox"]
    use_width, use_height = bbox["width"], bbox["height"]
else:
    use_width, use_height = map(int, VIEWPORT_SIZE.lower().strip().split('x'))

baselineEnvName = str(app_name) + "_" + str(test_name) + "_" + str(str(use_width).split('.', 1)[0])

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

# Step 4: Resize while preserving aspect ratio
actual_width = figma_image.size[0]
actual_height = figma_image.size[1]
w_percent = use_width / float(actual_width)
target_height = int(float(actual_height) * w_percent)

resized_img = figma_image.resize((use_width, target_height))

print(f"App Name                : {app_name}", file=sys.stderr)
print(f"Test Name               : {test_name}", file=sys.stderr)
print(f"Node                    : {FIGMA_NODE_ID}", file=sys.stderr)
print(f"Original dimensions     : {actual_width}x{actual_height}", file=sys.stderr)
print(f"Using dimensions        : {use_width}x{use_height}", file=sys.stderr)
print(f"Baseline Env Name       : {baselineEnvName}", file=sys.stderr)

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
config.viewport_size     = RectangleSize(width=(use_width), height=(use_height))
eyes.set_configuration(config)

# ─── Run the visual check ─────────────────────────────────────────────────
try:
    eyes.open()
    print(f"Checking Figma Node {FIGMA_NODE_ID} with dimensions {use_width}x{use_height}", file=sys.stderr)
    eyes.check("Figma Node Image", Target.image(resized_img))
    all_test_results = eyes.close(False)
    applitools_result = serialize_test_results(all_test_results)
    print("📊 Status of uploading Figma image to Applitools:", file=sys.stderr)
    print(json.dumps(applitools_result, indent=4), file=sys.stderr)
except Exception as e:
    print(f"Abort the test: {e}", file=sys.stderr)
    eyes.abort()

print("-" * 75, file=sys.stderr)
print("\n", file=sys.stderr)

# Return values in the expected format
figma_output = {
    "appName": app_name,
    "testName": test_name,
    "viewPortSize": {"width": use_width, "height": use_height},
    "baselineEnvName": baselineEnvName,
    "uploadFromFigmaResults": {
        "name": all_test_results.name if 'results' in locals() else "N/A",
        "status": all_test_results.status.value if 'results' in locals() else "N/A",
        "url": all_test_results.url,
        "all_test_results": applitools_result
    }
}
print(json.dumps(figma_output))
# print(json.dumps(figma_output, indent=4, default=str))
