
import pandas as pd
import subprocess
import json
import os
import sys
import csv
import uuid

os.environ["NODE_NO_WARNINGS"] = "1"

# Load the configuration.json file
configuration_file_path = os.path.join(
    os.path.dirname(__file__), 'resources', 'configuration.json'
)
# Load the csv file
testdata_file_path = os.path.join(
    os.path.dirname(__file__), 'resources', 'TestData.csv'
)
loadFromFigma_path = os.path.join(
    os.path.dirname(__file__), 'LoadFromFigma.py'
)
testInBrowser_path = os.path.join(
    os.path.dirname(__file__), 'TestInBrowser.py'
)

config = {}
try:
    with open(configuration_file_path, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
except FileNotFoundError:
    print("❌ JSON file not found.")
except json.JSONDecodeError:
    print("❌ Invalid JSON format.")

FIGMA_TOKEN = config.get('FIGMA_TOKEN')
APPLITOOLS_SERVER_URL = config.get('APPLITOOLS_SERVER_URL')
APPLITOOLS_API_KEY = config.get('APPLITOOLS_API_KEY')
HEADLESS = config.get('HEADLESS', "true")

IMAGES_UUID = str(uuid.uuid4())
IMAGES_BATCH_NAME_SUFFIX = " - Check with Figma"
SELENIUM_UUID = str(uuid.uuid4())
SELENIUM_BATCH_NAME_SUFFIX = " - Check against Figma"

def mask(value, min_length=8):
    if not value:
        return "❌ Missing"
    if len(value) < min_length:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"

print(f"{'FIGMA_TOKEN':<25}: {mask(FIGMA_TOKEN)}", file=sys.stderr)
print(f"{'APPLITOOLS_SERVER_URL':<25}: {APPLITOOLS_SERVER_URL or '❌ Missing'}", file=sys.stderr)
print(f"{'APPLITOOLS_API_KEY':<25}: {mask(APPLITOOLS_API_KEY)}", file=sys.stderr)

with open(testdata_file_path, newline='', encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)

    for index, row in enumerate(reader):
        # Extract values from the csv row   
        FIGMA_FILE_KEY = row['FIGMA_FILE_KEY']
        FIGMA_NODE_ID = row['FIGMA_NODE_ID']
        FIGMA_NODE_ID = FIGMA_NODE_ID.replace("-", ":")
        APP_URL = row['APP_URL']
        VIEWPORT_SIZE = row['VIEWPORT_SIZE']
        IGNORE_DISPLACEMENT = row.get('IGNORE_DISPLACEMENT', 'false').strip().lower()
        MATCH_LEVEL = row.get('MATCH_LEVEL', 'Strict').strip()
        SKIP = row.get('SKIP', 'false').strip().lower()

        print(f"\n🔍 Processing row {index + 1}:", file=sys.stderr)
        print(f"{'FIGMA_FILE_KEY':<25}: {FIGMA_FILE_KEY or '❌ Missing'}", file=sys.stderr)
        print(f"{'FIGMA_NODE_ID':<25}: {FIGMA_NODE_ID or '❌ Missing'}", file=sys.stderr)
        print(f"{'APP_URL':<25}: {APP_URL or '❌ Missing'}", file=sys.stderr)
        print(f"{'VIEWPORT_SIZE':<25}: {VIEWPORT_SIZE or '❌ Missing'}", file=sys.stderr)
        print(f"{'SKIP':<25}: {SKIP}", file=sys.stderr)
        print("-" * 75, file=sys.stderr)
        print("\n", file=sys.stderr)

        if SKIP == 'true':
            print("Skipping this row as per configuration.", file=sys.stderr)
            continue
        else:
            try:
                upload_result = subprocess.run(
                    ['python3', 
                    loadFromFigma_path, FIGMA_TOKEN, FIGMA_FILE_KEY, FIGMA_NODE_ID, APPLITOOLS_SERVER_URL, APPLITOOLS_API_KEY, IMAGES_BATCH_NAME_SUFFIX, IMAGES_UUID, VIEWPORT_SIZE],
                    capture_output=True, 
                    text=True,
                    check=True
                )
                print("Output from LoadFromFigma.py:", file=sys.stderr)
                print("🛑 STDERR from Figma Upload:", file=sys.stderr)
                print(upload_result.stderr.strip(), file=sys.stderr)
                print("-" * 50, file=sys.stderr)

                print("📤 STDOUT from Figma Upload:")
                print(upload_result.stdout.strip())
                print("-" * 50)

                upload_result_values = json.loads(upload_result.stdout.strip().splitlines()[-1])
                print("Parsed output from LoadFromFigma.py:", file=sys.stderr)
                print(json.dumps(upload_result_values, indent=4), file=sys.stderr)

            except subprocess.CalledProcessError as e:
                print("❌ LoadFromFigma.py failed with:")
                print("STDOUT:\n", e.stdout)
                print("STDERR:\n", e.stderr)
                continue
            except json.JSONDecodeError:
                print("❌ JSON parsing failed. Output:")
                print(upload_result.stdout)
                print(upload_result.stderr)
                continue

            appName = upload_result_values['appName']
            testName = upload_result_values['testName']
            viewPortSize = upload_result_values['viewPortSize']
            baselineEnvName = upload_result_values['baselineEnvName']
            uploadFromFigmaResults = upload_result_values['uploadFromFigmaResults']

            # Step 2: Call TestInBrowser.py with additional parameters
            try:
                comparison_result = subprocess.run(
                    ['python3', testInBrowser_path, 
                    appName, testName, APPLITOOLS_API_KEY, json.dumps(viewPortSize), baselineEnvName, 
                    APP_URL, SELENIUM_BATCH_NAME_SUFFIX, SELENIUM_UUID, HEADLESS, IGNORE_DISPLACEMENT, MATCH_LEVEL],
                    capture_output=True, 
                    text=True, 
                    check=True)
                print("Output from TestInBrowser.py:", file=sys.stderr)
                print(comparison_result.stderr)
                print(comparison_result.stdout)

                comparison_result_values = json.loads(comparison_result.stdout.strip().splitlines()[-1])
                print("Parsed output from TestInBrowser.py:", file=sys.stderr)
                print(comparison_result_values)

            except subprocess.CalledProcessError as e:
                print("❌ TestInBrowser.py failed with:")
                print("STDOUT:\n", e.stdout)
                print("STDERR:\n", e.stderr)
                continue
            except json.JSONDecodeError:
                print("❌ JSON parsing failed. Output:")
                print(comparison_result.stdout)
                print(comparison_result.stderr)
                continue

            print(f"Output from TestInBrowser.py with \n\tappName={comparison_result_values['appName']}, \n\ttestName={comparison_result_values['testName']}, \n\tviewPortSize={comparison_result_values['viewPortSize']}, \n\tbaselineEnvName={comparison_result_values['baselineEnvName']}, \n\tAPP_URL={comparison_result_values['APP_URL']}, \n\tstatus={comparison_result_values['status']}")
            print("TestInBrowser.py executed successfully.")

        print("=" * 80)
        print("\n" + "=" * 80 + "\n")
