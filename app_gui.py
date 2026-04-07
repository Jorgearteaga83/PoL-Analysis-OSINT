import logging
import threading
import queue
import shutil
import webbrowser
import requests
import tempfile
import base64
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# Import from our new modules
from data_processing import normalize_dataset, extract_exif
from utils import best_col
from osint_analysis import SentimentEngine, infer_location_data, categorize_location, generate_sna_graph

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"
SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}

def ensure_directories():
    for d in (DATA_DIR, OUTPUT_DIR, OUTPUT_IMAGES_DIR):
        d.mkdir(exist_ok=True, parents=True)

class OSINTCleanGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OSINT Dataset Analysis (Offline Mode)")
        self.geometry("1500x900")
        self.configure(bg="#050910")

        self.df_all: Optional[pd.DataFrame] = None
        self.preview_img = None
        self.sentiment = SentimentEngine()
        self.task_queue = queue.Queue()

        self.setup_style()
        self.build_ui()
        self.poll_queue()

    def setup_style(self):
        style = ttk.Style()
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure(".", background="#050910", foreground="#E5F0FF", fieldbackground="#050910")
        style.configure("Dark.TFrame", background="#050910")
        style.configure("Dark.TLabel", background="#050910", foreground="#E5F0FF")
        style.configure("Dark.TButton", background="#1A2738", foreground="#E5F0FF", padding=6)
        style.map("Dark.TButton", background=[("active", "#22344A")])
        style.configure("Dark.Treeview", background="#101620", foreground="#E5F0FF", fieldbackground="#101620", rowheight=24)
        style.map("Dark.Treeview", background=[("selected", "#28406A")])

    def build_ui(self):
        main = ttk.Frame(self, style="Dark.TFrame")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # LEFT PANEL
        left = ttk.Frame(main, style="Dark.TFrame", width=320)
        left.pack_propagate(False)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        ttk.Button(left, text="Upload dataset", style="Dark.TButton", command=self.upload_dataset).pack(fill=tk.X, pady=(12, 6))
        self.dataset_label = tk.StringVar(value="No dataset loaded.")
        ttk.Label(left, textvariable=self.dataset_label, style="Dark.TLabel", wraplength=280).pack(anchor="w", fill=tk.X)

        self.target_var = tk.StringVar(value="(all)")
        self.target_combo = ttk.Combobox(left, textvariable=self.target_var, values=["(all)"], state="readonly", width=38)
        self.target_combo.pack(anchor="w", pady=(4, 10))

        self.window_var = tk.StringVar(value="All available")
        for t in ["All available", "Last 7 days", "Last 30 days", "Custom range"]:
            ttk.Radiobutton(left, text=t, value=t, variable=self.window_var).pack(anchor="w")

        self.start_entry = ttk.Entry(left, width=18)
        self.end_entry = ttk.Entry(left, width=18)
        self.start_entry.pack(anchor="w", pady=(5,0))
        self.end_entry.pack(anchor="w", pady=(5,0))

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
        ttk.Button(left, text="Overview", style="Dark.TButton", command=self.show_overview).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Temporal Analysis", style="Dark.TButton", command=self.show_temporal).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Sentiment Analysis", style="Dark.TButton", command=self.show_sentiment).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Leakage", style="Dark.TButton", command=self.show_leakage).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Raw Posts", style="Dark.TButton", command=self.show_raw).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Generate Intelligence Report", style="Dark.TButton", command=self.generate_report).pack(fill=tk.X, pady=(10, 3))
        
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(left, textvariable=self.status_var, style="Dark.TLabel").pack(anchor="w")

        # RIGHT PANEL
        self.right = ttk.Frame(main, style="Dark.TFrame")
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.title_label = ttk.Label(self.right, text="Upload a dataset to begin.", style="Dark.TLabel", font=("Segoe UI", 14, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 10))
        self.content_frame = ttk.Frame(self.right, style="Dark.TFrame")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

    def poll_queue(self):
        try:
            while True:
                msg_type, data = self.task_queue.get_nowait()
                if msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "error":
                    messagebox.showerror("Error", data)
                elif msg_type == "dataset_loaded":
                    self.handle_dataset_loaded(data)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.poll_queue)

    def run_in_background(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def upload_dataset(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")])
        if not path: return
        ensure_directories()
        self.status_var.set("Loading dataset in background...")
        self.run_in_background(self._async_load_dataset, path)

    def _async_load_dataset(self, path: str):
        try:
            p = Path(path)
            if p.suffix.lower() == ".csv": df_raw = pd.read_csv(p, low_memory=False)
            else: df_raw = pd.read_excel(p)
            df_norm = normalize_dataset(df_raw)
            self.task_queue.put(("dataset_loaded", (df_norm, p.name)))
        except Exception as e:
            logger.error(f"Dataset load error: {e}")
            self.task_queue.put(("error", f"Failed to load dataset:\n{e}"))

    def handle_dataset_loaded(self, data):
        df_norm, filename = data
        if df_norm.empty:
            messagebox.showerror("Empty dataset", "Dataset loaded but no usable rows found.")
            return
        self.df_all = df_norm
        users = sorted(set(self.df_all["username"].astype(str)))
        self.target_combo["values"] = ["(all)"] + users
        self.target_var.set("(all)")
        
        wrapped_filename = "\n".join(textwrap.wrap(filename, width=35, break_long_words=True))
        self.dataset_label.set(f"Loaded: \n{wrapped_filename}\nRows: {len(self.df_all):,}")
        
        self.status_var.set("Dataset loaded successfully.")
        self.title_label.config(text="Dataset loaded. Select an analysis.")
        self.clear_content()

    def filtered_df(self) -> pd.DataFrame:
        if self.df_all is None: return pd.DataFrame()
        df = self.df_all.copy()
        t = self.target_var.get()
        if t and t != "(all)": df = df[df["username"] == t]
        
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
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.X, pady=(0, 10))
        return canvas

    # =========================================================
    # RESTORED ANALYSES
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
        tag_posts = int(df["associated_entities"].apply(lambda x: len(x) if isinstance(x, list) else 0).gt(0).sum())

        info = ttk.Label(
            self.content_frame,
            text=f"Total posts: {total_posts} | Posts with location: {loc_posts} | Posts with tagged users: {tag_posts}",
            style="Dark.TLabel",
            font=("Consolas", 11),
        )
        info.pack(anchor="w", pady=(0, 10))

        tree = self.make_tree(
            columns=["timestamp_utc", "username", "location", "associated_entities", "caption", "display_url"],
            headings=["Timestamp (UTC)", "User", "Location", "Associated Entities", "Caption", "displayUrl"],
            widths=[180, 140, 200, 240, 600, 350],
        )

        for _, r in df.head(400).iterrows():
            tagged = ", ".join(r["associated_entities"]) if isinstance(r["associated_entities"], list) else ""
            tree.insert("", tk.END, values=[str(r["timestamp_utc"]), r["username"], r["location"], tagged, str(r["caption"])[:140], r["display_url"]])

        def on_double_click(_event):
            item = tree.selection()
            if item: self.open_url(str(tree.item(item[0], "values")[-1]))

        tree.bind("<Double-1>", on_double_click)

    def show_temporal(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Temporal Analysis")

        if df.empty or df[pd.notna(df["timestamp_utc"])].empty:
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return

        df = df[pd.notna(df["timestamp_utc"])].copy()
        df["date"] = df["timestamp_utc"].dt.date
        df["hour"] = df["timestamp_utc"].dt.hour
        df["weekday"] = df["timestamp_utc"].dt.day_name()

        per_day = df.groupby("date")["post_id"].count().reset_index(name="posts").sort_values("date")
        per_hour = df.groupby("hour")["post_id"].count().reset_index(name="posts").sort_values("hour")
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        per_weekday = df.groupby("weekday")["post_id"].count().reindex(weekday_order, fill_value=0).reset_index(name="posts")

        style = ttk.Style()
        style.configure("Dark.TNotebook", background="#050910", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#1A2738", foreground="#E5F0FF", padding=[8, 4])
        style.map("Dark.TNotebook.Tab", background=[("selected", "#28406A"), ("active", "#22344A")])
        notebook = ttk.Notebook(self.content_frame, style="Dark.TNotebook")
        notebook.pack(fill='both', expand=True)

        def embed_plot_in_tab(fig, parent):
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            return canvas
            
        day_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)
        notebook.add(day_frame, text='Posts per Day')
        per_day_plot = per_day.copy()
        per_day_plot["date"] = pd.to_datetime(per_day_plot["date"])
        fig1, ax1 = plt.subplots(figsize=(9, 4))
        ax1.plot(per_day_plot["date"], per_day_plot["posts"], marker="o")
        ax1.set_title("Posting Frequency Over Time")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Posts")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig1.autofmt_xdate()
        fig1.tight_layout()
        embed_plot_in_tab(fig1, day_frame)
        plt.close(fig1)

        hour_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)
        notebook.add(hour_frame, text='Posts per Hour')
        fig2, ax2 = plt.subplots(figsize=(9, 4))
        ax2.bar(per_hour["hour"].astype(int), per_hour["posts"].astype(int))
        ax2.set_title("Diurnal Posting Pattern")
        ax2.set_xlabel("Hour of Day (0–23)")
        ax2.set_ylabel("Posts")
        ax2.set_xticks(list(range(0, 24, 1)))
        fig2.tight_layout()
        embed_plot_in_tab(fig2, hour_frame)
        plt.close(fig2)

        weekday_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)
        notebook.add(weekday_frame, text='Posts per Weekday')
        fig3, ax3 = plt.subplots(figsize=(9, 4))
        ax3.bar(per_weekday["weekday"], per_weekday["posts"])
        ax3.set_title("Weekly Posting Pattern")
        ax3.set_xlabel("Weekday")
        ax3.set_ylabel("Posts")
        fig3.autofmt_xdate()
        fig3.tight_layout()
        embed_plot_in_tab(fig3, weekday_frame)
        plt.close(fig3)

        heatmap_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)
        notebook.add(heatmap_frame, text='Pattern of Life Heatmap')
        heatmap_data = pd.crosstab(df['weekday'], df['hour'])
        heatmap_data = heatmap_data.reindex(columns=range(24), fill_value=0)
        heatmap_data = heatmap_data.reindex(index=weekday_order, fill_value=0)
        fig4, ax4 = plt.subplots(figsize=(9, 4))
        im = ax4.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
        ax4.set_xticks(range(len(heatmap_data.columns)))
        ax4.set_xticklabels(heatmap_data.columns)
        ax4.set_yticks(range(len(heatmap_data.index)))
        ax4.set_yticklabels(heatmap_data.index)
        cbar = ax4.figure.colorbar(im, ax=ax4)
        cbar.ax.set_ylabel("Activity Density", rotation=-90, va="bottom")
        ax4.set_title("Weekly Activity Heatmap (Day vs. Hour)")
        fig4.tight_layout()
        embed_plot_in_tab(fig4, heatmap_frame)
        plt.close(fig4)

    def show_sentiment(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Sentiment Analysis")

        if df.empty or df[pd.notna(df["timestamp_utc"])].empty:
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return

        df = df[pd.notna(df["timestamp_utc"])].copy()
        df["caption"] = df["caption"].fillna("").astype(str)
        df["sentiment"] = df["caption"].apply(self.sentiment.score)
        df["date"] = df["timestamp_utc"].dt.date

        daily = df.groupby("date")["sentiment"].mean().reset_index(name="avg_sentiment").sort_values("date")
        daily["date"] = pd.to_datetime(daily["date"])

        mean_s, med_s, min_s, max_s = df["sentiment"].mean(), df["sentiment"].median(), df["sentiment"].min(), df["sentiment"].max()

        ttk.Label(self.content_frame, text=f"Engine: {self.sentiment.mode.upper()} | Mean: {mean_s:.3f} | Median: {med_s:.3f} | Min: {min_s:.3f} | Max: {max_s:.3f}", style="Dark.TLabel", font=("Consolas", 11)).pack(anchor="w", pady=(0, 8))

        fig, ax = plt.subplots(figsize=(9, 3.8))
        ax.plot(daily["date"], daily["avg_sentiment"], marker="o")
        ax.axhline(0, linestyle="--")
        ax.set_title("Daily Sentiment Trend (Average)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Average Sentiment (≈ -1 to +1)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        for label in ax.get_xticklabels(): label.set_rotation(45); label.set_ha("right")
        fig.tight_layout()
        self.embed_plot(fig)
        plt.close(fig)

        tree = self.make_tree(["timestamp_utc", "username", "sentiment", "caption", "display_url"], ["Timestamp (UTC)", "User", "Sentiment", "Caption (truncated)", "displayUrl"], [180, 140, 100, 750, 350])
        for _, r in df.head(500).iterrows():
            tree.insert("", tk.END, values=[str(r["timestamp_utc"]), r["username"], f"{float(r['sentiment']):.3f}", str(r["caption"])[:180], r["display_url"]])

        tree.bind("<Double-1>", lambda e: self.open_url(str(tree.item(tree.selection()[0], "values")[-1])) if tree.selection() else None)

    def show_raw(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Raw Posts")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        tree = self.make_tree(["post_id", "timestamp_utc", "username", "caption", "image_ref", "display_url"], ["Post ID", "Timestamp", "User", "Caption", "Image ref", "displayUrl"], [160, 180, 140, 650, 200, 350])
        for _, r in df.head(800).iterrows():
            tree.insert("", tk.END, values=[r["post_id"], str(r["timestamp_utc"]), r["username"], str(r["caption"])[:160], r["image_ref"], r["display_url"]])

        tree.bind("<Double-1>", lambda e: self.open_url(str(tree.item(tree.selection()[0], "values")[-1])) if tree.selection() else None)

    def show_leakage(self):
        df = self.filtered_df()
        self.clear_content()
        self.title_label.config(text="Image Leakage & EXIF Analysis")

        if df.empty:
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return

        container = ttk.Frame(self.content_frame, style="Dark.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        container.columnconfigure(0, weight=1, uniform="panels")
        container.columnconfigure(1, weight=1, uniform="panels")
        container.rowconfigure(0, weight=1)

        left = ttk.Frame(container, style="Dark.TFrame")
        right = ttk.Frame(container, style="Dark.TFrame")
        left.grid(row=0, column=0, sticky="nsew")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

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

        right.rowconfigure(0, weight=1, uniform="group1")  # Give image and details equal weight
        right.rowconfigure(1, weight=1, uniform="group1")
        right.columnconfigure(0, weight=1)

        preview_label = tk.Label(right, bg="#101620", fg="#E5F0FF", text="No image selected")
        preview_label.grid(row=0, column=0, sticky="nsew")

        details = tk.Text(right, bg="#050910", fg="#E5F0FF", insertbackground="#E5F0FF", wrap="word")
        details.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

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
            elif url:
                preview_label.config(image="", text="Downloading image...")
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                            tmp_file.write(response.content)
                            tmp_path = Path(tmp_file.name)
                        
                        exif_present, gps_present, lat, lon = extract_exif(tmp_path)
                        tree.set(sel[0], "exif", "Yes" if exif_present else "No")
                        tree.set(sel[0], "gps", "Yes" if gps_present else "No")
                        tree.set(sel[0], "lat", "" if lat is None else f"{lat:.6f}")
                        tree.set(sel[0], "lon", "" if lon is None else f"{lon:.6f}")

                        img = Image.open(tmp_path)
                        img.thumbnail((520, 520))
                        self.preview_img = ImageTk.PhotoImage(img)
                        preview_label.config(image=self.preview_img, text="")
                        local_img = str(tmp_path)
                    elif response.status_code == 403:
                        preview_label.config(image="", text="Image URL expired or forbidden.")
                    else:
                        preview_label.config(image="", text=f"Failed to download.\nStatus: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    preview_label.config(image="", text=f"Download error:\n{e}")
                except Exception:
                    preview_label.config(image="", text="Image processing failed.")
            else:
                preview_label.config(image="", text="No local image or URL.")

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

    def generate_report(self):
        df_filtered = self.filtered_df()
        if df_filtered.empty:
            messagebox.showinfo("Report Generation", "No data matches the current filter. Cannot generate report.")
            return

        target_user = self.target_var.get()
        if not target_user or target_user == "(all)":
            messagebox.showinfo("Report Generation", "Please select a single target account to generate a report.")
            return

        self.status_var.set("Generating report asynchronously...")
        self.run_in_background(self._async_generate_report, df_filtered, target_user)

    def _async_generate_report(self, df_filtered: pd.DataFrame, target_user: str):
        try:
            now = datetime.now()
            report_path = OUTPUT_DIR / f"intelligence_report_{target_user}_{now.strftime('%Y%m%d_%H%M%S')}.html"

            df = df_filtered.copy()
            if 'sentiment' not in df.columns:
                df['sentiment'] = df['caption'].fillna("").astype(str).apply(self.sentiment.score)
            
            df['hour'] = df['timestamp_utc'].dt.hour
            df['weekday'] = df['timestamp_utc'].dt.day_name()
            df_sorted = df.sort_values('timestamp_utc').reset_index(drop=True)

            df_sorted['inferred_city'] = None
            df_sorted['inferred_country'] = None
            df_sorted['inferred_timezone'] = None
            
            if best_col(df_sorted, ['lat', 'latitude']) and best_col(df_sorted, ['lon', 'longitude']):
                c_lat = best_col(df_sorted, ['lat', 'latitude'])
                c_lon = best_col(df_sorted, ['lon', 'longitude'])
                loc_data = df_sorted.apply(lambda row: infer_location_data(row[c_lat], row[c_lon], row['location']), axis=1)
                loc_df = pd.DataFrame(loc_data.tolist(), index=df_sorted.index, columns=['inferred_city', 'inferred_country', 'inferred_timezone'])
                df_sorted.update(loc_df)

            df_sorted = categorize_location(df_sorted)

            total_posts = len(df_sorted)
            first_post_date = df_sorted['timestamp_utc'].min().strftime('%Y-%m-%d')
            last_post_date = df_sorted['timestamp_utc'].max().strftime('%Y-%m-%d')

            location_counts = df_sorted[df_sorted['location'] != '']['location'].value_counts().head(10)
            loc_analysis_html = "<h4>Most Frequent Locations</h4>"
            if not location_counts.empty: loc_analysis_html += location_counts.to_frame().to_html()
            else: loc_analysis_html += "<p>No significant location data found.</p>"
            
            cat_data = df_sorted[df_sorted['location_category'] != 'Uncategorized']
            if not cat_data.empty:
                def get_unique_locations(s):
                    locs = s.dropna().astype(str)
                    return ", ".join(sorted(set(locs[locs.str.strip() != ''])))
                cat_summary = cat_data.groupby('location_category').agg(count=('location_category', 'count'), associated_locations=('location', get_unique_locations)).reset_index().sort_values(by='count', ascending=False)
                loc_analysis_html += "<h4>Heuristic Location Categories</h4>" + cat_summary.to_html(index=False)

            sna_path = generate_sna_graph(df_sorted, target_user, OUTPUT_DIR)
            sna_html = "<h3>Social Network Analysis</h3>"
            if sna_path:
                try:
                    with open(sna_path, "rb") as f: encoded_img = base64.b64encode(f.read()).decode('utf-8')
                    sna_html += f'<img src="data:image/png;base64,{encoded_img}" alt="SNA Graph" style="max-width:100%;"><p>The graph shows entities frequently mentioned or tagged by the target.</p>'
                except Exception as e: sna_html += f"<p>Could not embed SNA graph: {e}</p>"
            else: sna_html += "<p>No social network data to display.</p>"

            anomalies = []
            df_sorted['prev_timezone'] = df_sorted['inferred_timezone'].shift(1)
            travel_anomalies = df_sorted[(df_sorted['inferred_timezone'].notna()) & (df_sorted['prev_timezone'].notna()) & (df_sorted['inferred_timezone'] != df_sorted['prev_timezone'])]
            for _, row in travel_anomalies.iterrows(): anomalies.append(f"<b>Travel Anomaly:</b> Detected travel to {row['inferred_timezone']} on {row['timestamp_utc']:%Y-%m-%d}.")
            
            df_sorted['rolling_sentiment'] = df_sorted['sentiment'].rolling(window=5, min_periods=1).mean()
            mood_drops = df_sorted[(df_sorted['sentiment'] < -0.5) & (df_sorted['rolling_sentiment'].shift(1) > 0)]
            for _, row in mood_drops.iterrows(): anomalies.append(f"<b>Mood Drop:</b> Significant negative sentiment post on {row['timestamp_utc']:%Y-%m-%d}.")
            
            disruptions = df_sorted[df_sorted['inferred_timezone'].notna()]
            if not disruptions.empty:
                disruptions['local_time'] = disruptions.apply(lambda row: row['timestamp_utc'].tz_convert(row['inferred_timezone']), axis=1)
                sleep_posts = disruptions[disruptions['local_time'].dt.hour.between(0, 6)]
                for _, row in sleep_posts.iterrows(): anomalies.append(f"<b>Routine Disruption:</b> Post detected during typical sleep hours at {row['local_time']:%H:%M} local time on {row['local_time']:%Y-%m-%d}.")

            anomaly_html = "<h3>Anomaly Detection</h3>"
            if anomalies: anomaly_html += "<ul>" + "".join([f"<li>{a}</li>" for a in anomalies]) + "</ul>"
            else: anomaly_html += "<p>No significant anomalies detected in this dataset.</p>"

            grievances = df_sorted[df_sorted['sentiment'] < -0.5].sort_values('sentiment').head(5)
            grievance_html = "<h3>User Grievances (Top Negative Posts)</h3>"
            if not grievances.empty:
                grievance_html += "<ul>"
                for _, row in grievances.iterrows(): grievance_html += f"<li>({row['sentiment']:.2f}) {row['caption'][:150]}...</li>"
                grievance_html += "</ul>"
            else: grievance_html += "<p>No significant negative posts found.</p>"

            # Mosaic Effect Conclusion
            mosaic_conclusion = """
            <h3>The Mosaic Effect: Synthesized Intelligence</h3>
            <p>This section synthesizes the individual analyses into a cohesive narrative.</p>
            """
            if anomalies:
                mosaic_conclusion += "<p>The target's pattern of life shows significant disruptions. The detected anomalies, when viewed together, suggest periods of stress, travel, or unusual activity. For instance, a mood drop coinciding with a travel anomaly could indicate stressful travel. These events should be cross-referenced with other intelligence sources.</p>"
                
                if not travel_anomalies.empty:
                    mosaic_conclusion += "<h4>Travel Anomalies</h4><ul>"
                    for _, row in travel_anomalies.iterrows():
                        loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                        mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Time:</b> {row['timestamp_utc']} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                    mosaic_conclusion += "</ul>"
                    
                if 'sleep_posts' in locals() and not sleep_posts.empty:
                    mosaic_conclusion += "<h4>Routine Disruptions (Sleep)</h4><ul>"
                    for _, row in sleep_posts.iterrows():
                        loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                        mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Local Time:</b> {row['local_time']:%Y-%m-%d %H:%M} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                    mosaic_conclusion += "</ul>"
                    
                if not mood_drops.empty:
                    mosaic_conclusion += "<h4>Mood Drops</h4><ul>"
                    for _, row in mood_drops.iterrows():
                        loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                        mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Time:</b> {row['timestamp_utc']} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                    mosaic_conclusion += "</ul>"
            else:
                mosaic_conclusion += "<p>The target exhibits a stable and predictable pattern of life. Their activity is consistent, with few deviations from their established routine. This predictability can be used to forecast future behavior.</p>"
            
            if not grievances.empty:
                mosaic_conclusion += "<p>Recurring negative sentiment (grievances) often centers on specific themes. Further analysis of these themes could reveal the target's personal or professional stressors.</p>"
                mosaic_conclusion += "<h4>Grievances</h4><ul>"
                for _, row in grievances.iterrows():
                    loc = row['location'] if pd.notna(row['location']) and str(row['location']).strip() else 'Unknown'
                    mosaic_conclusion += f"<li><b>Location:</b> {loc} | <b>Date/Time:</b> {row['timestamp_utc']} | <b>Caption:</b> {str(row['caption'])[:100]}...</li>"
                mosaic_conclusion += "</ul>"
            
            if sna_path:
                mosaic_conclusion += "<p>The social network analysis identifies key individuals in the target's digital life. These individuals represent potential sources of secondary information leakage and are persons of interest for further investigation.</p>"

            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Intelligence Report: {target_user}</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 960px; margin: 20px auto; }}
                    h1, h2, h3, h4 {{ color: #1A2738; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                    .section {{ background-color: #f9f9f9; padding: 15px; border: 1px solid #eee; border-radius: 5px; margin-bottom: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #eef; }}
                </style>
            </head>
            <body>
                <h1 style="text-align: center;">OSINT Intelligence Report</h1>
                <p style="text-align: center;"><strong>Target:</strong> {target_user} | <strong>Report Date:</strong> {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <div class="section"><h2>Executive Summary</h2><p>This report covers <strong>{total_posts} posts</strong> from <strong>{first_post_date}</strong> to <strong>{last_post_date}</strong>.</p></div>
                <div class="section"><h2>Spatial Analysis (The 'Where')</h2>{loc_analysis_html}</div>
                <div class="section"><h2>Social Network & Leakage (The 'Who')</h2>{sna_html}</div>
                <div class="section"><h2>Behavioural & Anomaly Analysis (The 'Why' and 'When')</h2>{anomaly_html}{grievance_html}</div>
                <div class="section"><h2>Conclusion</h2>{mosaic_conclusion}</div>
            </body>
            </html>
            """

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            webbrowser.open(report_path.resolve().as_uri())
            self.task_queue.put(("status", f"Report saved to {report_path.name}"))
            
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            self.task_queue.put(("error", f"Failed to generate report:\n{e}"))