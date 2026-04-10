# PoL-Analysis-OSINT
OSINT Social Media Analysis Tool

A Python-based OSINT (Open-Source Intelligence) dashboard for analysing social-media posting behaviour and image-based metadata leakage.

## ⚙️ 1. Installation

Before running the tool, install all required Python libraries from `requirements.txt`:

```bash
pip install -r requirements.txt
```

This will install:
- `pandas`
- `Pillow`
- `openpyxl`
- `matplotlib`
- `vaderSentiment`
- `networkx`
- `reverse_geocoder`
- `timezonefinder`
- `pytest`

## 📁 2. Project Structure

-   `src/`: Contains the application source code.
    -   `main.py`: The main entry point for the GUI application.
    -   `app_gui.py`: The graphical user interface implementation.
    -   `data_processing.py`: Data cleaning and normalization logic.
    -   `osint_analysis.py`: Core analysis functions (temporal, sentiment, location, etc.).
    -   `utils.py`: Utility functions.
-   `data/`: Directory to store your input datasets (CSV, XLSX).
-   `output/`: Directory where the generated reports, graphs, and normalized datasets are saved.
-   `tests/`: Contains automated test cases.
-   `README.md`: This file.
-   `requirements.txt`: A list of all python libraries required to run the application.

## ▶️ 3. Running the Application

After installation, run the application from the project root:

```bash
python src/main.py
```

This opens the GUI dashboard, where you can:

-   Upload a dataset of social media posts.
-   Filter posts by target account and time window.
-   Perform overview, temporal, sentiment, and image leakage/EXIF analysis.
-   Generate comprehensive intelligence reports (including Spatial, Social Network, and Behavioural/Anomaly analysis).
-   View raw post data.

## 📊 4. Analyses

The tool provides the following analyses:

-   **Overview Analysis:** Shows a summary of the posts, including total posts, posts with location, and posts with tagged users.
-   **Temporal Analysis:** Displays posting patterns over time (per day, per hour, per weekday) with charts and a pattern-of-life heatmap.
-   **Sentiment Analysis:** Analyzes the sentiment of post captions and displays the trend over time, identifying potential grievances.
-   **Image Leakage & EXIF Analysis:** Analyzes images for EXIF metadata, including GPS coordinates and camera information.
-   **Reporting (Intelligence Report):** Generates detailed HTML intelligence reports summarizing all findings, which include Social Network Analysis (SNA) and Behavioural Anomaly Analysis.
-   **Raw Posts:** Shows a table of the raw post data.
