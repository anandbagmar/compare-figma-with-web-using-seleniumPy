# Compare Figma with Web using Selenium or with local Images + Applitools

This project automates visual testing by comparing UI designs from **Figma** with the actual rendered web UI using **Selenium WebDriver** or **local image files** and **Applitools Visual AI**.

---

## 🚀 How It Works

- Loads configuration values from `config/Config.json`
- Reads test parameters per row from `config/TestData.csv`
- IF `"FIGMA_ONLY": "true"`, then
  - Fetches Figma designs via API using Figma token and uploads to Applitools Eyes
- ELSE IF `"FIGMA_ONLY": "false"`, then
  - Fetches Figma designs via API using Figma token and uploads to Applitools Eyes
  - Compares rendered browser UI against Figma image via Applitools Eyes
  - Optionally uses HEADLESS mode for execution
  - Supports setting the Applitools MatchLevel per test

---

## 🛠 Prerequisites

- Python 3.9+
- Google Chrome
- (Selenium 4 manages drivers automatically; no manual chromedriver needed in most setups)
- [Figma read‑only key](How%20to%20create%20Figma%20read-only%20key.mov)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
compare-figma-with-web-using-seleniumPy/
├── config/
│   ├── Config.json          # API keys, server/config
│   └── TestData.csv         # Test-specific data
├── src/
│   └── utils/
│       └── ApplitoolsResultsSerializer.py
├── tests/
│   ├── Main.py              # Orchestrates Figma-to-Web comparison
│   ├── TestInBrowser.py     # Visual checks using Selenium + Applitools
│   ├── TestAnImage.py       # Compare a local PNG image against Figma
│   └── LoadFromFigma.py     # Downloads and prepares Figma images
└── java-runner/             # (Optional) Java wrapper to run Main.py via Gradle
    ├── build.gradle
    └── src/main/java/com/eot/runner/RunMainPy.java
```

---

## 📄 Config Format (`config/Config.json`)

```json
{
  "FIGMA_TOKEN": "MY FIGMA TOKEN",
  "APPLITOOLS_API_KEY": "MY APPLITOOLS_API_KEY",
  "APPLITOOLS_SERVER_URL": "https://eyes.applitools.com",
  "HEADLESS": "true",
  "FIGMA_ONLY": "false"
}
```

> You can also provide `FIGMA_TOKEN` / `APPLITOOLS_API_KEY` via environment variables before running.

---

## 📄 Test Data Format (`config/TestData.csv`)

| FIGMA_URL | APP_URL | VIEWPORT_SIZE | IGNORE_DISPLACEMENT | MATCH_LEVEL | SKIP |
|---|---|---|---|---|---|
| https://www.figma.com/design/myapp?node-id=17-4&t=... | https://yourapp.com | 1600x900 | true/false | layout | true/false |
| https://www.figma.com/design/myapp?node-id=17-4&t=... | /FULL/PATH/TO/image.png | 1600x900 | true/false | strict | true/false |

- `VIEWPORT_SIZE` — `"USE_SOURCE"` to use Figma node’s native size, or a specific size (e.g., `1600x1250`).
- `IGNORE_DISPLACEMENT` — values like `true` or `false`.
- `MATCH_LEVEL` — `layout`, `strict`, `exact`, `content`.
- `SKIP` — `true` to skip a row.
- You may comment out a Figma row by starting the URL with `#`, `//`, or `/*`.

---

## 🧪 Running the Tests (Python)

From the repo root:

```bash
python tests/Main.py --config config/Config.json --data config/TestData.csv -v
# Optional:
# python tests/Main.py --dry-run -v
```

> File paths in `APP_URL` can be plain paths or `file:` URIs (e.g. `file:./tests/resources/app.png`).

---

## ▶️ Run via Java (Gradle)

This repo includes an optional **Gradle-based Java runner** at `java-runner/` that executes `tests/Main.py`, streams logs in **real time**, and fails the build if Python exits non‑zero.

### Quick start

```bash
cd java-runner
./gradlew run
```

The runner will:
- Auto-detect the repo root (parent directory of `java-runner/`)
- Use `config/Config.json` and `config/TestData.csv`
- Stream Python logs to the console (`[py]` for stdout, `[py!]` for stderr)

### Advanced usage

```bash
./gradlew run   -PrepoRoot=..   -Pconfig=../config/Config.json   -Pdata=../config/TestData.csv   -PtimeoutSec=1200   -Pverbose=true   -PdryRun=false
```

**Options (`-P…`)**
- `repoRoot` — path to repo root (defaults to auto-detect from `java-runner/`).
- `config` — config JSON path (default: `../config/Config.json`).
- `data` — CSV path (default: `../config/TestData.csv`).
- `timeoutSec` — overall timeout in seconds (default: `900`).
- `verbose` — `true|false` (adds `-v` to `Main.py`).
- `dryRun` — `true|false` (adds `--dry-run` to `Main.py`).

> The Java runner prefers the Python interpreter in `./.venv` if present; otherwise it falls back to `python3`/`python.exe` on PATH.

---

## 🔧 Troubleshooting

- **`IsADirectoryError: '.'`** — Make sure `--config` / `--data` point to files, not directories, or run Gradle with valid `-Pconfig`/`-Pdata` values.
- **“APP_URL is neither a URL nor an existing file path”** — Ensure local image paths exist. File URIs like `file:./path.png` are supported.
- **Chrome / driver issues** — Install Google Chrome. Selenium 4 uses Selenium Manager to fetch drivers (internet access required).

---

## 🔇 Warnings Suppressed

- Experimental Node warnings
- Deprecated marshmallow context warnings
- Handles UTF-8 BOM in CSV/JSON

---

## 📜 License

MIT License © [Anand Bagmar](https://github.com/anandbagmar)
