# Compare Figma with Web using Selenium + Applitools

This project automates visual testing by comparing UI designs from **Figma** with the actual rendered web UI using **Selenium WebDriver** and **Applitools Visual AI**.

---

## 🚀 How It Works

- Reads test data from a [CSV file](tests/resources/TestData.csv) for test-specific parameters
- Loads shared credentials and configuration from a [JSON file](tests/resources/configuration.json)
- Loads design components from Figma using the Figma API
- Opens the corresponding app page using Selenium
- Uses Applitools Eyes to visually compare the UI against the Figma design
- Logs and prints test results with visual links

---

## 🛠 Prerequisites

- Python 3.8+
- Google Chrome installed
- ChromeDriver available in PATH

Install required dependencies:

```bash
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
compare-figma-with-web-using-seleniumPy/
├── src/                         # Core logic and helpers
├── tests/
│   ├── main.py                  # Entry point to run visual comparisons
│   ├── TestInBrowser.py         # Web test logic using Applitools Eyes
│   ├── LoadFromFigma.py         # Figma API interaction
│   └── resources/
│       ├── TestData.csv        # Test-specific inputs (file key, node ID, app URL, viewport)
│       └── configuration.json          # Shared API tokens and server config
├── requirements.txt
```

---

## 🧪 Running the Tests

Make the script executable:

```bash
chmod +x tests/main.py
```

Then run it directly:

```bash
./tests/main.py
```

Or run using Python:

```bash
python tests/main.py
```

---

## 📄 [Config Format](tests/resources/configuration.json)

```json
{
  "FIGMA_TOKEN": "figd_abc123",
  "APPLITOOLS_API_KEY": "key_12345",
  "APPLITOOLS_SERVER_URL": "https://eyes.applitools.com"
}
```

---

## 📄 [CSV Format](tests/resources/TestData.csv)

The CSV file should include:

| FIGMA_FILE_KEY | FIGMA_NODE_ID | APP_URL | VIEWPORT_SIZE |
|----------------|----------------|---------|----------------|
| key_987xyz     | 5-21           | https://myapp.com | 1600x800 |

### Notes:
- All values are required per row
- `FIGMA_NODE_ID` is auto-transformed from `5-21` to `5:21`
- `VIEWPORT_SIZE` is used to:
  - Resize the browser window **before comparison**
  - Resize the image uploaded from Figma (unless set to `"USE_SOURCE"`)
- If `VIEWPORT_SIZE` is `"USE_SOURCE"`, the Figma image's native dimensions will be used

---

## ✅ Sample Output

```text
🔍 Processing row 1:
FIGMA_FILE_KEY      : key_987xyz
FIGMA_NODE_ID       : 5:21
APP_URL             : https://myapp.com
VIEWPORT_SIZE       : 1600x800
--------------------------------------------------
✅ Test passed. View results at: https://eyes.applitools.com/app/batches/...
```

---

## 🧹 Warnings Suppressed

- `RemovedInMarshmallow4Warning` and Node.js experimental warnings are automatically suppressed
- `utf-8-sig` is used to handle BOMs in CSV/JSON files

---

## 🤝 Contributing

Pull requests and issues are welcome. Please ensure your changes are tested.

---

## 📜 License

MIT License © [Anand Bagmar](https://github.com/anandbagmar)
