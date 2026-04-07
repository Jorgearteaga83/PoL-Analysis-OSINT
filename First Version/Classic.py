from __future__ import annotations  # Import necessary module or component

import os  # Import necessary module or component
import re  # Import necessary module or component
import json  # Import necessary module or component
import shutil  # Import necessary module or component
import webbrowser  # Import necessary module or component
import requests  # Import necessary module or component
import tempfile  # Import necessary module or component
from pathlib import Path  # Import necessary module or component
from datetime import datetime  # Import necessary module or component
from typing import Any, Optional, Union  # Import necessary module or component
import base64  # Import necessary module or component
from io import BytesIO  # Import necessary module or component

import tkinter as tk  # Import necessary module or component
from tkinter import ttk, messagebox, filedialog  # Import necessary module or component

try:  # Start of try block for exception handling
    import pandas as pd  # Import necessary module or component
    from PIL import Image, ImageTk, ExifTags  # Import necessary module or component
    import openpyxl  # Import necessary module or component

    # Charts
    import matplotlib.pyplot as plt  # Import necessary module or component
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Import necessary module or component
    import matplotlib.dates as mdates  # Import necessary module or component
    
    # New imports for advanced analysis
    import networkx as nx  # Import necessary module or component
    import reverse_geocoder as rg  # Import necessary module or component
    from timezonefinder import TimezoneFinder  # Import necessary module or component

except ImportError as e:  # Handle specific exceptions
    root = tk.Tk()  # Assign value to root
    root.withdraw()  # Close bracket/parenthesis
    # Close bracket/parenthesis
    # Close bracket/parenthesis
    messagebox.showerror("Missing Libraries", f"Required library missing: {e}\n\nPlease run:\npip install pandas Pillow openpyxl matplotlib networkx reverse_geocoder timezonefinder")
    raise SystemExit  # Raise an exception


# =========================================================
# Directories
# =========================================================
DATA_DIR = Path("data")  # Assign value to DATA_DIR
OUTPUT_DIR = Path("output")  # Assign value to OUTPUT_DIR
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"  # Assign value to OUTPUT_IMAGES_DIR

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}  # Assign value to SUPPORTED_EXTS


def ensure_directories():  # Define function ensure_directories
    DATA_DIR.mkdir(exist_ok=True, parents=True)  # Close bracket/parenthesis
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)  # Close bracket/parenthesis
    OUTPUT_IMAGES_DIR.mkdir(exist_ok=True, parents=True)  # Close bracket/parenthesis


# =========================================================
# Utility helpers
# =========================================================
def best_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:  # Define function best_col
    """Return the first matching column name from candidates (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}  # Assign value to cols_lower
    for cand in candidates:  # Iterate in a loop
        if cand.lower() in cols_lower:  # Check conditional statement
            return cols_lower[cand.lower()]  # Return value from function
    return None  # Return value from function


NaTType = type(pd.NaT)  # Assign value to NaTType


def to_datetime_safe(x: Any) -> Union[pd.Timestamp, NaTType]:  # Define function to_datetime_safe
    """Parse timestamps robustly (unix seconds/ms OR ISO strings). Always UTC."""
    if x is None or (isinstance(x, float) and pd.isna(x)):  # Check conditional statement
        return pd.NaT  # Return value from function

    if isinstance(x, (int, float)) and not pd.isna(x):  # Check conditional statement
        try:  # Start of try block for exception handling
            xi = int(x)  # Assign value to xi
            if xi > 10_000_000_000:  # likely ms
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")  # Return value from function
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")  # Return value from function
        except Exception:  # Handle specific exceptions
            return pd.NaT  # Return value from function

    s = str(x).strip()  # Assign value to s
    if not s:  # Check conditional statement
        return pd.NaT  # Return value from function

    if re.fullmatch(r"\d{10,13}", s):  # Check conditional statement
        try:  # Start of try block for exception handling
            xi = int(s)  # Assign value to xi
            if xi > 10_000_000_000:  # Check conditional statement
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")  # Return value from function
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")  # Return value from function
        except Exception:  # Handle specific exceptions
            return pd.NaT  # Return value from function

    return pd.to_datetime(s, utc=True, errors="coerce")  # Return value from function


def safe_json_loads(s: str):  # Define function safe_json_loads
    try:  # Start of try block for exception handling
        return json.loads(s)  # Return value from function
    except Exception:  # Handle specific exceptions
        return None  # Return value from function


def extract_tagged_users(cell: Any) -> list[str]:  # Define function extract_tagged_users
    """Extract tagged usernames from list/dict/json-string or comma/space string."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):  # Check conditional statement
        return []  # Return value from function

    if isinstance(cell, list):  # Check conditional statement
        out = []  # Assign value to out
        for item in cell:  # Iterate in a loop
            if isinstance(item, str):  # Check conditional statement
                out.append(item.strip().lstrip("@"))  # Close bracket/parenthesis
            elif isinstance(item, dict):  # Check alternative condition
                if isinstance(item.get("username"), str):  # Check conditional statement
                    out.append(item["username"].strip().lstrip("@"))  # Close bracket/parenthesis
                # Check alternative condition
                # Check alternative condition
                elif isinstance(item.get("user"), dict) and isinstance(item["user"].get("username"), str):
                    out.append(item["user"]["username"].strip().lstrip("@"))  # Close bracket/parenthesis
        return sorted({x for x in out if x})  # Return value from function

    if isinstance(cell, dict):  # Check conditional statement
        if "taggedUsers" in cell:  # Check conditional statement
            return extract_tagged_users(cell.get("taggedUsers"))  # Return value from function
        if "users" in cell:  # Check conditional statement
            return extract_tagged_users(cell.get("users"))  # Return value from function
        if isinstance(cell.get("username"), str):  # Check conditional statement
            return [cell["username"].strip().lstrip("@")]  # Return value from function
        return []  # Return value from function

    s = str(cell).strip()  # Assign value to s
    if not s:  # Check conditional statement
        return []  # Return value from function

    if s.startswith("[") or s.startswith("{"):  # Check conditional statement
        obj = safe_json_loads(s)  # Assign value to obj
        if obj is not None:  # Check conditional statement
            return extract_tagged_users(obj)  # Return value from function

    parts = re.split(r"[,\s]+", s)  # Assign value to parts
    cleaned = [p.strip().lstrip("@") for p in parts if p.strip()]  # Assign value to cleaned
    return sorted({x for x in cleaned if x})  # Return value from function


# =========================================================
# EXIF GPS parsing
# =========================================================
GPSTAGS = ExifTags.GPSTAGS  # Assign value to GPSTAGS


def ratio_to_float(x):  # Define function ratio_to_float
    try:  # Start of try block for exception handling
        if hasattr(x, "numerator") and hasattr(x, "denominator"):  # Check conditional statement
            return float(x.numerator) / float(x.denominator)  # Return value from function
        if isinstance(x, (tuple, list)) and len(x) == 2:  # Check conditional statement
            num, den = x  # Execute statement or expression
            return float(num) / float(den) if den else 0.0  # Return value from function
        return float(x)  # Return value from function
    except Exception:  # Handle specific exceptions
        return 0.0  # Return value from function


def dms_to_decimal(dms, ref):  # Define function dms_to_decimal
    try:  # Start of try block for exception handling
        deg = ratio_to_float(dms[0])  # Assign value to deg
        minutes = ratio_to_float(dms[1])  # Assign value to minutes
        seconds = ratio_to_float(dms[2])  # Assign value to seconds
        dec = deg + (minutes / 60.0) + (seconds / 3600.0)  # Assign value to dec
        if ref in ("S", "W"):  # Check conditional statement
            dec = -dec  # Assign value to dec
        return dec  # Return value from function
    except Exception:  # Handle specific exceptions
        return None  # Return value from function


def extract_exif(path: Path):  # Define function extract_exif
    """
    Returns:
        exif_readable(bool) -> could we read EXIF container
        gps_present(bool)    -> GPS fields present
        lat(float|None), lon(float|None)
    """
    try:  # Start of try block for exception handling
        img = Image.open(path)  # Assign value to img
        exif = img.getexif()  # Assign value to exif
        if not exif:  # Check conditional statement
            return False, False, None, None  # Return value from function

        gps_tag = None  # Assign value to gps_tag
        for k, v in ExifTags.TAGS.items():  # Iterate in a loop
            if v == "GPSInfo":  # Check conditional statement
                gps_tag = k  # Assign value to gps_tag
                break  # Exit the current loop

        if gps_tag is None or gps_tag not in exif:  # Check conditional statement
            return True, False, None, None  # Return value from function

        gps_info = exif[gps_tag]  # Assign value to gps_info
        if not isinstance(gps_info, dict):  # Check conditional statement
            return True, False, None, None  # Return value from function

        decoded = {}  # Assign value to decoded
        for key, val in gps_info.items():  # Iterate in a loop
            decoded[GPSTAGS.get(key, key)] = val  # Execute statement or expression

        lat = lon = None  # Assign value to lat
        if "GPSLatitude" in decoded and "GPSLatitudeRef" in decoded:  # Check conditional statement
            lat = dms_to_decimal(decoded["GPSLatitude"], str(decoded["GPSLatitudeRef"]))  # Assign value to lat
        if "GPSLongitude" in decoded and "GPSLongitudeRef" in decoded:  # Check conditional statement
            lon = dms_to_decimal(decoded["GPSLongitude"], str(decoded["GPSLongitudeRef"]))  # Assign value to lon

        return True, True, lat, lon  # Return value from function
    except Exception:  # Handle specific exceptions
        return False, False, None, None  # Return value from function


# =========================================================
# Dataset Normalizer
# =========================================================
def normalize_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:  # Define function normalize_dataset
    """
    Harmonise heterogeneous CSV/XLSX schemas into a consistent OSINT analysis table.
    """
    df = df_raw.copy()  # Assign value to df
    out = pd.DataFrame()  # Assign value to out

    c_post = best_col(df, ["post_id", "id", "postId", "shortCode", "shortcode"])  # Assign value to c_post
    c_user = best_col(df, ["account", "username", "ownerUsername", "owner.username"])  # Assign value to c_user
    c_time = best_col(df, ["timestamp_utc", "timestamp", "takenAtTimestamp", "createdAt"])  # Assign value to c_time
    c_caption = best_col(df, ["caption", "text", "description"])  # Assign value to c_caption
    c_url = best_col(df, ["display_url", "displayUrl", "imageUrl"])  # Assign value to c_url
    c_posturl = best_col(df, ["post_url", "url"])  # Assign value to c_posturl
    c_loc = best_col(df, ["location", "locationName", "location_name", "placeName"])  # Assign value to c_loc
    c_img = best_col(df, ["image_ref", "imagePath", "local_path"])  # Assign value to c_img

    out["post_id"] = df[c_post].fillna("") if c_post else ""  # Assign value to out["post_id"]
    out["username"] = df[c_user].fillna("unknown") if c_user else "unknown"  # Assign value to out["username"]
    out["timestamp_utc"] = df[c_time].apply(to_datetime_safe) if c_time else pd.NaT  # Assign value to out["timestamp_utc"]
    out["caption"] = df[c_caption].fillna("") if c_caption else ""  # Assign value to out["caption"]
    out["display_url"] = df[c_url].fillna("") if c_url else ""  # Assign value to out["display_url"]
    out["post_url"] = df[c_posturl].fillna("") if c_posturl else ""  # Assign value to out["post_url"]
    out["location"] = df[c_loc].fillna("") if c_loc else ""  # Assign value to out["location"]
    out["image_ref"] = df[c_img].fillna("").astype(str) if c_img else ""  # Assign value to out["image_ref"]

    # --- NEW: Associated Entities (for SNA) ---
    all_entities = [[] for _ in range(len(df))]  # Assign value to all_entities
    
    # Regex to find columns related to tagged users or mentions
    # Assign value to mention_cols
    # Assign value to mention_cols
    mention_cols = [c for c in df.columns if re.search(r'.*taggedUsers.*username.*|mentions/\d+', c, re.IGNORECASE)]
    
    # Also include standard columns that might contain user tags
    for simple_col_name in ["tagged_users", "taggedUsers", "userTags", "mentions"]:  # Iterate in a loop
        simple_col = best_col(df, [simple_col_name])  # Assign value to simple_col
        if simple_col and simple_col not in mention_cols:  # Check conditional statement
            mention_cols.append(simple_col)  # Close bracket/parenthesis

    for i, row in df.iterrows():  # Iterate in a loop
        row_entities = set()  # Assign value to row_entities
        for col in mention_cols:  # Iterate in a loop
            cell_val = row[col]  # Assign value to cell_val
            if pd.notna(cell_val):  # Check conditional statement
                # The existing 'extract_tagged_users' is robust enough to handle various formats
                extracted = extract_tagged_users(cell_val)  # Assign value to extracted
                for user in extracted:  # Iterate in a loop
                    row_entities.add(user)  # Close bracket/parenthesis
        all_entities[i] = sorted(list(row_entities))  # Assign value to all_entities[i]

    out["associated_entities"] = all_entities  # Assign value to out["associated_entities"]

    # cleanup
    out["username"] = out["username"].fillna("unknown").astype(str).str.strip()  # Assign value to out["username"]
    out["post_id"] = out["post_id"].fillna("").astype(str).str.strip()  # Assign value to out["post_id"]
    
    out.rename(columns={'tagged_users': 'associated_entities'}, inplace=True)  # Close bracket/parenthesis


    out = out[out["post_id"] != ""]  # Assign value to out
    out = out[out["username"] != "unknown"]  # Assign value to out

    return out.reset_index(drop=True)  # Return value from function

# =========================================================
# NEW: Offline Geocoding & Timezone Engine
# =========================================================
tf = TimezoneFinder()  # Assign value to tf

# Define function infer_location_data
# Define function infer_location_data
def infer_location_data(lat: Optional[float], lon: Optional[float], location_string: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Offline-only location and timezone inference.
    Returns (City, Country, Timezone).
    """
    if lat is not None and lon is not None:  # Check conditional statement
        try:  # Start of try block for exception handling
            # reverse_geocoder is offline, uses a local city database
            results = rg.search((lat, lon), mode=1)  # Assign value to results
            if results:  # Check conditional statement
                location = results[0]  # Assign value to location
                city = location.get('name')  # Assign value to city
                country = location.get('country')  # Assign value to country
                
                # timezonefinder is offline
                timezone = tf.timezone_at(lng=lon, lat=lat)  # Assign value to timezone
                
                return city, country, timezone  # Return value from function
        except Exception:  # Handle specific exceptions
            return None, None, None  # Return value from function
    
    # If only a string is available, don't geocode to maintain OPSEC
    if location_string:  # Check conditional statement
        return location_string, None, None # Note the location name without geocoding
        
    return None, None, None  # Return value from function

# =========================================================
# NEW: Heuristic NLP Location Categorization
# =========================================================
def categorize_location(df: pd.DataFrame) -> pd.DataFrame:  # Define function categorize_location
    """
    Assigns location categories (Work, Home, Travel) based on keywords and time.
    """
    df_out = df.copy()  # Assign value to df_out
    
    # Define keyword lexicons
    lexicons = {  # Assign value to lexicons
        "Work": ["office", "grind", "meeting", "work", "job", "desk", "colleagues"],  # Execute statement or expression
        "Home": ["couch", "living room", "neighborhood", "home", "relaxing", "chilling", "sofa"],  # Execute statement or expression
        "Travel": ["airport", "vacation", "explore", "travel", "holiday", "sightseeing", "tourist"]  # Close bracket/parenthesis
    }  # Close bracket/parenthesis
    
    # Default category is unassigned
    df_out['location_category'] = "Uncategorized"  # Assign value to df_out['location_category']
    
    # This is a simplified heuristic. A real system would need more complex logic.
    for category, keywords in lexicons.items():  # Iterate in a loop
        # Create a regex pattern for the keywords
        pattern = '|'.join(keywords)  # Assign value to pattern
        # Find rows where the caption matches the keyword pattern
        mask = df_out['caption'].str.contains(pattern, case=False, na=False)  # Assign value to mask
        df_out.loc[mask, 'location_category'] = f"Assumed: {category}"  # Execute statement or expression

    return df_out  # Return value from function

# =========================================================
# NEW: Social Network Analysis (SNA) Module
# =========================================================
def generate_sna_graph(df: pd.DataFrame, target_user: str, output_dir: Path) -> Optional[Path]:  # Define function generate_sna_graph
    """
    Generates a social network graph and saves it as a PNG.
    """
    if 'associated_entities' not in df.columns:  # Check conditional statement
        return None  # Return value from function

    G = nx.Graph()  # Assign value to G
    G.add_node(target_user, size=50, color='red') # Central node

    edge_weights = {}  # Assign value to edge_weights
    for _, row in df.iterrows():  # Iterate in a loop
        entities = row['associated_entities']  # Assign value to entities
        if not isinstance(entities, list):  # Check conditional statement
            continue  # Skip to next loop iteration
        for entity in entities:  # Iterate in a loop
            if entity == target_user:  # Check conditional statement
                continue  # Skip to next loop iteration
            
            # Add node if it doesn't exist
            if not G.has_node(entity):  # Check conditional statement
                G.add_node(entity, size=10, color='skyblue')  # Close bracket/parenthesis

            # Update edge weight
            edge = tuple(sorted((target_user, entity)))  # Assign value to edge
            edge_weights[edge] = edge_weights.get(edge, 0) + 1  # Assign value to edge_weights[edge]

    for edge, weight in edge_weights.items():  # Iterate in a loop
        G.add_edge(edge[0], edge[1], weight=weight)  # Close bracket/parenthesis

    if len(G.nodes) <= 1:  # Check conditional statement
        return None # No network to draw

    plt.figure(figsize=(12, 12))  # Close bracket/parenthesis
    pos = nx.spring_layout(G, k=0.5, iterations=50)  # Assign value to pos
    
    node_sizes = [d['size']*20 for n, d in G.nodes(data=True)]  # Assign value to node_sizes
    node_colors = [d['color'] for n, d in G.nodes(data=True)]  # Assign value to node_colors
    
    # Close bracket/parenthesis
    # Close bracket/parenthesis
    nx.draw(G, pos, with_labels=True, node_size=node_sizes, node_color=node_colors, font_size=10, font_weight='bold')
    
    edge_labels = nx.get_edge_attributes(G, 'weight')  # Assign value to edge_labels
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)  # Close bracket/parenthesis

    plt.title(f"Social Network Analysis for {target_user}")  # Close bracket/parenthesis
    
    sna_path = output_dir / f"sna_{target_user}.png"  # Assign value to sna_path
    try:  # Start of try block for exception handling
        plt.savefig(sna_path, format="PNG", bbox_inches="tight")  # Close bracket/parenthesis
        plt.close()  # Close bracket/parenthesis
        return sna_path  # Return value from function
    except Exception:  # Handle specific exceptions
        plt.close()  # Close bracket/parenthesis
        return None  # Return value from function


# =========================================================
# Sentiment engine (VADER if available, else fallback)
# =========================================================
class SentimentEngine:  # Define class SentimentEngine
    """
    Uses vaderSentiment if installed:
        pip install vaderSentiment
    If not installed, uses a lightweight lexicon fallback (not as strong as VADER,
    but sufficient for offline demonstration).
    """

    def __init__(self):  # Define function __init__
        self.mode = "fallback"  # Assign value to self.mode
        self.analyzer = None  # Assign value to self.analyzer
        try:  # Start of try block for exception handling
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore

            self.analyzer = SentimentIntensityAnalyzer()  # Assign value to self.analyzer
            self.mode = "vader"  # Assign value to self.mode
        except ImportError:  # Handle specific exceptions
            self.mode = "fallback"  # Assign value to self.mode
            self.analyzer = None  # Assign value to self.analyzer

        # Minimal fallback lexicon (expand if you want)
        self.pos_words = {  # Assign value to self.pos_words
            # Execute statement or expression
            # Execute statement or expression
            "good", "great", "amazing", "love", "happy", "nice", "excellent", "fun", "win", "success",
            "beautiful", "best", "awesome", "positive", "enjoy", "wonderful"  # Execute statement or expression
        }  # Close bracket/parenthesis
        self.neg_words = {  # Assign value to self.neg_words
            # Execute statement or expression
            # Execute statement or expression
            "bad", "terrible", "hate", "sad", "angry", "awful", "worst", "fail", "failure", "negative",
            "pain", "cry", "depressed", "stress", "upset"  # Execute statement or expression
        }  # Close bracket/parenthesis

    def score(self, text: str) -> float:  # Define function score
        text = (text or "").strip()  # Assign value to text
        if not text:  # Check conditional statement
            return 0.0  # Return value from function

        if self.mode == "vader" and self.analyzer is not None:  # Check conditional statement
            # VADER returns compound in [-1, 1]
            return float(self.analyzer.polarity_scores(text).get("compound", 0.0))  # Return value from function

        # Fallback: simple normalized polarity
        words = re.findall(r"[A-Za-z']+", text.lower())  # Assign value to words
        if not words:  # Check conditional statement
            return 0.0  # Return value from function
        pos = sum(1 for w in words if w in self.pos_words)  # Assign value to pos
        neg = sum(1 for w in words if w in self.neg_words)  # Assign value to neg
        raw = pos - neg  # Assign value to raw
        # normalize to approx [-1, 1]
        return max(-1.0, min(1.0, raw / max(5, len(words) / 2)))  # Return value from function


# =========================================================
# Main GUI App
# =========================================================
class OSINTCleanGUI(tk.Tk):  # Define class OSINTCleanGUI
    def __init__(self):  # Define function __init__
        super().__init__()  # Call function super
        self.title("OSINT Dataset Analysis (Offline Mode)")  # Call instance method
        self.geometry("1500x900")  # Call instance method
        self.configure(bg="#050910")

        self.df_all: Optional[pd.DataFrame] = None  # Execute statement or expression
        self.preview_img = None  # Assign value to self.preview_img

        self.sentiment = SentimentEngine()  # Assign value to self.sentiment

        self.setup_style()  # Call instance method
        self.build_ui()  # Call instance method

    # -----------------------------
    # Styling
    # -----------------------------
    def setup_style(self):  # Define function setup_style
        style = ttk.Style()  # Assign value to style
        try:  # Start of try block for exception handling
            style.theme_use("clam")  # Close bracket/parenthesis
        except Exception:  # Handle specific exceptions
            pass  # No-op placeholder

        style.configure(".", background="#050910", foreground="#E5F0FF", fieldbackground="#050910")
        style.configure("Dark.TFrame", background="#050910")
        style.configure("Dark.TLabel", background="#050910", foreground="#E5F0FF")
        style.configure("Dark.TButton", background="#1A2738", foreground="#E5F0FF", padding=6)
        style.map("Dark.TButton", background=[("active", "#22344A"), ("pressed", "#182234")])

        style.configure(  # Execute statement or expression
            "Dark.Treeview",  # Execute statement or expression
            background="#101620",
            foreground="#E5F0FF",
            fieldbackground="#101620",
            rowheight=24,  # Assign value to rowheight
        )  # Close bracket/parenthesis
        style.map("Dark.Treeview", background=[("selected", "#28406A")], foreground=[("selected", "#FFFFFF")])

    # -----------------------------
    # UI layout
    # -----------------------------
    def build_ui(self):  # Define function build_ui
        main = ttk.Frame(self, style="Dark.TFrame")  # Assign value to main
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)  # Close bracket/parenthesis

        # LEFT PANEL
        left = ttk.Frame(main, style="Dark.TFrame")  # Assign value to left
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))  # Close bracket/parenthesis

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(left, text="DATASET CONTROLS", style="Dark.TLabel", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        # Execute statement or expression
        # Execute statement or expression
        ttk.Button(left, text="Upload dataset (CSV/XLSX)", style="Dark.TButton", command=self.upload_dataset).pack(
            fill=tk.X, pady=(12, 6)  # Assign value to fill
        )  # Close bracket/parenthesis

        self.dataset_label = tk.StringVar(value="No dataset loaded.")  # Assign value to self.dataset_label
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(left, textvariable=self.dataset_label, style="Dark.TLabel", wraplength=330).pack(anchor="w")

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)  # Close bracket/parenthesis

        ttk.Label(left, text="Target account", style="Dark.TLabel").pack(anchor="w")  # Close bracket/parenthesis
        self.target_var = tk.StringVar(value="(all)")  # Assign value to self.target_var
        # Assign value to self.target_combo
        # Assign value to self.target_combo
        self.target_combo = ttk.Combobox(left, textvariable=self.target_var, values=["(all)"], state="readonly", width=38)
        self.target_combo.pack(anchor="w", pady=(4, 10))  # Close bracket/parenthesis

        ttk.Label(left, text="Time window", style="Dark.TLabel").pack(anchor="w")  # Close bracket/parenthesis
        self.window_var = tk.StringVar(value="All available")  # Assign value to self.window_var

        for t in ["All available", "Last 7 days", "Last 30 days", "Custom range"]:  # Iterate in a loop
            ttk.Radiobutton(left, text=t, value=t, variable=self.window_var).pack(anchor="w")  # Close bracket/parenthesis

        self.start_entry = ttk.Entry(left, width=18)  # Assign value to self.start_entry
        self.end_entry = ttk.Entry(left, width=18)  # Assign value to self.end_entry

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(left, text="Start (YYYY-MM-DD)", style="Dark.TLabel").pack(anchor="w", pady=(6, 0))
        self.start_entry.pack(anchor="w")  # Close bracket/parenthesis

        ttk.Label(left, text="End (YYYY-MM-DD)", style="Dark.TLabel").pack(anchor="w", pady=(6, 0))  # Close bracket/parenthesis
        self.end_entry.pack(anchor="w")  # Close bracket/parenthesis

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)  # Close bracket/parenthesis

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(left, text="Run analysis:", style="Dark.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Overview Analysis", style="Dark.TButton", command=self.show_overview).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Temporal Analysis", style="Dark.TButton", command=self.show_temporal).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Sentiment Analysis", style="Dark.TButton", command=self.show_sentiment).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Leakage Analysis", style="Dark.TButton", command=self.show_leakage).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Raw Posts", style="Dark.TButton", command=self.show_raw).pack(fill=tk.X, pady=3)
        
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Generate Intelligence Report", style="Dark.TButton", command=self.generate_report).pack(fill=tk.X, pady=(10, 3))

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)  # Close bracket/parenthesis

        self.status_var = tk.StringVar(value="Ready.")  # Assign value to self.status_var
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(left, textvariable=self.status_var, style="Dark.TLabel", wraplength=330).pack(anchor="w")

        # RIGHT PANEL
        self.right = ttk.Frame(main, style="Dark.TFrame")  # Assign value to self.right
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

        self.title_label = ttk.Label(  # Assign value to self.title_label
            self.right,  # Execute statement or expression
            text="Upload a dataset to begin.",  # Assign value to text
            style="Dark.TLabel",  # Assign value to style
            font=("Segoe UI", 14, "bold"),  # Assign value to font
        )  # Close bracket/parenthesis
        self.title_label.pack(anchor="w", pady=(0, 10))  # Close bracket/parenthesis

        self.content_frame = ttk.Frame(self.right, style="Dark.TFrame")  # Assign value to self.content_frame
        self.content_frame.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

    # -----------------------------
    # Dataset loading
    # -----------------------------
    def upload_dataset(self):  # Define function upload_dataset
        path = filedialog.askopenfilename(  # Assign value to path
            title="Select dataset file",  # Assign value to title
            # Assign value to filetypes
            # Assign value to filetypes
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")],
        )  # Close bracket/parenthesis
        if not path:  # Check conditional statement
            return  # Return value from function

        ensure_directories()  # Call function ensure_directories

        p = Path(path)  # Assign value to p
        if p.suffix.lower() not in SUPPORTED_EXTS:  # Check conditional statement
            messagebox.showerror("Unsupported file", "Supported formats: CSV, XLSX, XLS")  # Close bracket/parenthesis
            return  # Return value from function

        dest = DATA_DIR / p.name  # Assign value to dest
        try:  # Start of try block for exception handling
            if p.resolve() != dest.resolve():  # Check conditional statement
                shutil.copy2(p, dest)  # Close bracket/parenthesis
        except Exception:  # Handle specific exceptions
            pass  # No-op placeholder

        try:  # Start of try block for exception handling
            if p.suffix.lower() == ".csv":  # Check conditional statement
                df_raw = pd.read_csv(p)  # Assign value to df_raw
            else:  # Execute if preceding conditions are false
                df_raw = pd.read_excel(p)  # Assign value to df_raw
        except Exception as e:  # Handle specific exceptions
            messagebox.showerror("Load error", f"Failed to load dataset:\n{e}")  # Close bracket/parenthesis
            return  # Return value from function

        self.df_all = normalize_dataset(df_raw)  # Assign value to self.df_all

        if self.df_all.empty:  # Check conditional statement
            messagebox.showerror("Empty dataset", "Dataset loaded but no usable rows were found.")  # Close bracket/parenthesis
            return  # Return value from function

        users = sorted(set(self.df_all["username"].astype(str)))  # Assign value to users
        self.target_combo["values"] = ["(all)"] + users  # Assign value to self.target_combo["values"]
        self.target_var.set("(all)")  # Close bracket/parenthesis

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        self.dataset_label.set(f"Loaded: {p.name}\nRows: {len(self.df_all):,}\nTargets: {len(users)}")
        self.status_var.set("Dataset loaded successfully.")  # Close bracket/parenthesis

        try:  # Start of try block for exception handling
            self.df_all.to_csv(OUTPUT_DIR / "normalized_dataset.csv", index=False)  # Close bracket/parenthesis
        except Exception:  # Handle specific exceptions
            pass  # No-op placeholder

        self.clear_content()  # Call instance method
        self.title_label.config(text="Dataset loaded. Select an analysis.")  # Close bracket/parenthesis

    def filtered_df(self) -> pd.DataFrame:  # Define function filtered_df
        if self.df_all is None:  # Check conditional statement
            return pd.DataFrame()  # Return value from function

        df = self.df_all.copy()  # Assign value to df

        # target filter
        t = self.target_var.get()  # Assign value to t
        if t and t != "(all)":  # Check conditional statement
            df = df[df["username"] == t]  # Assign value to df

        # time-window filter
        mode = self.window_var.get()  # Assign value to mode

        if mode in ("Last 7 days", "Last 30 days"):  # Check conditional statement
            max_date = df["timestamp_utc"].max()  # Assign value to max_date
            if pd.notna(max_date):  # Check conditional statement
                days = 7 if mode == "Last 7 days" else 30  # Assign value to days
                cutoff = max_date - pd.Timedelta(days=days)  # Assign value to cutoff
                df = df[df["timestamp_utc"] >= cutoff]  # Assign value to df

        elif mode == "Custom range":  # Check alternative condition
            s = self.start_entry.get().strip()  # Assign value to s
            e = self.end_entry.get().strip()  # Assign value to e
            if s and e:  # Check conditional statement
                try:  # Start of try block for exception handling
                    sd = datetime.strptime(s, "%Y-%m-%d").date()  # Assign value to sd
                    ed = datetime.strptime(e, "%Y-%m-%d").date()  # Assign value to ed
                    df = df[df["timestamp_utc"].dt.date.between(sd, ed)]  # Assign value to df
                except Exception:  # Handle specific exceptions
                    pass  # No-op placeholder

        return df.sort_values("timestamp_utc", ascending=False)  # Return value from function

    # -----------------------------
    # UI helpers
    # -----------------------------
    def clear_content(self):  # Define function clear_content
        for child in self.content_frame.winfo_children():  # Iterate in a loop
            child.destroy()  # Close bracket/parenthesis

    def make_tree(self, columns, headings, widths):  # Define function make_tree
        frame = ttk.Frame(self.content_frame, style="Dark.TFrame")  # Assign value to frame
        frame.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

        tree = ttk.Treeview(frame, columns=columns, show="headings", style="Dark.Treeview")  # Assign value to tree
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)  # Assign value to vsb
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)  # Assign value to hsb

        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)  # Close bracket/parenthesis

        tree.grid(row=0, column=0, sticky="nsew")  # Close bracket/parenthesis
        vsb.grid(row=0, column=1, sticky="ns")  # Close bracket/parenthesis
        hsb.grid(row=1, column=0, sticky="ew")  # Close bracket/parenthesis

        frame.rowconfigure(0, weight=1)  # Close bracket/parenthesis
        frame.columnconfigure(0, weight=1)  # Close bracket/parenthesis

        for c, h, w in zip(columns, headings, widths):  # Iterate in a loop
            tree.heading(c, text=h)  # Close bracket/parenthesis
            tree.column(c, width=w, anchor="w")  # Close bracket/parenthesis

        return tree  # Return value from function

    def open_url(self, url: str):  # Define function open_url
        if url.startswith("http://") or url.startswith("https://"):  # Check conditional statement
            webbrowser.open(url)  # Close bracket/parenthesis

    def embed_plot(self, fig):  # Define function embed_plot
        """Embed a matplotlib Figure into the content frame (Tk canvas)."""
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)  # Assign value to canvas
        canvas.draw()  # Close bracket/parenthesis
        canvas.get_tk_widget().pack(fill=tk.X, pady=(0, 10))  # Close bracket/parenthesis
        return canvas  # Return value from function

    # =========================================================
    # Analyses
    # =========================================================
    def show_overview(self):  # Define function show_overview
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Overview Analysis")  # Close bracket/parenthesis

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        total_posts = len(df)  # Assign value to total_posts
        loc_posts = int((df["location"].astype(str).str.strip() != "").sum())  # Assign value to loc_posts
        # Assign value to tag_posts
        # Assign value to tag_posts
        tag_posts = int(df["associated_entities"].apply(lambda x: len(x) if isinstance(x, list) else 0).gt(0).sum())

        info = ttk.Label(  # Assign value to info
            self.content_frame,  # Execute statement or expression
            # Assign value to text
            # Assign value to text
            text=f"Total posts: {total_posts} | Posts with location: {loc_posts} | Posts with tagged users: {tag_posts}",
            style="Dark.TLabel",  # Assign value to style
            font=("Consolas", 11),  # Assign value to font
        )  # Close bracket/parenthesis
        info.pack(anchor="w", pady=(0, 10))  # Close bracket/parenthesis

        tree = self.make_tree(  # Assign value to tree
            # Assign value to columns
            # Assign value to columns
            columns=["timestamp_utc", "username", "location", "associated_entities", "caption", "display_url"],
            # Assign value to headings
            # Assign value to headings
            headings=["Timestamp (UTC)", "User", "Location", "Associated Entities", "Caption", "displayUrl"],
            widths=[180, 140, 200, 240, 600, 350],  # Assign value to widths
        )  # Close bracket/parenthesis

        for _, r in df.head(400).iterrows():  # Iterate in a loop
            # Assign value to tagged
            # Assign value to tagged
            tagged = ", ".join(r["associated_entities"]) if isinstance(r["associated_entities"], list) else ""
            tree.insert(  # Execute statement or expression
                "",  # Execute statement or expression
                tk.END,  # Execute statement or expression
                values=[  # Assign value to values
                    str(r["timestamp_utc"]),  # Call function str
                    r["username"],  # Execute statement or expression
                    r["location"],  # Execute statement or expression
                    tagged,  # Execute statement or expression
                    str(r["caption"])[:140],  # Call function str
                    r["display_url"],  # Execute statement or expression
                ],  # Close structure
            )  # Close bracket/parenthesis

        def on_double_click(_event):  # Define function on_double_click
            item = tree.selection()  # Assign value to item
            if not item:  # Check conditional statement
                return  # Return value from function
            vals = tree.item(item[0], "values")  # Assign value to vals
            self.open_url(str(vals[-1]))  # Call instance method

        tree.bind("<Double-1>", on_double_click)  # Close bracket/parenthesis

    def show_temporal(self):  # Define function show_temporal
        """
        Temporal Analysis:
          - Posts per day (chart + table)
          - Posts per hour (bar chart + table)
          - Posts per weekday (bar chart + table)
          - Weekly Pattern of Life (heatmap)
        """
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Temporal Analysis")  # Close bracket/parenthesis

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        df = df.copy()  # Assign value to df
        df = df[pd.notna(df["timestamp_utc"])]  # Assign value to df

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        df["date"] = df["timestamp_utc"].dt.date  # Assign value to df["date"]
        df["hour"] = df["timestamp_utc"].dt.hour  # Assign value to df["hour"]
        df["weekday"] = df["timestamp_utc"].dt.day_name()  # Assign value to df["weekday"]

        # --- Data processing ---
        # Assign value to per_day
        # Assign value to per_day
        per_day = df.groupby("date")["post_id"].count().reset_index(name="posts").sort_values("date")
        # Assign value to per_hour
        # Assign value to per_hour
        per_hour = df.groupby("hour")["post_id"].count().reset_index(name="posts").sort_values("hour")
        # Assign value to weekday_order
        # Assign value to weekday_order
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        # Assign value to per_weekday
        # Assign value to per_weekday
        per_weekday = df.groupby("weekday")["post_id"].count().reindex(weekday_order, fill_value=0).reset_index(name="posts")

        # --- Create a Notebook for tabs ---
        style = ttk.Style()  # Assign value to style
        style.configure("Dark.TNotebook", background="#050910", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#1A2738", foreground="#E5F0FF", padding=[8, 4])
        style.map("Dark.TNotebook.Tab", background=[("selected", "#28406A"), ("active", "#22344A")])
        notebook = ttk.Notebook(self.content_frame, style="Dark.TNotebook")  # Assign value to notebook
        notebook.pack(fill='both', expand=True)  # Close bracket/parenthesis

        # --- Helper for embedding plots in tabs ---
        def embed_plot_in_tab(fig, parent):  # Define function embed_plot_in_tab
            canvas = FigureCanvasTkAgg(fig, master=parent)  # Assign value to canvas
            canvas.draw()  # Close bracket/parenthesis
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
            return canvas  # Return value from function
            
        # =================== TAB 1: Posts per Day ===================
        day_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)  # Assign value to day_frame
        notebook.add(day_frame, text='Posts per Day')  # Close bracket/parenthesis

        per_day_plot = per_day.copy()  # Assign value to per_day_plot
        per_day_plot["date"] = pd.to_datetime(per_day_plot["date"])  # Assign value to per_day_plot["date"]
        fig1, ax1 = plt.subplots(figsize=(9, 4))  # Close bracket/parenthesis
        ax1.plot(per_day_plot["date"], per_day_plot["posts"], marker="o")  # Close bracket/parenthesis
        ax1.set_title("Posting Frequency Over Time")  # Close bracket/parenthesis
        ax1.set_xlabel("Date")  # Close bracket/parenthesis
        ax1.set_ylabel("Posts")  # Close bracket/parenthesis
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())  # Close bracket/parenthesis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))  # Close bracket/parenthesis
        fig1.autofmt_xdate()  # Close bracket/parenthesis
        fig1.tight_layout()  # Close bracket/parenthesis
        embed_plot_in_tab(fig1, day_frame)  # Call function embed_plot_in_tab
        plt.close(fig1)  # Close bracket/parenthesis

        # =================== TAB 2: Posts per Hour ===================
        hour_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)  # Assign value to hour_frame
        notebook.add(hour_frame, text='Posts per Hour')  # Close bracket/parenthesis
        
        fig2, ax2 = plt.subplots(figsize=(9, 4))  # Close bracket/parenthesis
        ax2.bar(per_hour["hour"].astype(int), per_hour["posts"].astype(int))  # Close bracket/parenthesis
        ax2.set_title("Diurnal Posting Pattern")  # Close bracket/parenthesis
        ax2.set_xlabel("Hour of Day (0–23)")  # Close bracket/parenthesis
        ax2.set_ylabel("Posts")  # Close bracket/parenthesis
        ax2.set_xticks(list(range(0, 24, 1)))  # Close bracket/parenthesis
        fig2.tight_layout()  # Close bracket/parenthesis
        embed_plot_in_tab(fig2, hour_frame)  # Call function embed_plot_in_tab
        plt.close(fig2)  # Close bracket/parenthesis

        # =================== TAB 3: Posts per Weekday ===================
        weekday_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)  # Assign value to weekday_frame
        notebook.add(weekday_frame, text='Posts per Weekday')  # Close bracket/parenthesis

        fig3, ax3 = plt.subplots(figsize=(9, 4))  # Close bracket/parenthesis
        ax3.bar(per_weekday["weekday"], per_weekday["posts"])  # Close bracket/parenthesis
        ax3.set_title("Weekly Posting Pattern")  # Close bracket/parenthesis
        ax3.set_xlabel("Weekday")  # Close bracket/parenthesis
        ax3.set_ylabel("Posts")  # Close bracket/parenthesis
        fig3.autofmt_xdate()  # Close bracket/parenthesis
        fig3.tight_layout()  # Close bracket/parenthesis
        embed_plot_in_tab(fig3, weekday_frame)  # Call function embed_plot_in_tab
        plt.close(fig3)  # Close bracket/parenthesis

        # =================== TAB 4: Weekly Pattern of Life Heatmap ===================
        heatmap_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)  # Assign value to heatmap_frame
        notebook.add(heatmap_frame, text='Pattern of Life Heatmap')  # Close bracket/parenthesis

        heatmap_data = pd.crosstab(df['weekday'], df['hour'])  # Assign value to heatmap_data
        heatmap_data = heatmap_data.reindex(columns=range(24), fill_value=0)  # Assign value to heatmap_data
        heatmap_data = heatmap_data.reindex(index=weekday_order, fill_value=0)  # Assign value to heatmap_data

        fig4, ax4 = plt.subplots(figsize=(9, 4))  # Close bracket/parenthesis
        im = ax4.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')  # Assign value to im

        ax4.set_xticks(range(len(heatmap_data.columns)))  # Close bracket/parenthesis
        ax4.set_xticklabels(heatmap_data.columns)  # Close bracket/parenthesis
        ax4.set_yticks(range(len(heatmap_data.index)))  # Close bracket/parenthesis
        ax4.set_yticklabels(heatmap_data.index)  # Close bracket/parenthesis

        cbar = ax4.figure.colorbar(im, ax=ax4)  # Assign value to cbar
        cbar.ax.set_ylabel("Activity Density", rotation=-90, va="bottom")  # Close bracket/parenthesis
        ax4.set_title("Weekly Activity Heatmap (Day vs. Hour)")  # Close bracket/parenthesis
        ax4.set_xlabel("Hour of Day")  # Close bracket/parenthesis
        ax4.set_ylabel("Day of Week")  # Close bracket/parenthesis

        fig4.tight_layout()  # Close bracket/parenthesis
        embed_plot_in_tab(fig4, heatmap_frame)  # Call function embed_plot_in_tab
        plt.close(fig4)  # Close bracket/parenthesis

    def show_sentiment(self):  # Define function show_sentiment
        """
        Sentiment Analysis:
          - compute post-level sentiment from captions
          - show daily average sentiment (chart with readable x-axis)
          - show summary stats + table of recent scored posts
        """
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Sentiment Analysis")  # Close bracket/parenthesis

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        df = df.copy()  # Assign value to df
        df = df[pd.notna(df["timestamp_utc"])]  # Assign value to df

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        df["caption"] = df["caption"].fillna("").astype(str)  # Assign value to df["caption"]
        df["sentiment"] = df["caption"].apply(self.sentiment.score)  # Assign value to df["sentiment"]
        df["date"] = df["timestamp_utc"].dt.date  # Assign value to df["date"]

        # Assign value to daily
        # Assign value to daily
        daily = df.groupby("date")["sentiment"].mean().reset_index(name="avg_sentiment").sort_values("date")
        daily["date"] = pd.to_datetime(daily["date"])  # Assign value to daily["date"]

        # Summary stats
        mean_s = float(df["sentiment"].mean())  # Assign value to mean_s
        med_s = float(df["sentiment"].median())  # Assign value to med_s
        min_s = float(df["sentiment"].min())  # Assign value to min_s
        max_s = float(df["sentiment"].max())  # Assign value to max_s

        ttk.Label(  # Execute statement or expression
            self.content_frame,  # Execute statement or expression
            # Assign value to text
            # Assign value to text
            text=f"Engine: {self.sentiment.mode.upper()} | Mean: {mean_s:.3f} | Median: {med_s:.3f} | Min: {min_s:.3f} | Max: {max_s:.3f}",
            style="Dark.TLabel",  # Assign value to style
            font=("Consolas", 11),  # Assign value to font
        ).pack(anchor="w", pady=(0, 8))  # Close bracket/parenthesis

        # Chart (IMPROVED X-AXIS)
        ttk.Label(  # Execute statement or expression
            self.content_frame,  # Execute statement or expression
            text="Average Sentiment per Day",  # Assign value to text
            style="Dark.TLabel",  # Assign value to style
            font=("Segoe UI", 11, "bold"),  # Assign value to font
        ).pack(anchor="w", pady=(0, 5))  # Close bracket/parenthesis

        fig, ax = plt.subplots(figsize=(9, 3.8))  # Close bracket/parenthesis
        ax.plot(daily["date"], daily["avg_sentiment"], marker="o")  # Close bracket/parenthesis
        ax.axhline(0, linestyle="--")  # Close bracket/parenthesis
        ax.set_title("Daily Sentiment Trend (Average)")  # Close bracket/parenthesis
        ax.set_xlabel("Date")  # Close bracket/parenthesis
        ax.set_ylabel("Average Sentiment (≈ -1 to +1)")  # Close bracket/parenthesis

        ax.xaxis.set_major_locator(mdates.AutoDateLocator())  # Close bracket/parenthesis
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))  # Close bracket/parenthesis
        for label in ax.get_xticklabels():  # Iterate in a loop
            label.set_rotation(45)  # Close bracket/parenthesis
            label.set_ha("right")  # Close bracket/parenthesis

        fig.tight_layout()  # Close bracket/parenthesis
        self.embed_plot(fig)  # Call instance method
        plt.close(fig)  # Close bracket/parenthesis

        # Table of scored posts
        ttk.Label(  # Execute statement or expression
            self.content_frame,  # Execute statement or expression
            text="Recent Posts (Scored)",  # Assign value to text
            style="Dark.TLabel",  # Assign value to style
            font=("Segoe UI", 11, "bold"),  # Assign value to font
        ).pack(anchor="w", pady=(8, 5))  # Close bracket/parenthesis

        tree = self.make_tree(  # Assign value to tree
            columns=["timestamp_utc", "username", "sentiment", "caption", "display_url"],  # Assign value to columns
            headings=["Timestamp (UTC)", "User", "Sentiment", "Caption (truncated)", "displayUrl"],  # Assign value to headings
            widths=[180, 140, 100, 750, 350],  # Assign value to widths
        )  # Close bracket/parenthesis

        for _, r in df.head(500).iterrows():  # Iterate in a loop
            tree.insert(  # Execute statement or expression
                "",  # Execute statement or expression
                tk.END,  # Execute statement or expression
                values=[  # Assign value to values
                    str(r["timestamp_utc"]),  # Call function str
                    r["username"],  # Execute statement or expression
                    f"{float(r['sentiment']):.3f}",  # Execute statement or expression
                    str(r["caption"])[:180],  # Call function str
                    r["display_url"],  # Execute statement or expression
                ],  # Close structure
            )  # Close bracket/parenthesis

        def on_double_click(_event):  # Define function on_double_click
            item = tree.selection()  # Assign value to item
            if not item:  # Check conditional statement
                return  # Return value from function
            vals = tree.item(item[0], "values")  # Assign value to vals
            self.open_url(str(vals[-1]))  # Call instance method

        tree.bind("<Double-1>", on_double_click)  # Close bracket/parenthesis

    def show_raw(self):  # Define function show_raw
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Raw Posts")  # Close bracket/parenthesis

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        tree = self.make_tree(  # Assign value to tree
            columns=["post_id", "timestamp_utc", "username", "caption", "image_ref", "display_url"],  # Assign value to columns
            headings=["Post ID", "Timestamp", "User", "Caption", "Image ref", "displayUrl"],  # Assign value to headings
            widths=[160, 180, 140, 650, 200, 350],  # Assign value to widths
        )  # Close bracket/parenthesis

        for _, r in df.head(800).iterrows():  # Iterate in a loop
            tree.insert(  # Execute statement or expression
                "",  # Execute statement or expression
                tk.END,  # Execute statement or expression
                values=[  # Assign value to values
                    r["post_id"],  # Execute statement or expression
                    str(r["timestamp_utc"]),  # Call function str
                    r["username"],  # Execute statement or expression
                    str(r["caption"])[:160],  # Call function str
                    r["image_ref"],  # Execute statement or expression
                    r["display_url"],  # Execute statement or expression
                ],  # Close structure
            )  # Close bracket/parenthesis

        def on_double_click(_event):  # Define function on_double_click
            item = tree.selection()  # Assign value to item
            if not item:  # Check conditional statement
                return  # Return value from function
            vals = tree.item(item[0], "values")  # Assign value to vals
            self.open_url(str(vals[-1]))  # Call instance method

        tree.bind("<Double-1>", on_double_click)  # Close bracket/parenthesis

    def show_leakage(self):  # Define function show_leakage
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Image Leakage & EXIF Analysis")  # Close bracket/parenthesis

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        container = ttk.Frame(self.content_frame, style="Dark.TFrame")  # Assign value to container
        container.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

        left = ttk.Frame(container, style="Dark.TFrame")  # Assign value to left
        right = ttk.Frame(container, style="Dark.TFrame")  # Assign value to right
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=(10, 0))  # Close bracket/parenthesis

        tree_frame = ttk.Frame(left, style="Dark.TFrame")  # Assign value to tree_frame
        tree_frame.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

        tree = ttk.Treeview(  # Assign value to tree
            tree_frame,  # Execute statement or expression
            # Assign value to columns
            # Assign value to columns
            columns=["post_id", "username", "local_image", "exif", "gps", "lat", "lon", "display_url"],
            show="headings",  # Assign value to show
            style="Dark.Treeview",  # Assign value to style
        )  # Close bracket/parenthesis
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)  # Assign value to vsb
        tree.configure(yscrollcommand=vsb.set)  # Close bracket/parenthesis

        tree.grid(row=0, column=0, sticky="nsew")  # Close bracket/parenthesis
        vsb.grid(row=0, column=1, sticky="ns")  # Close bracket/parenthesis

        tree_frame.rowconfigure(0, weight=1)  # Close bracket/parenthesis
        tree_frame.columnconfigure(0, weight=1)  # Close bracket/parenthesis

        cols = [  # Assign value to cols
            ("post_id", "Post ID", 140),  # Execute statement or expression
            ("username", "User", 120),  # Execute statement or expression
            ("local_image", "Local image", 240),  # Execute statement or expression
            ("exif", "EXIF", 60),  # Execute statement or expression
            ("gps", "GPS", 60),  # Execute statement or expression
            ("lat", "Lat", 90),  # Execute statement or expression
            ("lon", "Lon", 90),  # Execute statement or expression
            ("display_url", "displayUrl", 320),  # Execute statement or expression
        ]  # Close bracket/parenthesis
        for c, h, w in cols:  # Iterate in a loop
            tree.heading(c, text=h)  # Close bracket/parenthesis
            tree.column(c, width=w, anchor="w")  # Close bracket/parenthesis

        right.rowconfigure(0, weight=1)  # Give image and details equal weight
        right.rowconfigure(1, weight=1)  # Close bracket/parenthesis
        right.columnconfigure(0, weight=1)  # Close bracket/parenthesis

        preview_label = tk.Label(right, bg="#101620", fg="#E5F0FF", text="No image selected")
        preview_label.grid(row=0, column=0, sticky="nsew")  # Close bracket/parenthesis

        details = tk.Text(right, bg="#050910", fg="#E5F0FF", insertbackground="#E5F0FF", wrap="word")
        details.grid(row=1, column=0, sticky="nsew", pady=(10, 0))  # Close bracket/parenthesis

        for _, r in df.iterrows():  # Iterate in a loop
            img_ref = str(r.get("image_ref", "")).strip()  # Assign value to img_ref
            local_img_path = ""  # Assign value to local_img_path

            if img_ref:  # Check conditional statement
                p = Path(img_ref)  # Assign value to p
                if p.exists():  # Check conditional statement
                    local_img_path = str(p)  # Assign value to local_img_path
                else:  # Execute if preceding conditions are false
                    candidates = [  # Assign value to candidates
                        DATA_DIR / img_ref,  # Execute statement or expression
                        DATA_DIR / "images" / img_ref,  # Execute statement or expression
                        DATA_DIR / r["username"] / img_ref,  # Execute statement or expression
                        DATA_DIR / r["username"] / "images" / img_ref,  # Execute statement or expression
                    ]  # Close bracket/parenthesis
                    for c in candidates:  # Iterate in a loop
                        if c.exists():  # Check conditional statement
                            local_img_path = str(c.resolve())  # Assign value to local_img_path
                            break  # Exit the current loop

            exif_present = False  # Assign value to exif_present
            gps_present = False  # Assign value to gps_present
            lat = lon = None  # Assign value to lat

            if local_img_path:  # Check conditional statement
                exif_present, gps_present, lat, lon = extract_exif(Path(local_img_path))  # Close bracket/parenthesis

                try:  # Start of try block for exception handling
                    user_dir = OUTPUT_IMAGES_DIR / str(r["username"])  # Assign value to user_dir
                    user_dir.mkdir(parents=True, exist_ok=True)  # Close bracket/parenthesis
                    dst = user_dir / Path(local_img_path).name  # Assign value to dst
                    if not dst.exists():  # Check conditional statement
                        shutil.copy2(local_img_path, dst)  # Close bracket/parenthesis
                except Exception:  # Handle specific exceptions
                    pass  # No-op placeholder

            tree.insert(  # Execute statement or expression
                "",  # Execute statement or expression
                tk.END,  # Execute statement or expression
                values=[  # Assign value to values
                    r["post_id"],  # Execute statement or expression
                    r["username"],  # Execute statement or expression
                    local_img_path,  # Execute statement or expression
                    "Yes" if exif_present else "No",  # Execute statement or expression
                    "Yes" if gps_present else "No",  # Execute statement or expression
                    "" if lat is None else f"{lat:.6f}",  # Execute statement or expression
                    "" if lon is None else f"{lon:.6f}",  # Execute statement or expression
                    r["display_url"],  # Execute statement or expression
                ],  # Close structure
            )  # Close bracket/parenthesis

        def on_select(_event):  # Define function on_select
            sel = tree.selection()  # Assign value to sel
            if not sel:  # Check conditional statement
                return  # Return value from function
            vals = tree.item(sel[0], "values")  # Assign value to vals
            local_img = str(vals[2]).strip()  # Assign value to local_img
            url = str(vals[-1]).strip()  # Assign value to url

            if local_img and Path(local_img).exists():  # Check conditional statement
                try:  # Start of try block for exception handling
                    img = Image.open(local_img)  # Assign value to img
                    img.thumbnail((520, 520))  # Close bracket/parenthesis
                    self.preview_img = ImageTk.PhotoImage(img)  # Assign value to self.preview_img
                    preview_label.config(image=self.preview_img, text="")  # Close bracket/parenthesis
                except Exception:  # Handle specific exceptions
                    preview_label.config(image="", text="Preview failed")  # Close bracket/parenthesis
            elif url:  # Check alternative condition
                preview_label.config(image="", text="Downloading image...")  # Close bracket/parenthesis
                try:  # Start of try block for exception handling
                    response = requests.get(url, timeout=10)  # Assign value to response
                    if response.status_code == 200:  # Check conditional statement
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:  # Use context manager
                            tmp_file.write(response.content)  # Close bracket/parenthesis
                            tmp_path = Path(tmp_file.name)  # Assign value to tmp_path
                        
                        exif_present, gps_present, lat, lon = extract_exif(tmp_path)  # Close bracket/parenthesis
                        tree.set(sel[0], "exif", "Yes" if exif_present else "No")  # Close bracket/parenthesis
                        tree.set(sel[0], "gps", "Yes" if gps_present else "No")  # Close bracket/parenthesis
                        tree.set(sel[0], "lat", "" if lat is None else f"{lat:.6f}")  # Close bracket/parenthesis
                        tree.set(sel[0], "lon", "" if lon is None else f"{lon:.6f}")  # Close bracket/parenthesis

                        img = Image.open(tmp_path)  # Assign value to img
                        img.thumbnail((520, 520))  # Close bracket/parenthesis
                        self.preview_img = ImageTk.PhotoImage(img)  # Assign value to self.preview_img
                        preview_label.config(image=self.preview_img, text="")  # Close bracket/parenthesis
                        local_img = str(tmp_path)  # Assign value to local_img
                    elif response.status_code == 403:  # Check alternative condition
                        preview_label.config(image="", text="Image URL expired or forbidden.")  # Close bracket/parenthesis
                    else:  # Execute if preceding conditions are false
                        # Close bracket/parenthesis
                        # Close bracket/parenthesis
                        preview_label.config(image="", text=f"Failed to download.\nStatus: {response.status_code}")
                except requests.exceptions.RequestException as e:  # Handle specific exceptions
                    preview_label.config(image="", text=f"Download error:\n{e}")  # Close bracket/parenthesis
                except Exception:  # Handle specific exceptions
                    preview_label.config(image="", text="Image processing failed.")  # Close bracket/parenthesis
            else:  # Execute if preceding conditions are false
                preview_label.config(image="", text="No local image or URL.")  # Close bracket/parenthesis

            details.delete("1.0", tk.END)  # Close bracket/parenthesis
            details.insert(  # Execute statement or expression
                "1.0",  # Execute statement or expression
                f"Post ID: {vals[0]}\n"  # Execute statement or expression
                f"User: {vals[1]}\n"  # Execute statement or expression
                f"Local image: {local_img or '(none)'}\n"  # Execute statement or expression
                f"EXIF: {vals[3]}\n"  # Execute statement or expression
                f"GPS: {vals[4]}\n"  # Execute statement or expression
                f"Lat: {vals[5]}\n"  # Execute statement or expression
                f"Lon: {vals[6]}\n"  # Execute statement or expression
                f"displayUrl: {url}\n",  # Execute statement or expression
            )  # Close bracket/parenthesis

        def on_double_click(_event):  # Define function on_double_click
            sel = tree.selection()  # Assign value to sel
            if not sel:  # Check conditional statement
                return  # Return value from function
            vals = tree.item(sel[0], "values")  # Assign value to vals
            self.open_url(str(vals[-1]))  # Call instance method

        tree.bind("<<TreeviewSelect>>", on_select)  # Close bracket/parenthesis
        tree.bind("<Double-1>", on_double_click)  # Close bracket/parenthesis

    def generate_report(self):  # Define function generate_report
        """Generates a detailed HTML intelligence report for the selected target."""
        df_filtered = self.filtered_df()  # Assign value to df_filtered
        if df_filtered.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            messagebox.showinfo("Report Generation", "No data matches the current filter. Cannot generate report.")
            return  # Return value from function

        target_user = self.target_var.get()  # Assign value to target_user
        if not target_user or target_user == "(all)":  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            messagebox.showinfo("Report Generation", "Please select a single target account to generate a report.")
            return  # Return value from function

        now = datetime.now()  # Assign value to now
        # Assign value to report_path
        # Assign value to report_path
        report_path = OUTPUT_DIR / f"intelligence_report_{target_user}_{now.strftime('%Y%m%d_%H%M%S')}.html"
        self.status_var.set("Generating report...")  # Close bracket/parenthesis
        self.update_idletasks()  # Call instance method

        # --- 1. Data Enrichment ---
        df = df_filtered.copy()  # Assign value to df
        
        # Sentiment
        if 'sentiment' not in df.columns:  # Check conditional statement
            df['sentiment'] = df['caption'].fillna("").astype(str).apply(self.sentiment.score)  # Assign value to df['sentiment']
        
        # Temporal features
        df['hour'] = df['timestamp_utc'].dt.hour  # Assign value to df['hour']
        df['weekday'] = df['timestamp_utc'].dt.day_name()  # Assign value to df['weekday']
        df_sorted = df.sort_values('timestamp_utc').reset_index(drop=True)  # Assign value to df_sorted

        # Location features
        # This part is illustrative. A full implementation would integrate EXIF data from show_leakage.
        # For this refactoring, we'll assume lat/lon might be in the original data.
        df_sorted['inferred_city'] = None  # Assign value to df_sorted['inferred_city']
        df_sorted['inferred_country'] = None  # Assign value to df_sorted['inferred_country']
        df_sorted['inferred_timezone'] = None  # Assign value to df_sorted['inferred_timezone']
        if best_col(df_sorted, ['lat', 'latitude']) and best_col(df_sorted, ['lon', 'longitude']):  # Check conditional statement
            c_lat = best_col(df_sorted, ['lat', 'latitude'])  # Assign value to c_lat
            c_lon = best_col(df_sorted, ['lon', 'longitude'])  # Assign value to c_lon
            # Assign value to loc_data
            # Assign value to loc_data
            loc_data = df_sorted.apply(lambda row: infer_location_data(row[c_lat], row[c_lon], row['location']), axis=1)
            # Assign value to loc_df
            # Assign value to loc_df
            loc_df = pd.DataFrame(loc_data.tolist(), index=df_sorted.index, columns=['inferred_city', 'inferred_country', 'inferred_timezone'])
            df_sorted.update(loc_df)  # Close bracket/parenthesis

        # Heuristic Categorization
        df_sorted = categorize_location(df_sorted)  # Assign value to df_sorted

        # --- 2. Analysis Modules ---
        # Executive Summary
        total_posts = len(df_sorted)  # Assign value to total_posts
        first_post_date = df_sorted['timestamp_utc'].min().strftime('%Y-%m-%d')  # Assign value to first_post_date
        last_post_date = df_sorted['timestamp_utc'].max().strftime('%Y-%m-%d')  # Assign value to last_post_date

        # Spatial Analysis
        location_counts = df_sorted[df_sorted['location'] != '']['location'].value_counts().head(10)  # Assign value to location_counts
        loc_analysis_html = "<h4>Most Frequent Locations</h4>"  # Assign value to loc_analysis_html
        if not location_counts.empty:  # Check conditional statement
            loc_table = location_counts.to_frame().to_html()  # Assign value to loc_table
            loc_analysis_html += loc_table  # Assign value to loc_analysis_html
        else:  # Execute if preceding conditions are false
            loc_analysis_html += "<p>No significant location data found.</p>"  # Assign value to loc_analysis_html
        
        # Heuristic categorization table
        cat_data = df_sorted[df_sorted['location_category'] != 'Uncategorized']  # Assign value to cat_data
        if not cat_data.empty:  # Check conditional statement
            def get_unique_locations(s):  # Define function get_unique_locations
                locs = s.dropna().astype(str)  # Assign value to locs
                locs = locs[locs.str.strip() != '']  # Assign value to locs
                return ", ".join(sorted(set(locs)))  # Return value from function
                
            cat_summary = cat_data.groupby('location_category').agg(  # Assign value to cat_summary
                count=('location_category', 'count'),  # Assign value to count
                associated_locations=('location', get_unique_locations)  # Assign value to associated_locations
            ).reset_index()  # Close bracket/parenthesis
            
            cat_summary = cat_summary.sort_values(by='count', ascending=False)  # Assign value to cat_summary
            
            loc_analysis_html += "<h4>Heuristic Location Categories</h4>"  # Assign value to loc_analysis_html
            loc_analysis_html += cat_summary.to_html(index=False)  # Assign value to loc_analysis_html

        # SNA
        sna_path = generate_sna_graph(df_sorted, target_user, OUTPUT_DIR)  # Assign value to sna_path
        sna_html = "<h3>Social Network Analysis</h3>"  # Assign value to sna_html
        if sna_path:  # Check conditional statement
            try:  # Start of try block for exception handling
                with open(sna_path, "rb") as f:  # Use context manager
                    encoded_img = base64.b64encode(f.read()).decode('utf-8')  # Assign value to encoded_img
                # Assign value to sna_html
                # Assign value to sna_html
                sna_html += f'<img src="data:image/png;base64,{encoded_img}" alt="SNA Graph" style="max-width:100%;">'
                # Assign value to sna_html
                # Assign value to sna_html
                sna_html += "<p>The graph shows entities frequently mentioned or tagged by the target. Edge weight indicates interaction frequency.</p>"
            except Exception as e:  # Handle specific exceptions
                sna_html += f"<p>Could not embed SNA graph: {e}</p>"  # Assign value to sna_html
        else:  # Execute if preceding conditions are false
            sna_html += "<p>No social network data to display.</p>"  # Assign value to sna_html

        # Anomaly Detection
        anomalies = []  # Assign value to anomalies
        # Travel Anomaly
        df_sorted['prev_timezone'] = df_sorted['inferred_timezone'].shift(1)  # Assign value to df_sorted['prev_timezone']
        # Assign value to travel_anomalies
        # Assign value to travel_anomalies
        travel_anomalies = df_sorted[(df_sorted['inferred_timezone'].notna()) & (df_sorted['prev_timezone'].notna()) & (df_sorted['inferred_timezone'] != df_sorted['prev_timezone'])]
        for _, row in travel_anomalies.iterrows():  # Iterate in a loop
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            anomalies.append(f"<b>Travel Anomaly:</b> Detected travel to {row['inferred_timezone']} on {row['timestamp_utc']:%Y-%m-%d}.")
        
        # Mood Drop Anomaly
        # Assign value to df_sorted['rolling_sentiment']
        # Assign value to df_sorted['rolling_sentiment']
        df_sorted['rolling_sentiment'] = df_sorted['sentiment'].rolling(window=5, min_periods=1).mean()
        # Assign value to mood_drops
        # Assign value to mood_drops
        mood_drops = df_sorted[(df_sorted['sentiment'] < -0.5) & (df_sorted['rolling_sentiment'].shift(1) > 0)]
        for _, row in mood_drops.iterrows():  # Iterate in a loop
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            anomalies.append(f"<b>Mood Drop:</b> Significant negative sentiment post on {row['timestamp_utc']:%Y-%m-%d} following a period of positive sentiment.")
        
        # Routine Disruption (Sleep)
        # Assumes sleep is 00:00-06:00 local time. Requires timezone.
        disruptions = df_sorted[df_sorted['inferred_timezone'].notna()]  # Assign value to disruptions
        if not disruptions.empty:  # Check conditional statement
            # Assign value to disruptions['local_time']
            # Assign value to disruptions['local_time']
            disruptions['local_time'] = disruptions.apply(lambda row: row['timestamp_utc'].tz_convert(row['inferred_timezone']), axis=1)
            sleep_posts = disruptions[disruptions['local_time'].dt.hour.between(0, 6)]  # Assign value to sleep_posts
            for _, row in sleep_posts.iterrows():  # Iterate in a loop
                # Close bracket/parenthesis
                # Close bracket/parenthesis
                anomalies.append(f"<b>Routine Disruption:</b> Post detected during typical sleep hours at {row['local_time']:%H:%M} local time on {row['local_time']:%Y-%m-%d}.")

        anomaly_html = "<h3>Anomaly Detection</h3>"  # Assign value to anomaly_html
        if anomalies:  # Check conditional statement
            anomaly_html += "<ul>" + "".join([f"<li>{a}</li>" for a in anomalies]) + "</ul>"  # Assign value to anomaly_html
        else:  # Execute if preceding conditions are false
            anomaly_html += "<p>No significant anomalies detected in this dataset.</p>"  # Assign value to anomaly_html

        # User Grievances
        grievances = df_sorted[df_sorted['sentiment'] < -0.5].sort_values('sentiment').head(5)  # Assign value to grievances
        grievance_html = "<h3>User Grievances (Top Negative Posts)</h3>"  # Assign value to grievance_html
        if not grievances.empty:  # Check conditional statement
            grievance_html += "<ul>"  # Assign value to grievance_html
            for _, row in grievances.iterrows():  # Iterate in a loop
                grievance_html += f"<li>({row['sentiment']:.2f}) {row['caption'][:150]}...</li>"  # Assign value to grievance_html
            grievance_html += "</ul>"  # Assign value to grievance_html
        else:  # Execute if preceding conditions are false
            grievance_html += "<p>No significant negative posts found.</p>"  # Assign value to grievance_html

        # Mosaic Effect Conclusion
        mosaic_conclusion = """
        <h3>The Mosaic Effect: Synthesized Intelligence</h3>
        <p>This section synthesizes the individual analyses into a cohesive narrative.</p>
        """
        if anomalies:  # Check conditional statement
            # Assign value to mosaic_conclusion
            # Assign value to mosaic_conclusion
            mosaic_conclusion += "<p>The target's pattern of life shows significant disruptions. The detected anomalies, when viewed together, suggest periods of stress, travel, or unusual activity. For instance, a mood drop coinciding with a travel anomaly could indicate stressful travel. These events should be cross-referenced with other intelligence sources.</p>"
            
            if not travel_anomalies.empty:  # Check conditional statement
                mosaic_conclusion += "<h4>Travel Anomalies</h4><ul>"  # Assign value to mosaic_conclusion
                for _, row in travel_anomalies.iterrows():  # Iterate in a loop
                    # Assign value to loc
                    # Assign value to loc
                    loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                    # Assign value to mosaic_conclusion
                    # Assign value to mosaic_conclusion
                    mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Time:</b> {row['timestamp_utc']} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                mosaic_conclusion += "</ul>"  # Assign value to mosaic_conclusion
                
            if 'sleep_posts' in locals() and not sleep_posts.empty:  # Check conditional statement
                mosaic_conclusion += "<h4>Routine Disruptions (Sleep)</h4><ul>"  # Assign value to mosaic_conclusion
                for _, row in sleep_posts.iterrows():  # Iterate in a loop
                    # Assign value to loc
                    # Assign value to loc
                    loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                    # Assign value to mosaic_conclusion
                    # Assign value to mosaic_conclusion
                    mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Local Time:</b> {row['local_time']:%Y-%m-%d %H:%M} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                mosaic_conclusion += "</ul>"  # Assign value to mosaic_conclusion
                
            if not mood_drops.empty:  # Check conditional statement
                mosaic_conclusion += "<h4>Mood Drops</h4><ul>"  # Assign value to mosaic_conclusion
                for _, row in mood_drops.iterrows():  # Iterate in a loop
                    # Assign value to loc
                    # Assign value to loc
                    loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                    # Assign value to mosaic_conclusion
                    # Assign value to mosaic_conclusion
                    mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Time:</b> {row['timestamp_utc']} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                mosaic_conclusion += "</ul>"  # Assign value to mosaic_conclusion
        else:  # Execute if preceding conditions are false
            # Assign value to mosaic_conclusion
            # Assign value to mosaic_conclusion
            mosaic_conclusion += "<p>The target exhibits a stable and predictable pattern of life. Their activity is consistent, with few deviations from their established routine. This predictability can be used to forecast future behavior.</p>"
        
        if not grievances.empty:  # Check conditional statement
            # Assign value to mosaic_conclusion
            # Assign value to mosaic_conclusion
            mosaic_conclusion += "<p>Recurring negative sentiment (grievances) often centers on specific themes. Further analysis of these themes could reveal the target's personal or professional stressors.</p>"
            mosaic_conclusion += "<h4>Grievances</h4><ul>"  # Assign value to mosaic_conclusion
            for _, row in grievances.iterrows():  # Iterate in a loop
                # Assign value to loc
                # Assign value to loc
                loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                # Assign value to mosaic_conclusion
                # Assign value to mosaic_conclusion
                mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Time:</b> {row['timestamp_utc']} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
            mosaic_conclusion += "</ul>"  # Assign value to mosaic_conclusion
        
        if sna_path:  # Check conditional statement
            # Assign value to mosaic_conclusion
            # Assign value to mosaic_conclusion
            mosaic_conclusion += "<p>The social network analysis identifies key individuals in the target's digital life. These individuals represent potential sources of secondary information leakage and are persons of interest for further investigation.</p>"

        # --- 3. HTML Assembly ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Intelligence Report: {target_user}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 960px; margin: 20px auto; }}
                h1, h2, h3, h4 {{ color: #1A2738; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                h1 {{ text-align: center; }}
                .section {{ background-color: #f9f9f9; padding: 15px; border: 1px solid #eee; border-radius: 5px; margin-bottom: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #eef; }}
            </style>
        </head>
        <body>
            <h1>OSINT Intelligence Report</h1>
            <p style="text-align: center;"><strong>Target:</strong> {target_user} | <strong>Report Date:</strong> {now.strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="section">
                <h2>Executive Summary</h2>
                <p>This report covers <strong>{total_posts} posts</strong> from <strong>{first_post_date}</strong> to <strong>{last_post_date}</strong>.</p>
            </div>

            <div class="section">
                <h2>Spatial Analysis (The 'Where')</h2>
                {loc_analysis_html}
            </div>

            <div class="section">
                <h2>Social Network & Leakage (The 'Who')</h2>
                {sna_html}
            </div>

            <div class="section">
                <h2>Behavioural & Anomaly Analysis (The 'Why' and 'When')</h2>
                {anomaly_html}
                {grievance_html}
            </div>

            <div class="section">
                <h2>Conclusion</h2>
                {mosaic_conclusion}
            </div>
        </body>
        </html>
        """

        # --- 4. Write file and open ---
        try:  # Start of try block for exception handling
            with open(report_path, "w", encoding="utf-8") as f:  # Use context manager
                f.write(html_content)  # Close bracket/parenthesis
            webbrowser.open(report_path.resolve().as_uri())  # Close bracket/parenthesis
            self.status_var.set(f"Report saved to {report_path.name}")  # Close bracket/parenthesis
        except Exception as e:  # Handle specific exceptions
            messagebox.showerror("Error", f"Failed to write report file:\n{e}")  # Close bracket/parenthesis
            self.status_var.set("Error generating report.")  # Close bracket/parenthesis


def main():  # Define function main
    ensure_directories()  # Call function ensure_directories
    app = OSINTCleanGUI()  # Assign value to app
    app.mainloop()  # Close bracket/parenthesis


if __name__ == "__main__":  # Check conditional statement
    main()  # Call function main
