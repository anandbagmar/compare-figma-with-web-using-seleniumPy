import sys
import json
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from applitools.selenium import (
    Eyes,
    Target,
    Configuration
)
from applitools.common import BatchInfo
from applitools.common import TestResults

def serialize_test_results(results: TestResults) -> dict:
    return {
        "name": results.name,
        "app_name": results.app_name,
        "status": str(results.status),  # fix for TestResultsStatus
        "url": results.url,
        "is_new": results.is_new,
        "is_different": results.is_different,
        "is_aborted": results.is_aborted,
        "host_display_size": {
            "width": results.host_display_size.width,
            "height": results.host_display_size.height
        } if results.host_display_size else None,
        "matches": results.matches,
        "mismatches": results.mismatches,
        "missing": results.missing,
    }

print("-" * 75, file=sys.stderr)
print("\n", file=sys.stderr)
print("TestInBrowser.py - Starting script execution", file=sys.stderr)

# Parse arguments
appName = sys.argv[1]
testName = sys.argv[2]
APPLITOOLS_API_KEY = sys.argv[3]
viewPortSize = json.loads(sys.argv[4])
baselineEnvName = sys.argv[5]
APP_URL = sys.argv[6]
SELENIUM_BATCH_NAME_SUFFIX = sys.argv[7] if len(sys.argv) > 6 else "NOT_SET"
SELENIUM_BATCH_ID = sys.argv[8] if len(sys.argv) > 7 else str(uuid.uuid4())

print("TestInBrowser.py - Received Parameters:", file=sys.stderr)
print(f"appName: {appName}", file=sys.stderr)
print(f"testName: {testName}", file=sys.stderr)
print(f"viewPortSize: {viewPortSize}", file=sys.stderr)
print(f"baselineEnvName: {baselineEnvName}", file=sys.stderr)
print(f"APP_URL: {APP_URL}", file=sys.stderr)

# ─── Configure Selenium WebDriver ──────────────────────────────────────
chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(service=ChromeService(), options=chrome_options)

# ─── Configure Applitools with Visual Grid ─────────────────────────────
eyes = Eyes()

config = Configuration()
config.api_key = APPLITOOLS_API_KEY
config.app_name = appName
config.test_name = testName
config.baseline_env_name = baselineEnvName
selenium_batchInfo = BatchInfo()
selenium_batchInfo.name = f"{appName} - {SELENIUM_BATCH_NAME_SUFFIX}"
selenium_batchInfo.id = SELENIUM_BATCH_ID
config.batch = selenium_batchInfo
config.set_viewport_size({"width": viewPortSize['width'], "height": viewPortSize['height']})
eyes.set_configuration(config)

# ─── Run Test ──────────────────────────────────────────────────────────
try:
    driver.get(APP_URL)
    eyes.open(driver=driver)
    eyes.check("Full Window", Target.window().fully(True))

    # ─── Get and Print Results ─────────────────────────────────────────
    all_test_results = eyes.close(False)
    applitools_result = serialize_test_results(all_test_results)
    print('Figma upload status: ' + json.dumps(applitools_result, indent=4), file=sys.stderr)
finally:
    driver.quit()
    eyes.abort_async()

# Return values in the expected format
browser_output = {
    "appName": appName,
    "testName": testName,
    "baselineEnvName": baselineEnvName,
    "status": applitools_result,
    "viewPortSize": viewPortSize,
    "APP_URL": APP_URL
}
print(json.dumps(browser_output))
