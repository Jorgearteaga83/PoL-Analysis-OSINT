from __future__ import annotations  # Import necessary module or component

import os  # Import necessary module or component
import tkinter as tk  # Import necessary module or component
from tkinter import ttk, messagebox, filedialog, simpledialog  # Import necessary module or component
from datetime import datetime  # Import necessary module or component

import pandas as pd  # Import necessary module or component
import matplotlib  # Import necessary module or component
from matplotlib.figure import Figure  # Import necessary module or component
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Import necessary module or component
from PIL import Image, ImageTk  # Import necessary module or component

from app.config import ensure_directories  # Import necessary module or component
from app.database import initialise_database, save_posts  # Import necessary module or component
from app.targets import load_targets, TargetAccount  # Import necessary module or component
from app.timefilters import last_n_days, full_window, filter_posts, TimeWindow  # Import necessary module or component
from app.scraper import get_posts_for_profile  # uses IG_USER / IG_PASS env vars for live mode
from app.timestamp_analyser import posts_to_dataframe, posting_summary  # Import necessary module or component
from app.sentiment_analyser import sentiment_dataframe, daily_sentiment, sentiment_summary  # Import necessary module or component
from app.leakage_analyser import analyse_image_leaks, leakage_summary  # Import necessary module or component
from app.exif_analyser import image_path_for  # Import necessary module or component

matplotlib.use("TkAgg")  # Close bracket/parenthesis


def posts_per_day_df(df_posts: pd.DataFrame) -> pd.DataFrame:  # Define function posts_per_day_df
    if df_posts.empty:  # Check conditional statement
        return pd.DataFrame(columns=["date", "posts"])  # Return value from function
    out = df_posts.groupby("date")["post_id"].count().reset_index(name="posts")  # Assign value to out
    return out.sort_values("date")  # Return value from function


def posts_per_hour_df(df_posts: pd.DataFrame) -> pd.DataFrame:  # Define function posts_per_hour_df
    if df_posts.empty:  # Check conditional statement
        return pd.DataFrame(columns=["hour", "posts"])  # Return value from function
    out = df_posts.groupby("hour")["post_id"].count().reset_index(name="posts")  # Assign value to out
    return out.sort_values("hour")  # Return value from function


def posts_per_weekday_df(df_posts: pd.DataFrame) -> pd.DataFrame:  # Define function posts_per_weekday_df
    if df_posts.empty:  # Check conditional statement
        return pd.DataFrame(columns=["weekday", "posts"])  # Return value from function
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]  # Assign value to order
    tmp = df_posts.groupby("weekday")["post_id"].count().reset_index(name="posts")  # Assign value to tmp
    tmp["weekday"] = pd.Categorical(tmp["weekday"], categories=order, ordered=True)  # Assign value to tmp["weekday"]
    tmp = tmp.sort_values("weekday")  # Assign value to tmp
    tmp["weekday"] = tmp["weekday"].astype(str)  # Assign value to tmp["weekday"]
    return tmp  # Return value from function


class OSINTApp(tk.Tk):  # Define class OSINTApp
    def __init__(self, targets: list[TargetAccount]):  # Define function __init__
        super().__init__()  # Call function super
        self.targets = targets  # Assign value to self.targets
        self.target_by_label: dict[str, TargetAccount] = {}  # Close bracket/parenthesis

        self.df_posts: pd.DataFrame | None = None  # Execute statement or expression
        self.df_sent: pd.DataFrame | None = None  # Execute statement or expression
        self.df_daily_sent: pd.DataFrame | None = None  # Execute statement or expression

        self.leaks = []  # Assign value to self.leaks
        self.leak_stats = {}  # Assign value to self.leak_stats
        self.stats = {}  # Assign value to self.stats
        self.time_label = ""  # Assign value to self.time_label

        self.chart_canvases: list[FigureCanvasTkAgg] = []  # Close bracket/parenthesis
        self.leak_row_map = {}  # Assign value to self.leak_row_map
        self._leak_img_tk: ImageTk.PhotoImage | None = None  # Execute statement or expression

        self.title("OSINT Social Media Analysis")  # Call instance method
        self.geometry("1300x820")  # Call instance method
        self.configure(bg="#050910")
        self.iconify()  # Call instance method
        self.after(100, self.deiconify)  # Call instance method

        self.configure_style()  # Call instance method
        self.build_layout()  # Call instance method

    def configure_style(self):  # Define function configure_style
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
            rowheight=22,  # Assign value to rowheight
        )  # Close bracket/parenthesis
        style.map("Dark.Treeview", background=[("selected", "#28406A")], foreground=[("selected", "#FFFFFF")])

        style.configure("Dark.TNotebook", background="#050910", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#101620", foreground="#E5F0FF", padding=(10, 4))
        style.map("Dark.TNotebook.Tab", background=[("selected", "#1A2738")], foreground=[("selected", "#FFFFFF")])

        # Radiobutton styling (clam sometimes needs explicit style)
        style.configure("Dark.TRadiobutton", background="#050910", foreground="#E5F0FF")

    def build_layout(self):  # Define function build_layout
        main_frame = ttk.Frame(self, style="Dark.TFrame")  # Assign value to main_frame
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Close bracket/parenthesis

        control_frame = ttk.Frame(main_frame, style="Dark.TFrame")  # Assign value to control_frame
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))  # Close bracket/parenthesis

        ttk.Label(  # Execute statement or expression
            control_frame,  # Execute statement or expression
            text="OSINT SOCIAL MEDIA TOOL",  # Assign value to text
            style="Dark.TLabel",  # Assign value to style
            font=("Segoe UI", 14, "bold"),  # Assign value to font
        ).pack(anchor="w", pady=(0, 10))  # Close bracket/parenthesis

        ttk.Label(control_frame, text="Target account", style="Dark.TLabel").pack(anchor="w")  # Close bracket/parenthesis

        labels = []  # Assign value to labels
        for t in self.targets:  # Iterate in a loop
            label = f"{t.label} ({t.username}, {t.group})"  # Assign value to label
            labels.append(label)  # Close bracket/parenthesis
            self.target_by_label[label] = t  # Assign value to self.target_by_label[label]

        self.target_var = tk.StringVar()  # Assign value to self.target_var
        self.target_combo = ttk.Combobox(  # Assign value to self.target_combo
            control_frame,  # Execute statement or expression
            textvariable=self.target_var,  # Assign value to textvariable
            values=labels,  # Assign value to values
            state="readonly",  # Assign value to state
            width=40,  # Assign value to width
        )  # Close bracket/parenthesis
        if labels:  # Check conditional statement
            self.target_combo.current(0)  # Close bracket/parenthesis
        self.target_combo.pack(anchor="w", pady=(0, 10))  # Close bracket/parenthesis

        ttk.Label(control_frame, text="Time window", style="Dark.TLabel").pack(anchor="w")  # Close bracket/parenthesis
        self.window_var = tk.StringVar(value="Last 30 days")  # Assign value to self.window_var
        for text in ["All available", "Last 7 days", "Last 30 days", "Custom range"]:  # Iterate in a loop
            ttk.Radiobutton(  # Execute statement or expression
                control_frame,  # Execute statement or expression
                text=text,  # Assign value to text
                value=text,  # Assign value to value
                variable=self.window_var,  # Assign value to variable
                style="Dark.TRadiobutton",  # Assign value to style
            ).pack(anchor="w")  # Close bracket/parenthesis

        self.custom_frame = ttk.Frame(control_frame, style="Dark.TFrame")  # Assign value to self.custom_frame
        self.custom_frame.pack(anchor="w", pady=(8, 8))  # Close bracket/parenthesis
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(self.custom_frame, text="Start (YYYY-MM-DD)", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Label(self.custom_frame, text="End (YYYY-MM-DD)", style="Dark.TLabel").grid(row=1, column=0, sticky="w")
        self.start_entry = ttk.Entry(self.custom_frame, width=18)  # Assign value to self.start_entry
        self.end_entry = ttk.Entry(self.custom_frame, width=18)  # Assign value to self.end_entry
        self.start_entry.grid(row=0, column=1, padx=(6, 0), pady=2)  # Close bracket/parenthesis
        self.end_entry.grid(row=1, column=1, padx=(6, 0), pady=2)  # Close bracket/parenthesis

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)  # Close bracket/parenthesis

        # Data source section
        ttk.Label(control_frame, text="Data source", style="Dark.TLabel").pack(anchor="w")  # Close bracket/parenthesis
        self.source_var = tk.StringVar(value="Live (Instagram)")  # Assign value to self.source_var
        ttk.Radiobutton(  # Execute statement or expression
            control_frame,  # Execute statement or expression
            text="Live (Instagram)",  # Assign value to text
            value="Live (Instagram)",  # Assign value to value
            variable=self.source_var,  # Assign value to variable
            style="Dark.TRadiobutton",  # Assign value to style
        ).pack(anchor="w")  # Close bracket/parenthesis
        ttk.Radiobutton(  # Execute statement or expression
            control_frame,  # Execute statement or expression
            text="File (CSV/XLSX/TXT)",  # Assign value to text
            value="File (CSV/XLSX/TXT)",  # Assign value to value
            variable=self.source_var,  # Assign value to variable
            style="Dark.TRadiobutton",  # Assign value to style
        ).pack(anchor="w")  # Close bracket/parenthesis

        self.file_path_var = tk.StringVar(value="")  # Assign value to self.file_path_var
        file_row = ttk.Frame(control_frame, style="Dark.TFrame")  # Assign value to file_row
        file_row.pack(anchor="w", fill=tk.X, pady=(6, 0))  # Close bracket/parenthesis
        self.file_entry = ttk.Entry(file_row, textvariable=self.file_path_var, width=28)  # Assign value to self.file_entry
        self.file_entry.pack(side=tk.LEFT, padx=(0, 6))  # Close bracket/parenthesis
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Button(file_row, text="Browse", style="Dark.TButton", command=self.browse_file).pack(side=tk.LEFT)

        # Max posts + cache toggle (for Live)
        opts = ttk.Frame(control_frame, style="Dark.TFrame")  # Assign value to opts
        opts.pack(anchor="w", pady=(10, 0), fill=tk.X)  # Close bracket/parenthesis
        ttk.Label(opts, text="Max posts", style="Dark.TLabel").grid(row=0, column=0, sticky="w")  # Close bracket/parenthesis
        self.max_posts_var = tk.StringVar(value="50")  # Assign value to self.max_posts_var
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        ttk.Entry(opts, textvariable=self.max_posts_var, width=8).grid(row=0, column=1, sticky="w", padx=(6, 0))

        self.force_refresh_var = tk.BooleanVar(value=False)  # Assign value to self.force_refresh_var
        ttk.Checkbutton(  # Execute statement or expression
            control_frame,  # Execute statement or expression
            text="Force refresh (ignore cache)",  # Assign value to text
            variable=self.force_refresh_var,  # Assign value to variable
            style="Dark.TRadiobutton",  # Assign value to style
        ).pack(anchor="w", pady=(6, 0))  # Close bracket/parenthesis

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)  # Close bracket/parenthesis

        self.run_button = ttk.Button(  # Assign value to self.run_button
            control_frame,  # Execute statement or expression
            text="RUN ANALYSIS",  # Assign value to text
            style="Dark.TButton",  # Assign value to style
            command=self.run_analysis,  # Assign value to command
            width=25,  # Assign value to width
        )  # Close bracket/parenthesis
        self.run_button.pack(anchor="w", pady=(0, 6))  # Close bracket/parenthesis

        self.status_var = tk.StringVar(value="Ready.")  # Assign value to self.status_var
        ttk.Label(  # Execute statement or expression
            control_frame,  # Execute statement or expression
            textvariable=self.status_var,  # Assign value to textvariable
            style="Dark.TLabel",  # Assign value to style
            font=("Segoe UI", 9, "italic"),  # Assign value to font
            wraplength=300,  # Assign value to wraplength
            justify="left",  # Assign value to justify
        ).pack(anchor="w", pady=(4, 0))  # Close bracket/parenthesis

        output_frame = ttk.Frame(main_frame, style="Dark.TFrame")  # Assign value to output_frame
        output_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

        self.notebook = ttk.Notebook(output_frame, style="Dark.TNotebook")  # Assign value to self.notebook
        self.notebook.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

        self.tab_overview = ttk.Frame(self.notebook, style="Dark.TFrame")  # Assign value to self.tab_overview
        self.tab_temporal = ttk.Frame(self.notebook, style="Dark.TFrame")  # Assign value to self.tab_temporal
        self.tab_sentiment = ttk.Frame(self.notebook, style="Dark.TFrame")  # Assign value to self.tab_sentiment
        self.tab_leakage = ttk.Frame(self.notebook, style="Dark.TFrame")  # Assign value to self.tab_leakage
        self.tab_raw = ttk.Frame(self.notebook, style="Dark.TFrame")  # Assign value to self.tab_raw

        self.notebook.add(self.tab_overview, text="Overview")  # Close bracket/parenthesis
        self.notebook.add(self.tab_temporal, text="Temporal patterns")  # Close bracket/parenthesis
        self.notebook.add(self.tab_sentiment, text="Sentiment")  # Close bracket/parenthesis
        self.notebook.add(self.tab_leakage, text="Image leakage")  # Close bracket/parenthesis
        self.notebook.add(self.tab_raw, text="Raw posts")  # Close bracket/parenthesis

        self.build_overview_tab()  # Call instance method
        self.build_temporal_tab()  # Call instance method
        self.build_sentiment_tab()  # Call instance method
        self.build_leakage_tab()  # Call instance method
        self.build_raw_tab()  # Call instance method

    def browse_file(self):  # Define function browse_file
        path = filedialog.askopenfilename(  # Assign value to path
            title="Select dataset file",  # Assign value to title
            filetypes=[  # Assign value to filetypes
                ("CSV files", "*.csv"),  # Execute statement or expression
                ("Excel files", "*.xlsx;*.xls"),  # Execute statement or expression
                ("Text files", "*.txt"),  # Execute statement or expression
                ("All files", "*.*"),  # Execute statement or expression
            ],  # Close structure
        )  # Close bracket/parenthesis
        if path:  # Check conditional statement
            self.file_path_var.set(path)  # Close bracket/parenthesis
            self.source_var.set("File (CSV/XLSX/TXT)")  # Close bracket/parenthesis

    def ensure_live_credentials(self) -> bool:  # Define function ensure_live_credentials
        """
        Tutor-approved mode:
        - targets are usernames only
        - login credentials are provided via environment variables
        This function prompts once (GUI) if missing, then sets env vars for this process.
        """
        ig_user = os.environ.get("IG_USER", "").strip()  # Assign value to ig_user
        ig_pass = os.environ.get("IG_PASS", "").strip()  # Assign value to ig_pass
        if ig_user and ig_pass:  # Check conditional statement
            return True  # Return value from function

        # Prompt interactively (not stored on disk)
        messagebox.showinfo(  # Execute statement or expression
            "Instagram credentials required",  # Execute statement or expression
            "Live mode requires IG_USER and IG_PASS environment variables.\n\n"  # Execute statement or expression
            "To continue, enter them now (they will be used only for this session).",  # Execute statement or expression
        )  # Close bracket/parenthesis
        # Assign value to u
        # Assign value to u
        u = simpledialog.askstring("IG_USER", "Enter Instagram username (login account):", parent=self)
        if not u:  # Check conditional statement
            return False  # Return value from function
        p = simpledialog.askstring("IG_PASS", "Enter Instagram password:", show="*", parent=self)  # Assign value to p
        if not p:  # Check conditional statement
            return False  # Return value from function

        os.environ["IG_USER"] = u.strip()  # Assign value to os.environ["IG_USER"]
        os.environ["IG_PASS"] = p  # Assign value to os.environ["IG_PASS"]
        return True  # Return value from function

    def parse_time_window(self) -> TimeWindow | None:  # Define function parse_time_window
        window_mode = self.window_var.get()  # Assign value to window_mode
        if window_mode == "All available":  # Check conditional statement
            return None  # Return value from function
        if window_mode == "Last 7 days":  # Check conditional statement
            return last_n_days(7)  # Return value from function
        if window_mode == "Last 30 days":  # Check conditional statement
            return last_n_days(30)  # Return value from function
        # Custom range
        s = self.start_entry.get().strip()  # Assign value to s
        e = self.end_entry.get().strip()  # Assign value to e
        if not s or not e:  # Check conditional statement
            messagebox.showerror("Invalid dates", "Please enter both start and end dates.")  # Close bracket/parenthesis
            return None  # Return value from function
        try:  # Start of try block for exception handling
            start_date = datetime.strptime(s, "%Y-%m-%d").date()  # Assign value to start_date
            end_date = datetime.strptime(e, "%Y-%m-%d").date()  # Assign value to end_date
        except Exception:  # Handle specific exceptions
            messagebox.showerror("Invalid dates", "Dates must be in format YYYY-MM-DD.")  # Close bracket/parenthesis
            return None  # Return value from function
        if start_date > end_date:  # Check conditional statement
            messagebox.showerror("Invalid range", "Start date must be before end date.")  # Close bracket/parenthesis
            return None  # Return value from function
        return TimeWindow(start=start_date, end=end_date)  # Return value from function

    def load_posts_file_mode(self, target_username: str):  # Define function load_posts_file_mode
        """
        File mode assumes you have already exported data for your demo accounts.
        The actual parsing into the tool's internal Post objects is handled by app.scraper
        in your project architecture, so here we follow the simplest convention:
        - if a file is selected, it must be a per-target export your app.scraper can read.
        If your app.scraper does NOT read arbitrary files yet, keep using the per-target cached CSVs.
        """
        path = self.file_path_var.get().strip()  # Assign value to path
        if not path:  # Check conditional statement
            messagebox.showerror("No file selected", "Please choose a CSV/XLSX/TXT file first.")  # Close bracket/parenthesis
            return None  # Return value from function

        # If you already have a loader in app.scraper for file datasets, call it here.
        # Otherwise, the safest behaviour is to tell the user what is required.
        ext = os.path.splitext(path)[1].lower()  # Assign value to ext
        if ext not in [".csv", ".xlsx", ".xls", ".txt"]:  # Check conditional statement
            messagebox.showerror("Unsupported file", "Supported: CSV, XLSX/XLS, TXT.")  # Close bracket/parenthesis
            return None  # Return value from function

        # Minimal pragmatic approach:
        # - If you selected a CSV that is already in your expected "posts list" cache format,
        #   your get_posts_for_profile may still not apply. So we present a clear error.
        # If you want true arbitrary file ingestion, we can wire a dedicated parser next.
        messagebox.showinfo(  # Execute statement or expression
            "File mode note",  # Execute statement or expression
            # Execute statement or expression
            # Execute statement or expression
            "File mode is enabled, but this build expects your project’s existing per-target cache loader.\n\n"
            "If your selected file is not wired into app.scraper yet, the simplest approach is:\n"  # Execute statement or expression
            "1) Export each target to data/<username>_posts.csv\n"  # Execute statement or expression
            "2) Use Live mode once (or your exporter script) to create those cached CSVs\n"  # Execute statement or expression
            "3) Re-run with Force refresh OFF to read from cache.\n\n"  # Execute statement or expression
            # Execute statement or expression
            # Execute statement or expression
            "If you want, I can wire a full CSV/XLSX parser into this script to ingest your dataset.csv directly.",
        )  # Close bracket/parenthesis
        return None  # Return value from function

    def build_overview_tab(self):  # Define function build_overview_tab
        frame = self.tab_overview  # Assign value to frame
        top = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to top
        top.pack(fill=tk.X, pady=8, padx=8)  # Close bracket/parenthesis

        # Assign value to self.label_time
        # Assign value to self.label_time
        self.label_time = ttk.Label(top, text="Time window: –", style="Dark.TLabel", font=("Segoe UI", 10, "italic"))
        self.label_time.pack(anchor="w")  # Close bracket/parenthesis

        stats_frame = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to stats_frame
        stats_frame.pack(fill=tk.X, padx=8)  # Close bracket/parenthesis

        # Assign value to self.ov_total
        # Assign value to self.ov_total
        self.ov_total = ttk.Label(stats_frame, text="Total posts: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.ov_days
        # Assign value to self.ov_days
        self.ov_days = ttk.Label(stats_frame, text="Days covered: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.ov_mean
        # Assign value to self.ov_mean
        self.ov_mean = ttk.Label(stats_frame, text="Mean posts/day: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.ov_median
        # Assign value to self.ov_median
        self.ov_median = ttk.Label(stats_frame, text="Median posts/day: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.ov_busiest
        # Assign value to self.ov_busiest
        self.ov_busiest = ttk.Label(stats_frame, text="Busiest hour: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.ov_busiest_count
        # Assign value to self.ov_busiest_count
        self.ov_busiest_count = ttk.Label(stats_frame, text="Posts at busiest hour: –", style="Dark.TLabel", font=("Consolas", 11))

        self.ov_total.grid(row=0, column=0, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.ov_days.grid(row=0, column=1, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.ov_mean.grid(row=1, column=0, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.ov_median.grid(row=1, column=1, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.ov_busiest.grid(row=2, column=0, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.ov_busiest_count.grid(row=2, column=1, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis

        table_frame = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to table_frame
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 8))  # Close bracket/parenthesis
        self.overview_tree = self.make_treeview(  # Assign value to self.overview_tree
            table_frame,  # Execute statement or expression
            ["timestamp", "text"],  # Execute statement or expression
            ["Timestamp (UTC)", "Caption"],  # Execute statement or expression
            col_widths=[180, 700],  # Assign value to col_widths
        )  # Close bracket/parenthesis

    def build_temporal_tab(self):  # Define function build_temporal_tab
        frame = self.tab_temporal  # Assign value to frame
        charts_frame = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to charts_frame
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Close bracket/parenthesis
        self.temp_top = ttk.Frame(charts_frame, style="Dark.TFrame")  # Assign value to self.temp_top
        self.temp_mid = ttk.Frame(charts_frame, style="Dark.TFrame")  # Assign value to self.temp_mid
        self.temp_bot = ttk.Frame(charts_frame, style="Dark.TFrame")  # Assign value to self.temp_bot
        self.temp_top.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
        self.temp_mid.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
        self.temp_bot.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

    def build_sentiment_tab(self):  # Define function build_sentiment_tab
        frame = self.tab_sentiment  # Assign value to frame
        top = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to top
        top.pack(fill=tk.X, padx=8, pady=(8, 0))  # Close bracket/parenthesis
        # Assign value to self.sent_mean
        # Assign value to self.sent_mean
        self.sent_mean = ttk.Label(top, text="Mean compound: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.sent_median
        # Assign value to self.sent_median
        self.sent_median = ttk.Label(top, text="Median compound: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.sent_min
        # Assign value to self.sent_min
        self.sent_min = ttk.Label(top, text="Min compound: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.sent_max
        # Assign value to self.sent_max
        self.sent_max = ttk.Label(top, text="Max compound: –", style="Dark.TLabel", font=("Consolas", 11))
        self.sent_mean.grid(row=0, column=0, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.sent_median.grid(row=0, column=1, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.sent_min.grid(row=1, column=0, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.sent_max.grid(row=1, column=1, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis

        chart_frame = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to chart_frame
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Close bracket/parenthesis
        self.sent_chart_frame = chart_frame  # Assign value to self.sent_chart_frame

        table_frame = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to table_frame
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))  # Close bracket/parenthesis
        self.sent_tree = self.make_treeview(  # Assign value to self.sent_tree
            table_frame,  # Execute statement or expression
            ["timestamp", "compound", "text"],  # Execute statement or expression
            ["Timestamp (UTC)", "Compound", "Caption"],  # Execute statement or expression
            col_widths=[160, 80, 600],  # Assign value to col_widths
        )  # Close bracket/parenthesis

    def build_leakage_tab(self):  # Define function build_leakage_tab
        frame = self.tab_leakage  # Assign value to frame
        top = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to top
        top.pack(fill=tk.X, padx=8, pady=(8, 0))  # Close bracket/parenthesis
        # Assign value to self.leak_total
        # Assign value to self.leak_total
        self.leak_total = ttk.Label(top, text="Total images: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.leak_gps
        # Assign value to self.leak_gps
        self.leak_gps = ttk.Label(top, text="Images with GPS: –", style="Dark.TLabel", font=("Consolas", 11))
        # Assign value to self.leak_text
        # Assign value to self.leak_text
        self.leak_text = ttk.Label(top, text="Images with text: –", style="Dark.TLabel", font=("Consolas", 11))
        self.leak_total.grid(row=0, column=0, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.leak_gps.grid(row=0, column=1, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis
        self.leak_text.grid(row=0, column=2, sticky="w", padx=4, pady=2)  # Close bracket/parenthesis

        content = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to content
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Close bracket/parenthesis

        left = ttk.Frame(content, style="Dark.TFrame")  # Assign value to left
        right = ttk.Frame(content, style="Dark.TFrame")  # Assign value to right
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=(8, 0))  # Close bracket/parenthesis

        self.leak_tree = self.make_treeview(  # Assign value to self.leak_tree
            left,  # Execute statement or expression
            ["post_id", "image_filename", "gps_lat", "gps_lon", "text_snippet"],  # Execute statement or expression
            ["Post ID", "Image", "GPS lat", "GPS lon", "Text snippet"],  # Execute statement or expression
            col_widths=[120, 160, 80, 80, 500],  # Assign value to col_widths
        )  # Close bracket/parenthesis
        self.leak_tree.bind("<<TreeviewSelect>>", self.on_leak_select)  # Close bracket/parenthesis

        # Assign value to preview_title
        # Assign value to preview_title
        preview_title = ttk.Label(right, text="Image preview", style="Dark.TLabel", font=("Segoe UI", 10, "bold"))
        preview_title.pack(anchor="w", pady=(0, 4))  # Close bracket/parenthesis

        self.leak_image_label = tk.Label(  # Assign value to self.leak_image_label
            right,  # Execute statement or expression
            bg="#101620",
            fg="#E5F0FF",
            width=45,  # Assign value to width
            height=18,  # Assign value to height
            anchor="center",  # Assign value to anchor
            text="No image selected",  # Assign value to text
        )  # Close bracket/parenthesis
        self.leak_image_label.pack(fill=tk.BOTH, expand=False)  # Close bracket/parenthesis

        # Assign value to text_title
        # Assign value to text_title
        text_title = ttk.Label(right, text="Recognised text (OCR)", style="Dark.TLabel", font=("Segoe UI", 10, "bold"))
        text_title.pack(anchor="w", pady=(8, 4))  # Close bracket/parenthesis

        self.leak_text_widget = tk.Text(  # Assign value to self.leak_text_widget
            right,  # Execute statement or expression
            height=10,  # Assign value to height
            bg="#050910",
            fg="#E5F0FF",
            insertbackground="#E5F0FF",
            wrap="word",  # Assign value to wrap
        )  # Close bracket/parenthesis
        self.leak_text_widget.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis

    def build_raw_tab(self):  # Define function build_raw_tab
        frame = self.tab_raw  # Assign value to frame
        table_frame = ttk.Frame(frame, style="Dark.TFrame")  # Assign value to table_frame
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Close bracket/parenthesis
        self.raw_tree = self.make_treeview(  # Assign value to self.raw_tree
            table_frame,  # Execute statement or expression
            ["post_id", "timestamp", "text", "image_filename"],  # Execute statement or expression
            ["ID", "Timestamp (UTC)", "Caption", "Image"],  # Execute statement or expression
            col_widths=[120, 160, 500, 180],  # Assign value to col_widths
        )  # Close bracket/parenthesis

    def make_treeview(self, parent, columns, headings, col_widths=None):  # Define function make_treeview
        frame = ttk.Frame(parent, style="Dark.TFrame")  # Assign value to frame
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
        for i, col in enumerate(columns):  # Iterate in a loop
            width = 120  # Assign value to width
            if col_widths and i < len(col_widths):  # Check conditional statement
                width = col_widths[i]  # Assign value to width
            tree.heading(col, text=headings[i])  # Close bracket/parenthesis
            tree.column(col, width=width, anchor="w")  # Close bracket/parenthesis
        return tree  # Return value from function

    def run_analysis(self):  # Define function run_analysis
        label = self.target_var.get()  # Assign value to label
        if not label or label not in self.target_by_label:  # Check conditional statement
            messagebox.showerror("No target", "Please select a target account.")  # Close bracket/parenthesis
            return  # Return value from function
        target = self.target_by_label[label]  # Assign value to target

        # window
        window = self.parse_time_window()  # Assign value to window
        if self.window_var.get() != "All available" and window is None:  # Check conditional statement
            return  # error already shown for invalid custom range

        # source
        source = self.source_var.get().strip()  # Assign value to source
        self.status_var.set("Loading posts...")  # Close bracket/parenthesis
        self.update_idletasks()  # Call instance method

        try:  # Start of try block for exception handling
            if source == "Live (Instagram)":  # Check conditional statement
                if not self.ensure_live_credentials():  # Check conditional statement
                    self.status_var.set("Live mode cancelled (credentials not provided).")  # Close bracket/parenthesis
                    return  # Return value from function

                # optional: force_refresh could be passed into your scraper if supported.
                # If not supported, keep as UI-only for now.
                posts_all = get_posts_for_profile(target.profile_url)  # Assign value to posts_all

            else:  # Execute if preceding conditions are false
                posts_all = self.load_posts_file_mode(target.username)  # Assign value to posts_all
                if posts_all is None:  # Check conditional statement
                    self.status_var.set("No posts loaded (file mode not yet wired).")  # Close bracket/parenthesis
                    return  # Return value from function

        except Exception as e:  # Handle specific exceptions
            messagebox.showerror("Error", f"Error loading posts:\n{e}")  # Close bracket/parenthesis
            self.status_var.set("Error while loading posts.")  # Close bracket/parenthesis
            return  # Return value from function

        if not posts_all:  # Check conditional statement
            messagebox.showwarning("No posts", "No posts loaded for this target.")  # Close bracket/parenthesis
            self.status_var.set("No posts.")  # Close bracket/parenthesis
            return  # Return value from function

        # filter by time window
        if window is not None:  # Check conditional statement
            posts = filter_posts(posts_all, window)  # Assign value to posts
            self.time_label = f"{window.start} → {window.end}"  # Assign value to self.time_label
        else:  # Execute if preceding conditions are false
            posts = posts_all  # Assign value to posts
            full = full_window(posts_all)  # Assign value to full
            self.time_label = f"{full.start} → {full.end}"  # Assign value to self.time_label

        if not posts:  # Check conditional statement
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            messagebox.showwarning("No posts in window", "No posts fall inside the selected time window.")
            self.status_var.set("No posts in window.")  # Close bracket/parenthesis
            return  # Return value from function

        # persist + analyse
        save_posts(posts)  # Call function save_posts

        self.df_posts = posts_to_dataframe(posts)  # Assign value to self.df_posts
        # harden schema so UI never crashes if optional cols are missing
        if self.df_posts is not None:  # Check conditional statement
            if "image_filename" not in self.df_posts.columns:  # Check conditional statement
                self.df_posts["image_filename"] = ""  # Assign value to self.df_posts["image_filename"]
            if "text" not in self.df_posts.columns:  # Check conditional statement
                self.df_posts["text"] = ""  # Assign value to self.df_posts["text"]

        self.df_sent = sentiment_dataframe(posts)  # Assign value to self.df_sent
        self.df_daily_sent = daily_sentiment(self.df_sent)  # Assign value to self.df_daily_sent
        self.leaks = analyse_image_leaks(posts)  # Assign value to self.leaks
        self.leak_stats = leakage_summary(self.leaks)  # Assign value to self.leak_stats
        self.stats = posting_summary(self.df_posts)  # Assign value to self.stats

        self.update_overview()  # Call instance method
        self.update_temporal()  # Call instance method
        self.update_sentiment()  # Call instance method
        self.update_leakage()  # Call instance method
        self.update_raw()  # Call instance method
        self.status_var.set("Analysis completed.")  # Close bracket/parenthesis

    def update_overview(self):  # Define function update_overview
        if self.df_posts is None:  # Check conditional statement
            return  # Return value from function
        self.label_time.config(text=f"Time window: {self.time_label}")  # Close bracket/parenthesis
        s = self.stats  # Assign value to s
        self.ov_total.config(text=f"Total posts: {s.get('total_posts', '–')}")  # Close bracket/parenthesis
        self.ov_days.config(text=f"Days covered: {s.get('days_covered', '–')}")  # Close bracket/parenthesis
        self.ov_mean.config(text=f"Mean posts/day: {s.get('mean_posts_per_day', 0):.2f}")  # Close bracket/parenthesis
        self.ov_median.config(text=f"Median posts/day: {s.get('median_posts_per_day', 0):.2f}")  # Close bracket/parenthesis
        busiest = s.get("busiest_hour")  # Assign value to busiest
        busiest_label = "–" if busiest is None else f"{busiest}:00"  # Assign value to busiest_label
        self.ov_busiest.config(text=f"Busiest hour: {busiest_label}")  # Close bracket/parenthesis
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        self.ov_busiest_count.config(text=f"Posts at busiest hour: {s.get('busiest_hour_count', 0)}")

        tree = self.overview_tree  # Assign value to tree
        for item in tree.get_children():  # Iterate in a loop
            tree.delete(item)  # Close bracket/parenthesis

        # Assign value to df
        # Assign value to df
        df = self.df_posts.sort_values("timestamp", ascending=False)[["timestamp", "text"]].head(100)
        for _, row in df.iterrows():  # Iterate in a loop
            text = row.get("text", "") or ""  # Assign value to text
            if len(text) > 120:  # Check conditional statement
                text = text[:117] + "..."  # Assign value to text
            tree.insert("", tk.END, values=[row.get("timestamp", ""), text])  # Close bracket/parenthesis

    def clear_chart_frame(self, frame):  # Define function clear_chart_frame
        for child in frame.winfo_children():  # Iterate in a loop
            child.destroy()  # Close bracket/parenthesis
        self.chart_canvases = [c for c in self.chart_canvases if c.get_tk_widget().winfo_exists()]  # Assign value to self.chart_canvases

    def draw_chart(self, frame, fig: Figure):  # Define function draw_chart
        canvas = FigureCanvasTkAgg(fig, master=frame)  # Assign value to canvas
        canvas.draw()  # Close bracket/parenthesis
        widget = canvas.get_tk_widget()  # Assign value to widget
        widget.pack(fill=tk.BOTH, expand=True)  # Close bracket/parenthesis
        self.chart_canvases.append(canvas)  # Close bracket/parenthesis

    def update_temporal(self):  # Define function update_temporal
        if self.df_posts is None:  # Check conditional statement
            return  # Return value from function
        self.clear_chart_frame(self.temp_top)  # Call instance method
        self.clear_chart_frame(self.temp_mid)  # Call instance method
        self.clear_chart_frame(self.temp_bot)  # Call instance method

        per_day = posts_per_day_df(self.df_posts)  # Assign value to per_day
        per_hour = posts_per_hour_df(self.df_posts)  # Assign value to per_hour
        per_weekday = posts_per_weekday_df(self.df_posts)  # Assign value to per_weekday

        if not per_day.empty:  # Check conditional statement
            fig1 = Figure(figsize=(6, 2.2), dpi=100)  # Assign value to fig1
            ax1 = fig1.add_subplot(111)  # Assign value to ax1
            ax1.plot(per_day["date"], per_day["posts"])  # Close bracket/parenthesis
            ax1.set_facecolor("#101620")
            fig1.patch.set_facecolor("#050910")
            ax1.tick_params(axis="x", labelrotation=45, colors="#E5F0FF")
            ax1.tick_params(axis="y", colors="#E5F0FF")
            ax1.set_title("Posts per day", color="#E5F0FF")
            ax1.set_xlabel("Date (UTC)", color="#E5F0FF")
            ax1.set_ylabel("Count", color="#E5F0FF")
            ax1.grid(alpha=0.2, color="#445")
            self.draw_chart(self.temp_top, fig1)  # Call instance method

        if not per_hour.empty:  # Check conditional statement
            fig2 = Figure(figsize=(6, 2.2), dpi=100)  # Assign value to fig2
            ax2 = fig2.add_subplot(111)  # Assign value to ax2
            ax2.bar(per_hour["hour"], per_hour["posts"])  # Close bracket/parenthesis
            ax2.set_facecolor("#101620")
            fig2.patch.set_facecolor("#050910")
            ax2.tick_params(axis="x", colors="#E5F0FF")
            ax2.tick_params(axis="y", colors="#E5F0FF")
            ax2.set_title("Posts by hour of day", color="#E5F0FF")
            ax2.set_xlabel("Hour (0–23, UTC)", color="#E5F0FF")
            ax2.set_ylabel("Count", color="#E5F0FF")
            ax2.grid(alpha=0.2, color="#445")
            self.draw_chart(self.temp_mid, fig2)  # Call instance method

        if not per_weekday.empty:  # Check conditional statement
            fig3 = Figure(figsize=(6, 2.2), dpi=100)  # Assign value to fig3
            ax3 = fig3.add_subplot(111)  # Assign value to ax3
            ax3.bar(per_weekday["weekday"], per_weekday["posts"])  # Close bracket/parenthesis
            ax3.set_facecolor("#101620")
            fig3.patch.set_facecolor("#050910")
            ax3.tick_params(axis="x", labelrotation=20, colors="#E5F0FF")
            ax3.tick_params(axis="y", colors="#E5F0FF")
            ax3.set_title("Posts by weekday", color="#E5F0FF")
            ax3.set_xlabel("Weekday (UTC)", color="#E5F0FF")
            ax3.set_ylabel("Count", color="#E5F0FF")
            ax3.grid(alpha=0.2, color="#445")
            self.draw_chart(self.temp_bot, fig3)  # Call instance method

    def update_sentiment(self):  # Define function update_sentiment
        if self.df_sent is None:  # Check conditional statement
            return  # Return value from function

        if self.df_sent.empty:  # Check conditional statement
            self.sent_mean.config(text="Mean compound: –")  # Close bracket/parenthesis
            self.sent_median.config(text="Median compound: –")  # Close bracket/parenthesis
            self.sent_min.config(text="Min compound: –")  # Close bracket/parenthesis
            self.sent_max.config(text="Max compound: –")  # Close bracket/parenthesis
        else:  # Execute if preceding conditions are false
            s = sentiment_summary(self.df_sent)  # Assign value to s
            self.sent_mean.config(text=f"Mean compound: {s['mean_compound']:.3f}")  # Close bracket/parenthesis
            self.sent_median.config(text=f"Median compound: {s['median_compound']:.3f}")  # Close bracket/parenthesis
            self.sent_min.config(text=f"Min compound: {s['min_compound']:.3f}")  # Close bracket/parenthesis
            self.sent_max.config(text=f"Max compound: {s['max_compound']:.3f}")  # Close bracket/parenthesis

        self.clear_chart_frame(self.sent_chart_frame)  # Call instance method
        if self.df_daily_sent is not None and not self.df_daily_sent.empty:  # Check conditional statement
            fig = Figure(figsize=(6, 2.5), dpi=100)  # Assign value to fig
            ax = fig.add_subplot(111)  # Assign value to ax
            ax.plot(self.df_daily_sent["date"], self.df_daily_sent["avg_compound"])  # Close bracket/parenthesis
            ax.set_facecolor("#101620")
            fig.patch.set_facecolor("#050910")
            ax.tick_params(axis="x", labelrotation=45, colors="#E5F0FF")
            ax.tick_params(axis="y", colors="#E5F0FF")
            ax.set_title("Daily average sentiment", color="#E5F0FF")
            ax.set_xlabel("Date (UTC)", color="#E5F0FF")
            ax.set_ylabel("Compound score", color="#E5F0FF")
            ax.grid(alpha=0.2, color="#445")
            self.draw_chart(self.sent_chart_frame, fig)  # Call instance method

        tree = self.sent_tree  # Assign value to tree
        for item in tree.get_children():  # Iterate in a loop
            tree.delete(item)  # Close bracket/parenthesis

        if not self.df_sent.empty:  # Check conditional statement
            # Assign value to df
            # Assign value to df
            df = self.df_sent[["timestamp", "compound", "text"]].sort_values("timestamp", ascending=False).head(100)
            for _, row in df.iterrows():  # Iterate in a loop
                text = row.get("text", "") or ""  # Assign value to text
                if len(text) > 100:  # Check conditional statement
                    text = text[:97] + "..."  # Assign value to text
                tree.insert("", tk.END, values=[row["timestamp"], f"{row['compound']:.3f}", text])  # Close bracket/parenthesis

    def update_leakage(self):  # Define function update_leakage
        self.leak_total.config(text=f"Total images: {self.leak_stats.get('total_images', 0)}")  # Close bracket/parenthesis
        self.leak_gps.config(text=f"Images with GPS: {self.leak_stats.get('images_with_gps', 0)}")  # Close bracket/parenthesis
        # Close bracket/parenthesis
        # Close bracket/parenthesis
        self.leak_text.config(text=f"Images with text: {self.leak_stats.get('images_with_text', 0)}")

        tree = self.leak_tree  # Assign value to tree
        for item in tree.get_children():  # Iterate in a loop
            tree.delete(item)  # Close bracket/parenthesis

        self.leak_row_map = {}  # Assign value to self.leak_row_map
        for l in self.leaks:  # Iterate in a loop
            text = (l.text or "")  # Assign value to text
            if len(text) > 120:  # Check conditional statement
                text = text[:117] + "..."  # Assign value to text
            row_id = tree.insert(  # Assign value to row_id
                "",  # Execute statement or expression
                tk.END,  # Execute statement or expression
                values=[  # Assign value to values
                    getattr(l, "post_id", ""),  # Call function getattr
                    getattr(l, "image_filename", ""),  # Call function getattr
                    "" if getattr(l, "gps_lat", None) is None else f"{l.gps_lat:.5f}",  # Execute statement or expression
                    "" if getattr(l, "gps_lon", None) is None else f"{l.gps_lon:.5f}",  # Execute statement or expression
                    text,  # Execute statement or expression
                ],  # Close structure
            )  # Close bracket/parenthesis
            self.leak_row_map[row_id] = l  # Assign value to self.leak_row_map[row_id]

        self.leak_image_label.config(image="", text="No image selected")  # Close bracket/parenthesis
        self.leak_text_widget.delete("1.0", tk.END)  # Close bracket/parenthesis

    def on_leak_select(self, event):  # Define function on_leak_select
        selection = self.leak_tree.selection()  # Assign value to selection
        if not selection:  # Check conditional statement
            return  # Return value from function
        row_id = selection[0]  # Assign value to row_id
        leak = self.leak_row_map.get(row_id)  # Assign value to leak
        if not leak:  # Check conditional statement
            return  # Return value from function
        try:  # Start of try block for exception handling
            path = image_path_for(leak.username, leak.image_filename)  # Assign value to path
            img = Image.open(path)  # Assign value to img
            img.thumbnail((420, 420))  # Close bracket/parenthesis
            self._leak_img_tk = ImageTk.PhotoImage(img)  # Assign value to self._leak_img_tk
            self.leak_image_label.config(image=self._leak_img_tk, text="")  # Close bracket/parenthesis
        except Exception:  # Handle specific exceptions
            self.leak_image_label.config(image="", text="Image not found")  # Close bracket/parenthesis

        self.leak_text_widget.delete("1.0", tk.END)  # Close bracket/parenthesis
        self.leak_text_widget.insert("1.0", getattr(leak, "text", "") or "")  # Close bracket/parenthesis

    def update_raw(self):  # Define function update_raw
        if self.df_posts is None:  # Check conditional statement
            return  # Return value from function

        # Never crash if optional column is missing
        df = self.df_posts.copy()  # Assign value to df
        if "image_filename" not in df.columns:  # Check conditional statement
            df["image_filename"] = ""  # Assign value to df["image_filename"]
        if "text" not in df.columns:  # Check conditional statement
            df["text"] = ""  # Assign value to df["text"]

        tree = self.raw_tree  # Assign value to tree
        for item in tree.get_children():  # Iterate in a loop
            tree.delete(item)  # Close bracket/parenthesis

        view = df[["post_id", "timestamp", "text", "image_filename"]].sort_values("timestamp")  # Assign value to view
        for _, row in view.iterrows():  # Iterate in a loop
            text = row.get("text", "") or ""  # Assign value to text
            if len(text) > 80:  # Check conditional statement
                text = text[:77] + "..."  # Assign value to text
            # Close bracket/parenthesis
            # Close bracket/parenthesis
            tree.insert("", tk.END, values=[row.get("post_id", ""), row.get("timestamp", ""), text, row.get("image_filename", "")])


def main():  # Define function main
    ensure_directories()  # Call function ensure_directories
    initialise_database()  # Call function initialise_database
    targets = load_targets()  # Assign value to targets
    if not targets:  # Check conditional statement
        messagebox.showerror("Error", "No targets found in targets.json")  # Close bracket/parenthesis
        return  # Return value from function
    app = OSINTApp(targets)  # Assign value to app
    app.mainloop()  # Close bracket/parenthesis


if __name__ == "__main__":  # Check conditional statement
    main()  # Call function main
