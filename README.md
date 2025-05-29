# Compare Figma with Web using Selenium + Applitools

This project automates visual testing by comparing UI designs from **Figma** with the actual rendered web UI using **Selenium WebDriver** and **Applitools Visual AI**.

---

## 🚀 How It Works

- Reads test data from a CSV file (`tests/resources/test_data.csv`)
- Loads design components from Figma using the Figma API
- Opens the corresponding app page using Selenium
- Uses Applitools Eyes to visually compare the two
- Logs and prints test results with a visual link

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
├── src/                    # Core logic and helpers
├── tests/
│   ├── main.py             # Entry point to run visual comparisons
│   └── resources/
│       └── test_data.csv   # All test inputs (API tokens, URLs, etc.)
├── requirements.txt
```

---

## 🧪 Running the Tests

Run with Python:

```bash
python tests/main.py
```

Make sure the CSV at `tests/resources/test_data.csv` contains all necessary values.

---

## 📄 CSV Format (`TestData.csv`)

Your test data file must contain the following headers:

| FIGMA_TOKEN | FIGMA_FILE_KEY | FIGMA_NODE_ID | APPLITOOLS_SERVER_URL | APPLITOOLS_API_KEY | APP_URL |
|-------------|----------------|----------------|------------------------|--------------------|---------|
| token123    | fileKeyABC     | 5:21           | https://eyes.applitools.com | key456        | https://your-site |

All values are required per row. `FIGMA_NODE_ID` supports auto-fixing `-` to `:` where needed.

---

## ✅ Sample Output

```text
🔍 Processing row 1:
FIGMA_TOKEN         : abcd...1234
APPLITOOLS_API_KEY  : 1234...abcd
FIGMA_FILE_KEY      : a1b2c3
FIGMA_NODE_ID       : 5:21
APP_URL             : https://your-site.com
--------------------------------------------------
✅ Test passed. View results at: https://eyes.applitools.com/app/batches/...
```

---

## 🤝 Contributing

Pull requests and issues are welcome. Please ensure your changes are well tested.

---

## 📜 License

MIT License © [Anand Bagmar](https://github.com/anandbagmar)
