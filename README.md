
# Compare Figma with Web using Selenium + Applitools

This project automates visual testing by comparing UI designs from **Figma** with the actual rendered web UI using **Selenium WebDriver** and **Applitools Visual AI**.

---

## 🚀 How It Works

- Loads configuration values from `config.json`
- Reads test parameters per row from `test_data.csv`
- Fetches Figma designs via API using Figma token
- Compares rendered browser UI against Figma image via Applitools Eyes
- Optionally uses HEADLESS mode for execution
- Supports setting the Applitools MatchLevel per test

---

## 🛠 Prerequisites

- Python 3.8+
- Google Chrome
- ChromeDriver in PATH
- Figma key

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
compare-figma-with-web-using-seleniumPy/
├── src/
│   └── utils/
│       └── ApplitoolsResultsSerializer.py
├── tests/
│   ├── Main.py                  # Orchestrates Figma-to-Web comparison
│   ├── TestInBrowser.py         # Performs visual checks using Applitools
│   ├── LoadFromFigma.py         # Downloads and prepares Figma images
│   └── resources/
│       ├── Config.json          # API keys, server config
│       └── TestData.csv        # Test-specific data
```

---

## 📄 [Config Format](tests/resources/Config.json)

```json
{
  "FIGMA_TOKEN": "figd_abc123",
  "APPLITOOLS_API_KEY": "api_key_123",
  "APPLITOOLS_SERVER_URL": "https://eyes.applitools.com",
  "HEADLESS": "true"
}
```

---

## 📄 [Test Data Format](tests/resources/TestData.csv)

| FIGMA_FILE_KEY | FIGMA_NODE_ID | APP_URL                  | VIEWPORT_SIZE | IGNORE_DISPLACEMENT | MATCH_LEVEL | SKIP |
|----------------|---------------|--------------------------|---------------|---------------------|-------------|------|
| key_abc        | 123:456        | https://yourapp.com     | 1600x900       | true/false | layout       | true/false |

- `FIGMA_NODE_ID` uses `:` instead of `-`
- `VIEWPORT_SIZE` = `"USE_SOURCE"` to use image's native size, or specific size - example: `1600x1250`
- `IGNORE_DISPLACEMENT` = supports values like `true` or `false`. See [here](https://applitools.com/tutorials/concepts/best-practices/hide-displacements) for more information on Ignore Displacement
- `MATCH_LEVEL` supports values like `"layout"`, `"strict"`, `"exact"`. See [here](https://applitools.com/tutorials/concepts/best-practices/match-levels) for more information on Applitools MatchLevel
- `SKIP` = supports values like `true` or `false`. Value of `true` means this line will be skipped in the execution

---

## 🧪 Running the Tests

Make the script executable:

```bash
chmod +x tests/Main.py
```

Then run it directly:

```bash
./tests/Main.py
```

Or run using Python:

```bash
python tests/Main.py
```

---

## 🔇 Warnings Suppressed

- Experimental Node warnings
- Deprecated marshmallow context warnings
- Handles UTF-8 BOM in CSV/JSON

---

## 📜 License

MIT License © [Anand Bagmar](https://github.com/anandbagmar)
