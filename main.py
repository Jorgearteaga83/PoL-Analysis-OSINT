from __future__ import annotations

import os
import re
import json
import shutil
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd
from PIL import Image, ImageTk, ExifTags
import openpyxl

# Charts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates


# =========================================================
# Directories
# =========================================================
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}


def ensure_directories():
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    OUTPUT_IMAGES_DIR.mkdir(exist_ok=True, parents=True)


# =========================================================
# Utility helpers
# =========================================================
def best_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return the first matching column name from candidates (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def to_datetime_safe(x: Any) -> pd.Timestamp | pd.NaT:
    """Parse timestamps robustly (unix seconds/ms OR ISO strings). Always UTC."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return pd.NaT

    if isinstance(x, (int, float)) and not pd.isna(x):
        try:
            xi = int(x)
            if xi > 10_000_000_000:  # likely ms
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")
        except Exception:
            return pd.NaT

    s = str(x).strip()
    if not s:
        return pd.NaT

    if re.fullmatch(r"\d{10,13}", s):
        try:
            xi = int(s)
            if xi > 10_000_000_000:
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")
        except Exception:
            return pd.NaT

    return pd.to_datetime(s, utc=True, errors="coerce")


def safe_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def extract_tagged_users(cell: Any) -> list[str]:
    """Extract tagged usernames from list/dict/json-string or comma/space string."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []

    if isinstance(cell, list):
        out = []
        for item in cell:
            if isinstance(item, str):
                out.append(item.strip().lstrip("@"))
            elif isinstance(item, dict):
                if isinstance(item.get("username"), str):
                    out.append(item["username"].strip().lstrip("@"))
                elif isinstance(item.get("user"), dict) and isinstance(item["user"].get("username"), str):
                    out.append(item["user"]["username"].strip().lstrip("@"))
        return sorted({x for x in out if x})

    if isinstance(cell, dict):
        if "taggedUsers" in cell:
            return extract_tagged_users(cell.get("taggedUsers"))
        if "users" in cell:
            return extract_tagged_users(cell.get("users"))
        if isinstance(cell.get("username"), str):
            return [cell["username"].strip().lstrip("@")]
        return []

    s = str(cell).strip()
    if not s:
        return []

    if s.startswith("[") or s.startswith("{"):
        obj = safe_json_loads(s)
        if obj is not None:
            return extract_tagged_users(obj)

    parts = re.split(r"[,\s]+", s)
    cleaned = [p.strip().lstrip("@") for p in parts if p.strip()]
    return sorted({x for x in cleaned if x})


# =========================================================
# EXIF GPS parsing
# =========================================================
GPSTAGS = ExifTags.GPSTAGS


def ratio_to_float(x):
    try:
        if hasattr(x, "numerator") and hasattr(x, "denominator"):
            return float(x.numerator) / float(x.denominator)
        if isinstance(x, (tuple, list)) and len(x) == 2:
            num, den = x
            return float(num) / float(den) if den else 0.0
        return float(x)
    except Exception:
        return 0.0


def dms_to_decimal(dms, ref):
    try:
        deg = ratio_to_float(dms[0])
        minutes = ratio_to_float(dms[1])
        seconds = ratio_to_float(dms[2])
        dec = deg + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            dec = -dec
        return dec
    except Exception:
        return None


def extract_exif(path: Path):
    """
    Returns:
        exif_readable(bool) -> could we read EXIF container
        gps_present(bool)    -> GPS fields present
        lat(float|None), lon(float|None)
    """
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return False, False, None, None

        gps_tag = None
        for k, v in ExifTags.TAGS.items():
            if v == "GPSInfo":
                gps_tag = k
                break

        if gps_tag is None or gps_tag not in exif:
            return True, False, None, None

        gps_info = exif[gps_tag]
        if not isinstance(gps_info, dict):
            return True, False, None, None

        decoded = {}
        for key, val in gps_info.items():
            decoded[GPSTAGS.get(key, key)] = val

        lat = lon = None
        if "GPSLatitude" in decoded and "GPSLatitudeRef" in decoded:
            lat = dms_to_decimal(decoded["GPSLatitude"], str(decoded["GPSLatitudeRef"]))
        if "GPSLongitude" in decoded and "GPSLongitudeRef" in decoded:
            lon = dms_to_decimal(decoded["GPSLongitude"], str(decoded["GPSLongitudeRef"]))

        return True, True, lat, lon
    except Exception:
        return False, False, None, None


# =========================================================
# Dataset Normalizer
# =========================================================
def normalize_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Harmonise heterogeneous CSV/XLSX schemas into a consistent OSINT analysis table.
    Output schema:
        post_id, username, timestamp_utc, caption, display_url, post_url, location,
        tagged_users(list[str]), image_ref
    """
    df = df_raw.copy()

    c_post = best_col(df, ["post_id", "id", "postId", "shortCode", "shortcode"])
    c_user = best_col(df, ["account", "username", "ownerUsername", "owner.username"])
    c_time = best_col(df, ["timestamp_utc", "timestamp", "takenAtTimestamp", "createdAt"])
    c_caption = best_col(df, ["caption", "text", "description"])
    c_url = best_col(df, ["display_url", "displayUrl", "imageUrl"])
    c_posturl = best_col(df, ["post_url", "url"])
    c_loc = best_col(df, ["location", "locationName", "location_name", "placeName"])
    c_tagged = best_col(df, ["tagged_users", "taggedUsers", "userTags"])
    c_img = best_col(df, ["image_ref", "image_filename", "imageFilename", "image_path", "local_path"])

    out = pd.DataFrame()
    out["post_id"] = df[c_post].astype(str) if c_post else ""
    out["username"] = df[c_user].astype(str) if c_user else "unknown"

    out["timestamp_utc"] = df[c_time].apply(to_datetime_safe) if c_time else pd.NaT
    out["caption"] = df[c_caption].fillna("").astype(str) if c_caption else ""
    out["display_url"] = df[c_url].fillna("").astype(str) if c_url else ""
    out["post_url"] = df[c_posturl].fillna("").astype(str) if c_posturl else ""
    out["location"] = df[c_loc].fillna("").astype(str) if c_loc else ""

    if c_tagged:
        out["tagged_users"] = df[c_tagged].apply(extract_tagged_users)
    else:
        out["tagged_users"] = [[] for _ in range(len(df))]

    out["image_ref"] = df[c_img].fillna("").astype(str) if c_img else ""

    # cleanup
    out["username"] = out["username"].fillna("unknown").astype(str).str.strip()
    out["post_id"] = out["post_id"].fillna("").astype(str).str.strip()

    out = out[out["post_id"] != ""]
    out = out[out["username"] != "unknown"]

    return out.reset_index(drop=True)


# =========================================================
# Sentiment engine (VADER if available, else fallback)
# =========================================================
class SentimentEngine:
    """
    Uses vaderSentiment if installed:
        pip install vaderSentiment
    If not installed, uses a lightweight lexicon fallback (not as strong as VADER,
    but sufficient for offline demonstration).
    """

    def __init__(self):
        self.mode = "fallback"
        self.analyzer = None
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore

            self.analyzer = SentimentIntensityAnalyzer()
            self.mode = "vader"
        except ImportError:
            self.mode = "fallback"
            self.analyzer = None

        # Minimal fallback lexicon (expand if you want)
        self.pos_words = {
            "good", "great", "amazing", "love", "happy", "nice", "excellent", "fun", "win", "success",
            "beautiful", "best", "awesome", "positive", "enjoy", "wonderful"
        }
        self.neg_words = {
            "bad", "terrible", "hate", "sad", "angry", "awful", "worst", "fail", "failure", "negative",
            "pain", "cry", "depressed", "stress", "upset"
        }

    def score(self, text: str) -> float:
        text = (text or "").strip()
        if not text:
            return 0.0

        if self.mode == "vader" and self.analyzer is not None:
            # VADER returns compound in [-1, 1]
            return float(self.analyzer.polarity_scores(text).get("compound", 0.0))

        # Fallback: simple normalized polarity
        words = re.findall(r"[A-Za-z']+", text.lower())
        if not words:
            return 0.0
        pos = sum(1 for w in words if w in self.pos_words)
        neg = sum(1 for w in words if w in self.neg_words)
        raw = pos - neg
        # normalize to approx [-1, 1]
        return max(-1.0, min(1.0, raw / max(5, len(words) / 2)))


# =========================================================
# Main GUI App
# =========================================================
class OSINTCleanGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OSINT Dataset Analysis (Offline Mode)")
        self.geometry("1500x900")
        self.configure(bg="#050910")

        self.df_all: Optional[pd.DataFrame] = None
        self.preview_img = None

        self.sentiment = SentimentEngine()

        self.setup_style()
        self.build_ui()

    # -----------------------------
    # Styling
    # -----------------------------
    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background="#050910", foreground="#E5F0FF", fieldbackground="#050910")
        style.configure("Dark.TFrame", background="#050910")
        style.configure("Dark.TLabel", background="#050910", foreground="#E5F0FF")
        style.configure("Dark.TButton", background="#1A2738", foreground="#E5F0FF", padding=6)
        style.map("Dark.TButton", background=[("active", "#22344A"), ("pressed", "#182234")])

        style.configure(
            "Dark.Treeview",
            background="#101620",
            foreground="#E5F0FF",
            fieldbackground="#101620",
            rowheight=24,
        )
        style.map("Dark.Treeview", background=[("selected", "#28406A")], foreground=[("selected", "#FFFFFF")])

    # -----------------------------
    # UI layout
    # -----------------------------
    def build_ui(self):
        main = ttk.Frame(self, style="Dark.TFrame")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # LEFT PANEL
        left = ttk.Frame(main, style="Dark.TFrame")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        ttk.Label(left, text="DATASET CONTROLS", style="Dark.TLabel", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        ttk.Button(left, text="Upload dataset (CSV/XLSX)", style="Dark.TButton", command=self.upload_dataset).pack(
            fill=tk.X, pady=(12, 6)
        )

        self.dataset_label = tk.StringVar(value="No dataset loaded.")
        ttk.Label(left, textvariable=self.dataset_label, style="Dark.TLabel", wraplength=330).pack(anchor="w")

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        ttk.Label(left, text="Target account", style="Dark.TLabel").pack(anchor="w")
        self.target_var = tk.StringVar(value="(all)")
        self.target_combo = ttk.Combobox(left, textvariable=self.target_var, values=["(all)"], state="readonly", width=38)
        self.target_combo.pack(anchor="w", pady=(4, 10))

        ttk.Label(left, text="Time window", style="Dark.TLabel").pack(anchor="w")
        self.window_var = tk.StringVar(value="All available")

        for t in ["All available", "Last 7 days", "Last 30 days", "Custom range"]:
            ttk.Radiobutton(left, text=t, value=t, variable=self.window_var).pack(anchor="w")

        self.start_entry = ttk.Entry(left, width=18)
        self.end_entry = ttk.Entry(left, width=18)

        ttk.Label(left, text="Start (YYYY-MM-DD)", style="Dark.TLabel").pack(anchor="w", pady=(6, 0))
        self.start_entry.pack(anchor="w")

        ttk.Label(left, text="End (YYYY-MM-DD)", style="Dark.TLabel").pack(anchor="w", pady=(6, 0))
        self.end_entry.pack(anchor="w")

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        ttk.Label(left, text="Run analysis:", style="Dark.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        ttk.Button(left, text="Overview Analysis", style="Dark.TButton", command=self.show_overview).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Temporal Analysis", style="Dark.TButton", command=self.show_temporal).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Sentiment Analysis", style="Dark.TButton", command=self.show_sentiment).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Leakage Analysis", style="Dark.TButton", command=self.show_leakage).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Raw Posts", style="Dark.TButton", command=self.show_raw).pack(fill=tk.X, pady=3)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(left, textvariable=self.status_var, style="Dark.TLabel", wraplength=330).pack(anchor="w")

        # RIGHT PANEL
        self.right = ttk.Frame(main, style="Dark.TFrame")
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.title_label = ttk.Label(
            self.right,
            text="Upload a dataset to begin.",
            style="Dark.TLabel",
            font=("Segoe UI", 14, "bold"),
        )
        self.title_label.pack(anchor="w", pady=(0, 10))

        self.content_frame = ttk.Frame(self.right, style="Dark.TFrame")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

    # -----------------------------
    # Dataset loading
    # -----------------------------
    def upload_dataset(self):
        path = filedialog.askopenfilename(
            title="Select dataset file",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")],
        )
        if not path:
            return

        ensure_directories()

        p = Path(path)
        if p.suffix.lower() not in SUPPORTED_EXTS:
            messagebox.showerror("Unsupported file", "Supported formats: CSV, XLSX, XLS")
            return

        dest = DATA_DIR / p.name
        try:
            if p.resolve() != dest.resolve():
                shutil.copy2(p, dest)
        except Exception:
            pass

        try:
            if p.suffix.lower() == ".csv":
                df_raw = pd.read_csv(p)
            else:
                df_raw = pd.read_excel(p)
        except Exception as e:
            messagebox.showerror("Load error", f"Failed to load dataset:\n{e}")
            return

        self.df_all = normalize_dataset(df_raw)

        if self.df_all.empty:
            messagebox.showerror("Empty dataset", "Dataset loaded but no usable rows were found.")
            return

        users = sorted(set(self.df_all["username"].astype(str)))
        self.target_combo["values"] = ["(all)"] + users
        self.target_var.set("(all)")

        self.dataset_label.set(f"Loaded: {p.name}\nRows: {len(self.df_all):,}\nTargets: {len(users)}")
        self.status_var.set("Dataset loaded successfully.")

        try:
            self.df_all.to_csv(OUTPUT_DIR / "normalized_dataset.csv", index=False)
        except Exception:
            pass

        self.clear_content()
        self.title_label.config(text="Dataset loaded. Select an analysis.")

    def filtered_df(self) -> pd.DataFrame:
        if self.df_all is None:
            return pd.DataFrame()

        df = self.df_all.copy()

        # target filter
        t = self.target_var.get()
        if t and t != "(all)":
            df = df[df["username"] == t]

        # time-window filter
        mode = self.window_var.get()

        if mode in ("Last 7 days", "Last 30 days"):
            max_date = df["timestamp_utc"].max()
            if pd.notna(max_date):
                days = 7 if mode == "Last 7 days" else 30
                cutoff = max_date - pd.Timedelta(days=days)
                df = df[df["timestamp_utc"] >= cutoff]

        elif mode == "Custom range":
            s = self.start_entry.get().strip()
            e = self.end_entry.get().strip()
            if s and e:
                try:
                    sd = datetime.strptime(s, "%Y-%m-%d").date()
                    ed = datetime.strptime(e, "%Y-%m-%d").date()
                    df = df[df["timestamp_utc"].dt.date.between(sd, ed)]
                except Exception:
                    pass

        return df.sort_values("timestamp_utc", ascending=False)

    # -----------------------------
    # UI helpers
    # -----------------------------
    def clear_content(self):
        for child in self.content_frame.winfo_children():
            child.destroy()

    def make_tree(self, columns, headings, widths):
        frame = ttk.Frame(self.content_frame, style="Dark.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(frame, columns=columns, show="headings", style="Dark.Treeview")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)

        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        for c, h, w in zip(columns, headings, widths):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")

        return tree

    def open_url(self, url: str):
        if url.startswith("http://") or url.startswith("https://"):
            webbrowser.open(url)

    def embed_plot(self, fig):
        """Embed a matplotlib Figure into the content frame (Tk canvas)."""
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.X, pady=(0, 10))
        return canvas

    # =========================================================
    # Analyses
    # =========================================================
    def show_overview(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Overview Analysis")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        total_posts = len(df)
        loc_posts = int((df["location"].astype(str).str.strip() != "").sum())
        tag_posts = int(df["tagged_users"].apply(lambda x: len(x) if isinstance(x, list) else 0).gt(0).sum())

        info = ttk.Label(
            self.content_frame,
            text=f"Total posts: {total_posts} | Posts with location: {loc_posts} | Posts with tagged users: {tag_posts}",
            style="Dark.TLabel",
            font=("Consolas", 11),
        )
        info.pack(anchor="w", pady=(0, 10))

        tree = self.make_tree(
            columns=["timestamp_utc", "username", "location", "tagged_users", "caption", "display_url"],
            headings=["Timestamp (UTC)", "User", "Location", "Tagged users", "Caption", "displayUrl"],
            widths=[180, 140, 200, 240, 600, 350],
        )

        for _, r in df.head(400).iterrows():
            tagged = ", ".join(r["tagged_users"]) if isinstance(r["tagged_users"], list) else ""
            tree.insert(
                "",
                tk.END,
                values=[
                    str(r["timestamp_utc"]),
                    r["username"],
                    r["location"],
                    tagged,
                    str(r["caption"])[:140],
                    r["display_url"],
                ],
            )

        def on_double_click(_event):
            item = tree.selection()
            if not item:
                return
            vals = tree.item(item[0], "values")
            self.open_url(str(vals[-1]))

        tree.bind("<Double-1>", on_double_click)

    def show_temporal(self):
        """
        Temporal Analysis:
          - Posts per day (chart + table) with clear x-axis ticks
          - Posts per hour (bar chart + table)
          - Posts per weekday (bar chart + table)
        """
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Temporal Analysis")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        df = df.copy()
        df = df[pd.notna(df["timestamp_utc"])]

        if df.empty:
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return

        df["date"] = df["timestamp_utc"].dt.date
        df["hour"] = df["timestamp_utc"].dt.hour
        df["weekday"] = df["timestamp_utc"].dt.day_name()

        per_day = df.groupby("date")["post_id"].count().reset_index(name="posts").sort_values("date")
        per_hour = df.groupby("hour")["post_id"].count().reset_index(name="posts").sort_values("hour")

        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        per_weekday = (
            df.groupby("weekday")["post_id"].count().reindex(weekday_order, fill_value=0).reset_index(name="posts")
        )

        # ---------- Posts per Day (IMPROVED X-AXIS) ----------
        ttk.Label(
            self.content_frame,
            text="Posts per Day",
            style="Dark.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        per_day_plot = per_day.copy()
        per_day_plot["date"] = pd.to_datetime(per_day_plot["date"])

        fig1, ax1 = plt.subplots(figsize=(9, 3.8))
        ax1.plot(per_day_plot["date"], per_day_plot["posts"], marker="o")
        ax1.set_title("Posting Frequency Over Time")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Posts")

        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        for label in ax1.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")

        fig1.tight_layout()
        self.embed_plot(fig1)

        tree1 = self.make_tree(["date", "posts"], ["Date", "Posts"], [180, 120])
        for _, r in per_day.iterrows():
            tree1.insert("", tk.END, values=[r["date"], r["posts"]])

        # ---------- Posts per Hour ----------
        ttk.Label(
            self.content_frame,
            text="Posts per Hour",
            style="Dark.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12, 5))

        fig2, ax2 = plt.subplots(figsize=(9, 3.2))
        ax2.bar(per_hour["hour"].astype(int), per_hour["posts"].astype(int))
        ax2.set_title("Diurnal Posting Pattern")
        ax2.set_xlabel("Hour of Day (0–23)")
        ax2.set_ylabel("Posts")
        ax2.set_xticks(list(range(0, 24, 1)))
        for label in ax2.get_xticklabels():
            label.set_rotation(0)
        fig2.tight_layout()
        self.embed_plot(fig2)

        tree2 = self.make_tree(["hour", "posts"], ["Hour", "Posts"], [120, 120])
        for _, r in per_hour.iterrows():
            tree2.insert("", tk.END, values=[int(r["hour"]), int(r["posts"])])

        # ---------- Posts per Weekday ----------
        ttk.Label(
            self.content_frame,
            text="Posts per Weekday",
            style="Dark.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12, 5))

        fig3, ax3 = plt.subplots(figsize=(9, 3.2))
        ax3.bar(per_weekday["weekday"], per_weekday["posts"])
        ax3.set_title("Weekly Posting Pattern")
        ax3.set_xlabel("Weekday")
        ax3.set_ylabel("Posts")
        for label in ax3.get_xticklabels():
            label.set_rotation(25)
            label.set_ha("right")
        fig3.tight_layout()
        self.embed_plot(fig3)

        tree3 = self.make_tree(["weekday", "posts"], ["Weekday", "Posts"], [180, 120])
        for _, r in per_weekday.iterrows():
            tree3.insert("", tk.END, values=[r["weekday"], int(r["posts"])])

    def show_sentiment(self):
        """
        Sentiment Analysis:
          - compute post-level sentiment from captions
          - show daily average sentiment (chart with readable x-axis)
          - show summary stats + table of recent scored posts
        """
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Sentiment Analysis")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        df = df.copy()
        df = df[pd.notna(df["timestamp_utc"])]

        if df.empty:
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return

        df["caption"] = df["caption"].fillna("").astype(str)
        df["sentiment"] = df["caption"].apply(self.sentiment.score)
        df["date"] = df["timestamp_utc"].dt.date

        daily = df.groupby("date")["sentiment"].mean().reset_index(name="avg_sentiment").sort_values("date")
        daily["date"] = pd.to_datetime(daily["date"])

        # Summary stats
        mean_s = float(df["sentiment"].mean())
        med_s = float(df["sentiment"].median())
        min_s = float(df["sentiment"].min())
        max_s = float(df["sentiment"].max())

        ttk.Label(
            self.content_frame,
            text=f"Engine: {self.sentiment.mode.upper()} | Mean: {mean_s:.3f} | Median: {med_s:.3f} | Min: {min_s:.3f} | Max: {max_s:.3f}",
            style="Dark.TLabel",
            font=("Consolas", 11),
        ).pack(anchor="w", pady=(0, 8))

        # Chart (IMPROVED X-AXIS)
        ttk.Label(
            self.content_frame,
            text="Average Sentiment per Day",
            style="Dark.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        fig, ax = plt.subplots(figsize=(9, 3.8))
        ax.plot(daily["date"], daily["avg_sentiment"], marker="o")
        ax.axhline(0, linestyle="--")
        ax.set_title("Daily Sentiment Trend (Average)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Average Sentiment (≈ -1 to +1)")

        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")

        fig.tight_layout()
        self.embed_plot(fig)

        # Table of scored posts
        ttk.Label(
            self.content_frame,
            text="Recent Posts (Scored)",
            style="Dark.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(8, 5))

        tree = self.make_tree(
            columns=["timestamp_utc", "username", "sentiment", "caption", "display_url"],
            headings=["Timestamp (UTC)", "User", "Sentiment", "Caption (truncated)", "displayUrl"],
            widths=[180, 140, 100, 750, 350],
        )

        for _, r in df.head(500).iterrows():
            tree.insert(
                "",
                tk.END,
                values=[
                    str(r["timestamp_utc"]),
                    r["username"],
                    f"{float(r['sentiment']):.3f}",
                    str(r["caption"])[:180],
                    r["display_url"],
                ],
            )

        def on_double_click(_event):
            item = tree.selection()
            if not item:
                return
            vals = tree.item(item[0], "values")
            self.open_url(str(vals[-1]))

        tree.bind("<Double-1>", on_double_click)

    def show_raw(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Raw Posts")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        tree = self.make_tree(
            columns=["post_id", "timestamp_utc", "username", "caption", "image_ref", "display_url"],
            headings=["Post ID", "Timestamp", "User", "Caption", "Image ref", "displayUrl"],
            widths=[160, 180, 140, 650, 200, 350],
        )

        for _, r in df.head(800).iterrows():
            tree.insert(
                "",
                tk.END,
                values=[
                    r["post_id"],
                    str(r["timestamp_utc"]),
                    r["username"],
                    str(r["caption"])[:160],
                    r["image_ref"],
                    r["display_url"],
                ],
            )

        def on_double_click(_event):
            item = tree.selection()
            if not item:
                return
            vals = tree.item(item[0], "values")
            self.open_url(str(vals[-1]))

        tree.bind("<Double-1>", on_double_click)

    def show_leakage(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Image Leakage & EXIF Analysis")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        container = ttk.Frame(self.content_frame, style="Dark.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(container, style="Dark.TFrame")
        right = ttk.Frame(container, style="Dark.TFrame")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=(10, 0))

        tree_frame = ttk.Frame(left, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(
            tree_frame,
            columns=["post_id", "username", "local_image", "exif", "gps", "lat", "lon", "display_url"],
            show="headings",
            style="Dark.Treeview",
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        cols = [
            ("post_id", "Post ID", 140),
            ("username", "User", 120),
            ("local_image", "Local image", 240),
            ("exif", "EXIF", 60),
            ("gps", "GPS", 60),
            ("lat", "Lat", 90),
            ("lon", "Lon", 90),
            ("display_url", "displayUrl", 320),
        ]
        for c, h, w in cols:
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")

        preview_label = tk.Label(right, bg="#101620", fg="#E5F0FF", text="No image selected", width=55, height=20)
        preview_label.pack(fill=tk.BOTH, expand=False)

        details = tk.Text(right, height=12, bg="#050910", fg="#E5F0FF", insertbackground="#E5F0FF", wrap="word")
        details.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        for _, r in df.iterrows():
            img_ref = str(r.get("image_ref", "")).strip()
            local_img_path = ""

            if img_ref:
                p = Path(img_ref)
                if p.exists():
                    local_img_path = str(p)
                else:
                    candidates = [
                        DATA_DIR / img_ref,
                        DATA_DIR / "images" / img_ref,
                        DATA_DIR / r["username"] / img_ref,
                        DATA_DIR / r["username"] / "images" / img_ref,
                    ]
                    for c in candidates:
                        if c.exists():
                            local_img_path = str(c.resolve())
                            break

            exif_present = False
            gps_present = False
            lat = lon = None

            if local_img_path:
                exif_present, gps_present, lat, lon = extract_exif(Path(local_img_path))

                try:
                    user_dir = OUTPUT_IMAGES_DIR / str(r["username"])
                    user_dir.mkdir(parents=True, exist_ok=True)
                    dst = user_dir / Path(local_img_path).name
                    if not dst.exists():
                        shutil.copy2(local_img_path, dst)
                except Exception:
                    pass

            tree.insert(
                "",
                tk.END,
                values=[
                    r["post_id"],
                    r["username"],
                    local_img_path,
                    "Yes" if exif_present else "No",
                    "Yes" if gps_present else "No",
                    "" if lat is None else f"{lat:.6f}",
                    "" if lon is None else f"{lon:.6f}",
                    r["display_url"],
                ],
            )

        def on_select(_event):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            local_img = str(vals[2]).strip()
            url = str(vals[-1]).strip()

            if local_img and Path(local_img).exists():
                try:
                    img = Image.open(local_img)
                    img.thumbnail((520, 520))
                    self.preview_img = ImageTk.PhotoImage(img)
                    preview_label.config(image=self.preview_img, text="")
                except Exception:
                    preview_label.config(image="", text="Preview failed")
            else:
                preview_label.config(image="", text="No local image.\nProof via displayUrl only.")

            details.delete("1.0", tk.END)
            details.insert(
                "1.0",
                f"Post ID: {vals[0]}\n"
                f"User: {vals[1]}\n"
                f"Local image: {local_img or '(none)'}\n"
                f"EXIF: {vals[3]}\n"
                f"GPS: {vals[4]}\n"
                f"Lat: {vals[5]}\n"
                f"Lon: {vals[6]}\n"
                f"displayUrl: {url}\n",
            )

        def on_double_click(_event):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            self.open_url(str(vals[-1]))

        tree.bind("<<TreeviewSelect>>", on_select)
        tree.bind("<Double-1>", on_double_click)


def main():
    ensure_directories()
    app = OSINTCleanGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
