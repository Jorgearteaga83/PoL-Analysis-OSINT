# PoL-Analysis-OSINT
Aggregating Unstructured Public Data for 'Pattern of Life' - Analysis: An OSINT Tool for social media
OSINT Social Media Analysis Tool

A Python-based OSINT (Open-Source Intelligence) dashboard for analysing social-media posting behaviour, sentiment, and image-based metadata leakage.
The tool supports GUI analysis, image inspection, OCR, EXIF GPS extraction, sentiment analysis, and mock-profile simulation.

⚙️ 1. Installation

Before running the tool, install all required Python libraries inside your virtual environment:

pip install pandas matplotlib pillow exifread opencv-python pytesseract vaderSentiment scrapy requests seaborn folium streamlit flask

✔ Additional Requirements (Non-Python)
Tesseract OCR

Required for extracting text from images.

Download for Windows:
https://github.com/UB-Mannheim/tesseract/wiki

After installation, ensure the executable path is added to your system PATH, for example:

C:\Program Files\Tesseract-OCR\

📁 2. Project Structure (Important Folders)
osint_pol_tool/
│── app/
│   ├── scraper.py
│   ├── exif_analyser.py
│   ├── sentiment_analyser.py
│   ├── leakage_analyser.py
│   ├── timestamp_analyser.py
│   ├── ingest_export.py
│   ├── targets.py
│   ├── config.py
│   └── ...
│
│── data/               ← CSV post datasets generated or imported
│── images/
│   └── <username>/     ← Images for each target account
│
│── outputs/            ← Future output exports (optional)
│── main.py             ← GUI application entry point
│── generate_mock_posts.py  ← Script to generate synthetic datasets
│── targets.json        ← Target account configuration

▶️ 3. Running the Application

After installation, simply run:

python main.py


or in PyCharm, press Run ▶️ on main.py.

This opens the full GUI dashboard, where you can:

Select a target account

Choose a timeframe

View posting behaviour

Inspect sentiment patterns

Analyse EXIF leakage & OCR text

Preview actual images directly inside the GUI

🧪 4. Generating Mock Accounts & Posts

For ethical testing, the project includes mock social-media profiles that simulate realistic posting patterns.

To generate synthetic datasets:

python generate_mock_posts.py


This creates:

CSV post files under data/

Image folders under images/<username>/

Randomised timestamps, captions, and dummy images

Optional GPS leakage and fake text for OCR detection

These mock profiles allow:

Controlled experiments

Demonstration of leakage detection

Comparison across different user behaviours

📌 5. Targets Configuration

targets.json defines all available accounts shown in the GUI.
It includes both:

Public accounts (e.g., politicians, celebrities)

Mock accounts created for academic evaluation

Each entry includes:

{
    "label": "scrapper_target1",
    "username": "scrapper_user1",
    "group": "controller",
    "profile_url": "https://instagram.com/scrapper_user1/"
}


You may add or remove entries as needed.

📸 6. Image Leakage Analysis

The tool detects:

GPS coordinates from EXIF metadata

Visible text on images using OCR

Potential secondary leakage indicators

Clicking a row in Image Leakage tab shows:

Full-size image preview

OCR extracted text

GPS coordinates (if present)

📊 7. Outputs

The GUI includes:

Temporal graphs

Posting distributions

Sentiment statistics

Raw post tables

Image leakage summary

The dashboard is designed for academic, forensic, and ethical OSINT research.

✔ Ready to Use

Once dependencies are installed, simply run:

python main.py


and begin analysing any mock or public profile included in your targets.json.
