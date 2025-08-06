import sys
import os
import json

# Ensure the project root (one level above /tests) is in the module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from applitools.images import (
    Eyes,
    Target,
    Configuration
)
from applitools.common import BatchInfo
from applitools.common import MatchLevel

from src.utils.ApplitoolsResultsSerializer import serialize_test_results

def str_to_bool(value) -> bool:
    if isinstance(value, bool):
        return value  # already a boolean, return as-is
    return str(value).strip().lower() in ("true", "1", "yes", "y", "on")

print("-" * 75, file=sys.stderr)
print("\n", file=sys.stderr)
print("TestAnImage.py - Starting script execution", file=sys.stderr)

# Parse arguments
appName = sys.argv[1]
testName = sys.argv[2]
APPLITOOLS_SERVER_URL = sys.argv[3]
APPLITOOLS_API_KEY = sys.argv[4]
viewPortSize = json.loads(sys.argv[5])
baselineEnvName = sys.argv[6]
APP_URL = sys.argv[7]
SELENIUM_BATCH_NAME_SUFFIX = sys.argv[8]
SELENIUM_BATCH_ID = sys.argv[9]
HEADLESS = sys.argv[10].lower() == 'true'
IGNORE_DISPLACEMENT = sys.argv[11].lower() == 'true'
MATCH_LEVEL = sys.argv[12].strip().upper()

print("🔍 Received Parameters", file=sys.stderr)
print(f"{'appName':<18}: {appName}", file=sys.stderr)
print(f"{'testName':<18}: {testName}", file=sys.stderr)
print(f"{'viewPortSize':<18}: {viewPortSize}", file=sys.stderr)
print(f"{'baselineEnvName':<18}: {baselineEnvName}", file=sys.stderr)
print(f"{'APP_URL':<18}: {APP_URL}", file=sys.stderr)
print("-" * 50, file=sys.stderr)


# ─── Configure Applitools with Visual Grid ─────────────────────────────
eyes = Eyes()

config = Configuration()
config.api_key = APPLITOOLS_API_KEY
config.server_url = APPLITOOLS_SERVER_URL
config.app_name = appName
config.test_name = testName
config.baseline_env_name = baselineEnvName
config.ignore_displacements = str_to_bool(IGNORE_DISPLACEMENT)
config.properties.append({
    "name": "Ignore Displacement",
    "value": f"{str_to_bool(IGNORE_DISPLACEMENT)}",
})
config.properties.append({
    "name": "Match Level",
    "value": f"{MatchLevel[MATCH_LEVEL.upper()]}",
})
config.match_level = MatchLevel[MATCH_LEVEL.upper()]
selenium_batchInfo = BatchInfo()
selenium_batchInfo.name = f"{appName} - {SELENIUM_BATCH_NAME_SUFFIX}"
selenium_batchInfo.id = SELENIUM_BATCH_ID
config.batch = selenium_batchInfo
config.set_viewport_size({"width": viewPortSize['width'], "height": viewPortSize['height']})
eyes.set_configuration(config)

eyes.open()
eyes.check("Full Image", Target.image(APP_URL).fully(True))
# ─── Get and Print Results ─────────────────────────────────────────
all_test_results = eyes.close(False)
applitools_result = serialize_test_results(all_test_results)
print("📊 Status of comparison against Figma:", file=sys.stderr)
print(json.dumps(applitools_result, indent=4), file=sys.stderr)


# Return values in the expected format
browser_output = {
    "appName": appName,
    "testName": testName,
    "baselineEnvName": baselineEnvName,
    "status": applitools_result,
    "viewPortSize": viewPortSize,
    "APP_URL": APP_URL,
    "all_test_results": applitools_result
}
print(json.dumps(browser_output))

