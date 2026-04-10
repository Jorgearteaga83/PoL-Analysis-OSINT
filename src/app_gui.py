import logging  # Import necessary module or component
import threading  # Import necessary module or component
import queue  # Import necessary module or component
import shutil  # Import necessary module or component
import webbrowser  # Import necessary module or component
import requests  # Import necessary module or component
import tempfile  # Import necessary module or component
import base64  # Import necessary module or component
import textwrap  # Import necessary module or component
from pathlib import Path  # Import necessary module or component
from datetime import datetime  # Import necessary module or component
from typing import Optional  # Import necessary module or component

import tkinter as tk  # Import necessary module or component
from tkinter import ttk, messagebox, filedialog  # Import necessary module or component
import pandas as pd  # Import necessary module or component
from PIL import Image, ImageTk  # Import necessary module or component
import matplotlib.pyplot as plt  # Import necessary module or component
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Import necessary module or component
import matplotlib.dates as mdates  # Import necessary module or component

# Import from our new modules
from data_processing import normalize_dataset, extract_exif  # Import necessary module or component
from utils import best_col  # Import necessary module or component
# Import necessary module or component
# Import necessary module or component
from osint_analysis import SentimentEngine, infer_location_data, categorize_location, generate_sna_graph

logger = logging.getLogger(__name__)  # Assign value to logger

DATA_DIR = Path("data")  # Assign value to DATA_DIR
OUTPUT_DIR = Path("output")  # Assign value to OUTPUT_DIR
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"  # Assign value to OUTPUT_IMAGES_DIR
SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}  # Assign value to SUPPORTED_EXTS

def ensure_directories():  # Define function ensure_directories
    for d in (DATA_DIR, OUTPUT_DIR, OUTPUT_IMAGES_DIR):  # Iterate in a loop
        d.mkdir(exist_ok=True, parents=True)  # Close bracket/parenthesis

class OSINTCleanGUI(tk.Tk):  # Define class OSINTCleanGUI
    def __init__(self):  # Define function __init__
        super().__init__()  # Call function super
        self.title("OSINT Dataset Analysis (Offline Mode)")  # Call instance method
        self.geometry("1500x900")  # Call instance method
        self.configure(bg="#050910")

        self.df_all: Optional[pd.DataFrame] = None  # Execute statement or expression
        self.preview_img = None  # Assign value to self.preview_img
        self.sentiment = SentimentEngine()  # Assign value to self.sentiment
        self.task_queue = queue.Queue()  # Assign value to self.task_queue

        self.setup_style()  # Call instance method
        self.build_ui()  # Call instance method
        self.poll_queue()  # Call instance method

    def setup_style(self):  # Define function setup_style
        style = ttk.Style()  # Assign value to style
        try: style.theme_use("clam")  # Start of try block for exception handling
        except tk.TclError: pass  # Handle specific exceptions
        style.configure(".", background="#050910", foreground="#E5F0FF", fieldbackground="#050910")
        style.configure("Dark.TFrame", background="#050910")
        style.configure("Dark.TLabel", background="#050910", foreground="#E5F0FF")
        style.configure("Dark.TButton", background="#1A2738", foreground="#E5F0FF", padding=6)
        style.map("Dark.TButton", background=[("active", "#22344A")])
        style.configure("Dark.Treeview", background="#101620", foreground="#E5F0FF", fieldbackground="#101620", rowheight=24)
        style.map("Dark.Treeview", background=[("selected", "#28406A")])

    def build_ui(self):  # Define function build_ui
        main = ttk.Frame(self, style="Dark.TFrame")  # Assign value to main
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)  # Close bracket/parenthesis

        # LEFT PANEL
        left = ttk.Frame(main, style="Dark.TFrame", width=320)  # Assign value to left
        left.pack_propagate(False)  # Close bracket/parenthesis
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))  # Close bracket/parenthesis

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Upload dataset", style="Dark.TButton", command=self.upload_dataset).pack(fill=tk.X, pady=(12, 6))
        self.dataset_label = tk.StringVar(value="No dataset loaded.")  # Assign value to self.dataset_label
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(left, textvariable=self.dataset_label, style="Dark.TLabel", wraplength=280).pack(anchor="w", fill=tk.X)

        self.target_var = tk.StringVar(value="(all)")  # Assign value to self.target_var
        # Assign value to self.target_combo
        # Assign value to self.target_combo
        self.target_combo = ttk.Combobox(left, textvariable=self.target_var, values=["(all)"], state="readonly", width=38)
        self.target_combo.pack(anchor="w", pady=(4, 10))  # Close bracket/parenthesis

        self.window_var = tk.StringVar(value="All available")  # Assign value to self.window_var
        for t in ["All available", "Last 7 days", "Last 30 days", "Custom range"]:  # Iterate in a loop
            ttk.Radiobutton(left, text=t, value=t, variable=self.window_var).pack(anchor="w")  # Close bracket/parenthesis

        self.start_entry = ttk.Entry(left, width=18)  # Assign value to self.start_entry
        self.end_entry = ttk.Entry(left, width=18)  # Assign value to self.end_entry
        self.start_entry.pack(anchor="w", pady=(5,0))  # Close bracket/parenthesis
        self.end_entry.pack(anchor="w", pady=(5,0))  # Close bracket/parenthesis

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)  # Close bracket/parenthesis
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Overview", style="Dark.TButton", command=self.show_overview).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Temporal Analysis", style="Dark.TButton", command=self.show_temporal).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Sentiment Analysis", style="Dark.TButton", command=self.show_sentiment).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Leakage", style="Dark.TButton", command=self.show_leakage).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Raw Posts", style="Dark.TButton", command=self.show_raw).pack(fill=tk.X, pady=3)
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(left, text="Generate Intelligence Report", style="Dark.TButton", command=self.generate_report).pack(fill=tk.X, pady=(10, 3))
        
        self.status_var = tk.StringVar(value="Ready.")  # Assign value to self.status_var
        ttk.Label(left, textvariable=self.status_var, style="Dark.TLabel").pack(anchor="w")  # Close bracket/parenthesis

        # RIGHT PANEL
        self.right = ttk.Frame(main, style="Dark.TFrame")  # Assign value to self.right
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
        # Assign value to self.title_label
        # Assign value to self.title_label
        self.title_label = ttk.Label(self.right, text="Upload a dataset to begin.", style="Dark.TLabel", font=("Segoe UI", 14, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 10))  # Close bracket/parenthesis
        self.content_frame = ttk.Frame(self.right, style="Dark.TFrame")  # Assign value to self.content_frame
        self.content_frame.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

    def poll_queue(self):  # Define function poll_queue
        try:  # Start of try block for exception handling
            while True:  # Loop while condition is met
                msg_type, data = self.task_queue.get_nowait()  # Close bracket/parenthesis
                if msg_type == "status":  # Check conditional statement
                    self.status_var.set(data)  # Close bracket/parenthesis
                elif msg_type == "error":  # Check alternative condition
                    messagebox.showerror("Error", data)  # Close bracket/parenthesis
                elif msg_type == "dataset_loaded":  # Check alternative condition
                    self.handle_dataset_loaded(data)  # Call instance method
        except queue.Empty:  # Handle specific exceptions
            pass  # No-op placeholder
        finally:  # Execute cleanup code regardless of exceptions
            self.after(100, self.poll_queue)  # Call instance method

    def run_in_background(self, target, *args):  # Define function run_in_background
        threading.Thread(target=target, args=args, daemon=True).start()  # Close bracket/parenthesis

    def upload_dataset(self):  # Define function upload_dataset
        # Assign value to path
        # Assign value to path
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")])
        if not path: return  # Check conditional statement
        ensure_directories()  # Call function ensure_directories
        self.status_var.set("Loading dataset in background...")  # Close bracket/parenthesis
        self.run_in_background(self._async_load_dataset, path)  # Call instance method

    def _async_load_dataset(self, path: str):  # Define function _async_load_dataset
        try:  # Start of try block for exception handling
            p = Path(path)  # Assign value to p
            if p.suffix.lower() == ".csv": df_raw = pd.read_csv(p, low_memory=False)  # Check conditional statement
            else: df_raw = pd.read_excel(p)  # Execute if preceding conditions are false
            df_norm = normalize_dataset(df_raw)  # Assign value to df_norm
            self.task_queue.put(("dataset_loaded", (df_norm, p.name)))  # Close bracket/parenthesis
        except Exception as e:  # Handle specific exceptions
            logger.error(f"Dataset load error: {e}")  # Close bracket/parenthesis
            self.task_queue.put(("error", f"Failed to load dataset:\n{e}"))  # Close bracket/parenthesis

    def handle_dataset_loaded(self, data):  # Define function handle_dataset_loaded
        df_norm, filename = data  # Execute statement or expression
        if df_norm.empty:  # Check conditional statement
            messagebox.showerror("Empty dataset", "Dataset loaded but no usable rows found.")  # Close bracket/parenthesis
            return  # Return value from function
        self.df_all = df_norm  # Assign value to self.df_all
        users = sorted(set(self.df_all["username"].astype(str)))  # Assign value to users
        self.target_combo["values"] = ["(all)"] + users  # Assign value to self.target_combo["values"]
        self.target_var.set("(all)")  # Close bracket/parenthesis
        
        wrapped_filename = "\n".join(textwrap.wrap(filename, width=35, break_long_words=True))  # Assign value to wrapped_filename
        self.dataset_label.set(f"Loaded: \n{wrapped_filename}\nRows: {len(self.df_all):,}")  # Close bracket/parenthesis
        
        self.status_var.set("Dataset loaded successfully.")  # Close bracket/parenthesis
        self.title_label.config(text="Dataset loaded. Select an analysis.")  # Close bracket/parenthesis
        self.clear_content()  # Call instance method

    def filtered_df(self) -> pd.DataFrame:  # Define function filtered_df
        if self.df_all is None: return pd.DataFrame()  # Check conditional statement
        df = self.df_all.copy()  # Assign value to df
        t = self.target_var.get()  # Assign value to t
        if t and t != "(all)": df = df[df["username"] == t]  # Check conditional statement
        
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
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)  # Assign value to canvas
        canvas.draw()  # Close bracket/parenthesis
        canvas.get_tk_widget().pack(fill=tk.X, pady=(0, 10))  # Close bracket/parenthesis
        return canvas  # Return value from function

    # =========================================================
    # RESTORED ANALYSES
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
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            tree.insert("", tk.END, values=[str(r["timestamp_utc"]), r["username"], r["location"], tagged, str(r["caption"])[:140], r["display_url"]])

        def on_double_click(_event):  # Define function on_double_click
            item = tree.selection()  # Assign value to item
            if item: self.open_url(str(tree.item(item[0], "values")[-1]))  # Check conditional statement

        tree.bind("<Double-1>", on_double_click)  # Close bracket/parenthesis

    def show_temporal(self):  # Define function show_temporal
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Temporal Analysis")  # Close bracket/parenthesis

        if df.empty or df[pd.notna(df["timestamp_utc"])].empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        df = df[pd.notna(df["timestamp_utc"])].copy()  # Assign value to df
        df["date"] = df["timestamp_utc"].dt.date  # Assign value to df["date"]
        df["hour"] = df["timestamp_utc"].dt.hour  # Assign value to df["hour"]
        df["weekday"] = df["timestamp_utc"].dt.day_name()  # Assign value to df["weekday"]

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

        style = ttk.Style()  # Assign value to style
        style.configure("Dark.TNotebook", background="#050910", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#1A2738", foreground="#E5F0FF", padding=[8, 4])
        style.map("Dark.TNotebook.Tab", background=[("selected", "#28406A"), ("active", "#22344A")])
        notebook = ttk.Notebook(self.content_frame, style="Dark.TNotebook")  # Assign value to notebook
        notebook.pack(fill='both', expand=True)  # Close bracket/parenthesis

        def embed_plot_in_tab(fig, parent):  # Define function embed_plot_in_tab
            canvas = FigureCanvasTkAgg(fig, master=parent)  # Assign value to canvas
            canvas.draw()  # Close bracket/parenthesis
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
            return canvas  # Return value from function
            
        day_frame = ttk.Frame(notebook, style="Dark.TFrame", padding=10)  # Assign value to day_frame
        notebook.add(day_frame, text='Posts per Day')  # Close bracket/parenthesis
        per_day_plot = per_day.copy()  # Assign value to per_day_plot
        per_day_plot["date"] = pd.to_datetime(per_day_plot["date"])  # Assign value to per_day_plot["date"]
        fig1, ax1 = plt.subplots(figsize=(9, 4))  # Close bracket/parenthesis
        ax1.plot(per_day_plot["date"], per_day_plot["posts"], marker="o")  # Close bracket/parenthesis
        ax1.set_title("Posting Frequency Over Time")  # Close bracket/parenthesis
        ax1.set_xlabel("Date")  # Close bracket/parenthesis
        ax1.set_ylabel("Posts")  # Close bracket/parenthesis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))  # Close bracket/parenthesis
        fig1.autofmt_xdate()  # Close bracket/parenthesis
        fig1.tight_layout()  # Close bracket/parenthesis
        embed_plot_in_tab(fig1, day_frame)  # Call function embed_plot_in_tab
        plt.close(fig1)  # Close bracket/parenthesis

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
        fig4.tight_layout()  # Close bracket/parenthesis
        embed_plot_in_tab(fig4, heatmap_frame)  # Call function embed_plot_in_tab
        plt.close(fig4)  # Close bracket/parenthesis

    def show_sentiment(self):  # Define function show_sentiment
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Sentiment Analysis")  # Close bracket/parenthesis

        if df.empty or df[pd.notna(df["timestamp_utc"])].empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No valid timestamps available.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        df = df[pd.notna(df["timestamp_utc"])].copy()  # Assign value to df
        df["caption"] = df["caption"].fillna("").astype(str)  # Assign value to df["caption"]
        df["sentiment"] = df["caption"].apply(self.sentiment.score)  # Assign value to df["sentiment"]
        df["date"] = df["timestamp_utc"].dt.date  # Assign value to df["date"]

        # Assign value to daily
        # Assign value to daily
        daily = df.groupby("date")["sentiment"].mean().reset_index(name="avg_sentiment").sort_values("date")
        daily["date"] = pd.to_datetime(daily["date"])  # Assign value to daily["date"]

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        mean_s, med_s, min_s, max_s = df["sentiment"].mean(), df["sentiment"].median(), df["sentiment"].min(), df["sentiment"].max()

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(self.content_frame, text=f"Engine: {self.sentiment.mode.upper()} | Mean: {mean_s:.3f} | Median: {med_s:.3f} | Min: {min_s:.3f} | Max: {max_s:.3f}", style="Dark.TLabel", font=("Consolas", 11)).pack(anchor="w", pady=(0, 8))

        fig, ax = plt.subplots(figsize=(9, 3.8))  # Close bracket/parenthesis
        ax.plot(daily["date"], daily["avg_sentiment"], marker="o")  # Close bracket/parenthesis
        ax.axhline(0, linestyle="--")  # Close bracket/parenthesis
        ax.set_title("Daily Sentiment Trend (Average)")  # Close bracket/parenthesis
        ax.set_xlabel("Date")  # Close bracket/parenthesis
        ax.set_ylabel("Average Sentiment (≈ -1 to +1)")  # Close bracket/parenthesis
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))  # Close bracket/parenthesis
        for label in ax.get_xticklabels(): label.set_rotation(45); label.set_ha("right")  # Iterate in a loop
        fig.tight_layout()  # Close bracket/parenthesis
        self.embed_plot(fig)  # Call instance method
        plt.close(fig)  # Close bracket/parenthesis

        # Assign value to tree
        # Assign value to tree
        tree = self.make_tree(["timestamp_utc", "username", "sentiment", "caption", "display_url"], ["Timestamp (UTC)", "User", "Sentiment", "Caption (truncated)", "displayUrl"], [180, 140, 100, 750, 350])
        for _, r in df.head(500).iterrows():  # Iterate in a loop
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            tree.insert("", tk.END, values=[str(r["timestamp_utc"]), r["username"], f"{float(r['sentiment']):.3f}", str(r["caption"])[:180], r["display_url"]])

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        tree.bind("<Double-1>", lambda e: self.open_url(str(tree.item(tree.selection()[0], "values")[-1])) if tree.selection() else None)

    def show_raw(self):  # Define function show_raw
        df = self.filtered_df()  # Assign value to df
        self.clear_content()  # Call instance method
        self.title_label.config(text="Raw Posts")  # Close bracket/parenthesis

        if df.empty:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            ttk.Label(self.content_frame, text="No posts match this filter.", style="Dark.TLabel").pack(anchor="w")
            return  # Return value from function

        # Assign value to tree
        # Assign value to tree
        tree = self.make_tree(["post_id", "timestamp_utc", "username", "caption", "image_ref", "display_url"], ["Post ID", "Timestamp", "User", "Caption", "Image ref", "displayUrl"], [160, 180, 140, 650, 200, 350])
        for _, r in df.head(800).iterrows():  # Iterate in a loop
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            tree.insert("", tk.END, values=[r["post_id"], str(r["timestamp_utc"]), r["username"], str(r["caption"])[:160], r["image_ref"], r["display_url"]])

        # Close bracket/parenthesis
        # Close bracket/parenthesis
        tree.bind("<Double-1>", lambda e: self.open_url(str(tree.item(tree.selection()[0], "values")[-1])) if tree.selection() else None)

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

        container.columnconfigure(0, weight=1, uniform="panels")  # Close bracket/parenthesis
        container.columnconfigure(1, weight=1, uniform="panels")  # Close bracket/parenthesis
        container.rowconfigure(0, weight=1)  # Close bracket/parenthesis

        left = ttk.Frame(container, style="Dark.TFrame")  # Assign value to left
        right = ttk.Frame(container, style="Dark.TFrame")  # Assign value to right
        left.grid(row=0, column=0, sticky="nsew")  # Close bracket/parenthesis
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))  # Close bracket/parenthesis

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

        right.rowconfigure(0, weight=1, uniform="group1")  # Give image and details equal weight
        right.rowconfigure(1, weight=1, uniform="group1")  # Close bracket/parenthesis
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

        self.status_var.set("Generating report asynchronously...")  # Close bracket/parenthesis
        self.run_in_background(self._async_generate_report, df_filtered, target_user)  # Call instance method

    def _async_generate_report(self, df_filtered: pd.DataFrame, target_user: str):  # Define function _async_generate_report
        try:  # Start of try block for exception handling
            now = datetime.now()  # Assign value to now
            # Assign value to report_path
            # Assign value to report_path
            report_path = OUTPUT_DIR / f"intelligence_report_{target_user}_{now.strftime('%Y%m%d_%H%M%S')}.html"

            df = df_filtered.copy()  # Assign value to df
            if 'sentiment' not in df.columns:  # Check conditional statement
                df['sentiment'] = df['caption'].fillna("").astype(str).apply(self.sentiment.score)  # Assign value to df['sentiment']
            
            df['hour'] = df['timestamp_utc'].dt.hour  # Assign value to df['hour']
            df['weekday'] = df['timestamp_utc'].dt.day_name()  # Assign value to df['weekday']
            df_sorted = df.sort_values('timestamp_utc').reset_index(drop=True)  # Assign value to df_sorted

            df_sorted['inferred_city'] = None  # Assign value to df_sorted['inferred_city']
            df_sorted['inferred_country'] = None  # Assign value to df_sorted['inferred_country']
            df_sorted['inferred_timezone'] = None  # Assign value to df_sorted['inferred_timezone']
            
            # Check conditional statement
            # Check conditional statement
            if best_col(df_sorted, ['lat', 'latitude']) and best_col(df_sorted, ['lon', 'longitude']):
                c_lat = best_col(df_sorted, ['lat', 'latitude'])  # Assign value to c_lat
                c_lon = best_col(df_sorted, ['lon', 'longitude'])  # Assign value to c_lon
                # Assign value to loc_data
                # Assign value to loc_data
                loc_data = df_sorted.apply(lambda row: infer_location_data(row[c_lat], row[c_lon], row['location']), axis=1)
                # Assign value to loc_df
                # Assign value to loc_df
                loc_df = pd.DataFrame(loc_data.tolist(), index=df_sorted.index, columns=['inferred_city', 'inferred_country', 'inferred_timezone'])
                df_sorted.update(loc_df)  # Close bracket/parenthesis

            df_sorted = categorize_location(df_sorted)  # Assign value to df_sorted

            total_posts = len(df_sorted)  # Assign value to total_posts
            first_post_date = df_sorted['timestamp_utc'].min().strftime('%Y-%m-%d')  # Assign value to first_post_date
            last_post_date = df_sorted['timestamp_utc'].max().strftime('%Y-%m-%d')  # Assign value to last_post_date

            # Assign value to location_counts
            # Assign value to location_counts
            location_counts = df_sorted[df_sorted['location'] != '']['location'].value_counts().head(10)
            loc_analysis_html = "<h4>Most Frequent Locations</h4>"  # Assign value to loc_analysis_html
            if not location_counts.empty: loc_analysis_html += location_counts.to_frame().to_html()  # Check conditional statement
            else: loc_analysis_html += "<p>No significant location data found.</p>"  # Execute if preceding conditions are false
            
            cat_data = df_sorted[df_sorted['location_category'] != 'Uncategorized']  # Assign value to cat_data
            if not cat_data.empty:  # Check conditional statement
                def get_unique_locations(s):  # Define function get_unique_locations
                    locs = s.dropna().astype(str)  # Assign value to locs
                    return ", ".join(sorted(set(locs[locs.str.strip() != ''])))  # Return value from function
                # Assign value to cat_summary
                # Assign value to cat_summary
                cat_summary = cat_data.groupby('location_category').agg(count=('location_category', 'count'), associated_locations=('location', get_unique_locations)).reset_index().sort_values(by='count', ascending=False)
                # Assign value to loc_analysis_html
                # Assign value to loc_analysis_html
                loc_analysis_html += "<h4>Heuristic Location Categories</h4>" + cat_summary.to_html(index=False)

            sna_path = generate_sna_graph(df_sorted, target_user, OUTPUT_DIR)  # Assign value to sna_path
            sna_html = "<h3>Social Network Analysis</h3>"  # Assign value to sna_html
            if sna_path:  # Check conditional statement
                try:  # Start of try block for exception handling
                    # Use context manager
                    # Use context manager
                    with open(sna_path, "rb") as f: encoded_img = base64.b64encode(f.read()).decode('utf-8')
                    # Assign value to sna_html
                    # Assign value to sna_html
                    sna_html += f'<img src="data:image/png;base64,{encoded_img}" alt="SNA Graph" style="max-width:100%;"><p>The graph shows entities frequently mentioned or tagged by the target.</p>'
                except Exception as e: sna_html += f"<p>Could not embed SNA graph: {e}</p>"  # Handle specific exceptions
            else: sna_html += "<p>No social network data to display.</p>"  # Execute if preceding conditions are false

            anomalies = []  # Assign value to anomalies
            df_sorted['prev_timezone'] = df_sorted['inferred_timezone'].shift(1)  # Assign value to df_sorted['prev_timezone']
            # Assign value to travel_anomalies
            # Assign value to travel_anomalies
            travel_anomalies = df_sorted[(df_sorted['inferred_timezone'].notna()) & (df_sorted['prev_timezone'].notna()) & (df_sorted['inferred_timezone'] != df_sorted['prev_timezone'])]
            # Iterate in a loop
            # Iterate in a loop
            for _, row in travel_anomalies.iterrows(): anomalies.append(f"<b>Travel Anomaly:</b> Detected travel to {row['inferred_timezone']} on {row['timestamp_utc']:%Y-%m-%d}.")
            
            # Assign value to df_sorted['rolling_sentiment']
            # Assign value to df_sorted['rolling_sentiment']
            df_sorted['rolling_sentiment'] = df_sorted['sentiment'].rolling(window=5, min_periods=1).mean()
            # Assign value to mood_drops
            # Assign value to mood_drops
            mood_drops = df_sorted[(df_sorted['sentiment'] < -0.5) & (df_sorted['rolling_sentiment'].shift(1) > 0)]
            # Iterate in a loop
            # Iterate in a loop
            for _, row in mood_drops.iterrows(): anomalies.append(f"<b>Mood Drop:</b> Significant negative sentiment post on {row['timestamp_utc']:%Y-%m-%d}.")
            
            disruptions = df_sorted[df_sorted['inferred_timezone'].notna()]  # Assign value to disruptions
            if not disruptions.empty:  # Check conditional statement
                # Assign value to disruptions['local_time']
                # Assign value to disruptions['local_time']
                disruptions['local_time'] = disruptions.apply(lambda row: row['timestamp_utc'].tz_convert(row['inferred_timezone']), axis=1)
                sleep_posts = disruptions[disruptions['local_time'].dt.hour.between(0, 6)]  # Assign value to sleep_posts
                # Iterate in a loop
                # Iterate in a loop
                for _, row in sleep_posts.iterrows(): anomalies.append(f"<b>Routine Disruption:</b> Post detected during typical sleep hours at {row['local_time']:%H:%M} local time on {row['local_time']:%Y-%m-%d}.")

            anomaly_html = "<h3>Anomaly Detection</h3>"  # Assign value to anomaly_html
            # Check conditional statement
            # Check conditional statement
            if anomalies: anomaly_html += "<ul>" + "".join([f"<li>{a}</li>" for a in anomalies]) + "</ul>"
            else: anomaly_html += "<p>No significant anomalies detected in this dataset.</p>"  # Execute if preceding conditions are false

            grievances = df_sorted[df_sorted['sentiment'] < -0.5].sort_values('sentiment').head(5)  # Assign value to grievances
            grievance_html = "<h3>User Grievances (Top Negative Posts)</h3>"  # Assign value to grievance_html
            if not grievances.empty:  # Check conditional statement
                grievance_html += "<ul>"  # Assign value to grievance_html
                # Iterate in a loop
                # Iterate in a loop
                for _, row in grievances.iterrows(): grievance_html += f"<li>({row['sentiment']:.2f}) {row['caption'][:150]}...</li>"
                grievance_html += "</ul>"  # Assign value to grievance_html
            else: grievance_html += "<p>No significant negative posts found.</p>"  # Execute if preceding conditions are false

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

            with open(report_path, "w", encoding="utf-8") as f:  # Use context manager
                f.write(html_content)  # Close bracket/parenthesis
            webbrowser.open(report_path.resolve().as_uri())  # Close bracket/parenthesis
            self.task_queue.put(("status", f"Report saved to {report_path.name}"))  # Close bracket/parenthesis
            
        except Exception as e:  # Handle specific exceptions
            logger.error(f"Report generation error: {e}")  # Close bracket/parenthesis
            self.task_queue.put(("error", f"Failed to generate report:\n{e}"))  # Close bracket/parenthesis
