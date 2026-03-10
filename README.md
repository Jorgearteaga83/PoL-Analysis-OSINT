# PoL-Analysis-OSINT
OSINT Social Media Analysis Tool

A Python-based OSINT (Open-Source Intelligence) dashboard for analysing social-media posting behaviour and image-based metadata leakage.

## ⚙️ 1. Installation

Before running the tool, install all required Python libraries:

```bash
pip install pandas Pillow
```

## 📁 2. Project Structure

-   `main.py`: The main GUI application.
-   `data/`:  Directory to store your input datasets (CSV, XLSX).
-   `output/`: Directory where the normalized dataset and extracted images will be saved.
-   `README.md`: This file.

## ▶️ 3. Running the Application

After installation, simply run:

```bash
python main.py
```

This opens the GUI dashboard, where you can:

-   Upload a dataset of social media posts.
-   Filter posts by target account and time window.
-   Perform overview, temporal, and leakage analysis.
-   View raw post data.
-   Extract and analyze EXIF data from images.

## 📊 4. Analyses

The tool provides the following analyses:

-   **Overview Analysis:** Shows a summary of the posts, including total posts, posts with location, and posts with tagged users.
-   **Temporal Analysis:**  Displays posting patterns over time (per day, per hour, per weekday).
-   **Leakage Analysis:**  Analyzes images for EXIF metadata, including GPS coordinates.
-   **Raw Posts:**  Shows a table of the raw post data.
