from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

import pandas as pd
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

from app.config import ensure_directories
from app.database import initialise_database, save_posts
from app.targets import load_targets, TargetAccount
from app.timefilters import last_n_days, full_window, filter_posts, TimeWindow
from app.scraper import get_posts_for_profile
from app.timestamp_analyser import posts_to_dataframe, posting_summary
from app.sentiment_analyser import sentiment_dataframe, daily_sentiment, sentiment_summary
from app.leakage_analyser import analyse_image_leaks, leakage_summary
from app.exif_analyser import image_path_for

matplotlib.use("TkAgg")


def posts_per_day_df(df_posts: pd.DataFrame) -> pd.DataFrame:
    if df_posts.empty:
        return pd.DataFrame(columns=["date", "posts"])
    out = df_posts.groupby("date")["post_id"].count().reset_index(name="posts")
    return out.sort_values("date")


def posts_per_hour_df(df_posts: pd.DataFrame) -> pd.DataFrame:
    if df_posts.empty:
        return pd.DataFrame(columns=["hour", "posts"])
    out = df_posts.groupby("hour")["post_id"].count().reset_index(name="posts")
    return out.sort_values("hour")


def posts_per_weekday_df(df_posts: pd.DataFrame) -> pd.DataFrame:
    if df_posts.empty:
        return pd.DataFrame(columns=["weekday", "posts"])
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    tmp = df_posts.groupby("weekday")["post_id"].count().reset_index(name="posts")
    tmp["weekday"] = pd.Categorical(tmp["weekday"], categories=order, ordered=True)
    tmp = tmp.sort_values("weekday")
    tmp["weekday"] = tmp["weekday"].astype(str)
    return tmp


class OSINTApp(tk.Tk):
    def __init__(self, targets: list[TargetAccount]):
        super().__init__()
        self.targets = targets
        self.target_by_label = {}
        self.df_posts: pd.DataFrame | None = None
        self.df_sent: pd.DataFrame | None = None
        self.df_daily_sent: pd.DataFrame | None = None
        self.leaks = []
        self.leak_stats = {}
        self.stats = {}
        self.time_label = ""
        self.chart_canvases: list[FigureCanvasTkAgg] = []
        self.leak_row_map = {}
        self._leak_img_tk: ImageTk.PhotoImage | None = None

        self.title("OSINT Social Media Analysis")
        self.geometry("1300x800")
        self.configure(bg="#050910")
        self.iconify()
        self.after(100, self.deiconify)

        self.configure_style()
        self.build_layout()

    def configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background="#050910", foreground="#E5F0FF", fieldbackground="#050910")
        style.configure("Dark.TFrame", background="#050910")
        style.configure("Dark.TLabel", background="#050910", foreground="#E5F0FF")
        style.configure("Dark.TButton", background="#1A2738", foreground="#E5F0FF", padding=6)
        style.map(
            "Dark.TButton",
            background=[("active", "#22344A"), ("pressed", "#182234")],
        )
        style.configure(
            "Dark.Treeview",
            background="#101620",
            foreground="#E5F0FF",
            fieldbackground="#101620",
            rowheight=22,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", "#28406A")],
            foreground=[("selected", "#FFFFFF")],
        )
        style.configure("Dark.TNotebook", background="#050910", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#101620", foreground="#E5F0FF", padding=(10, 4))
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", "#1A2738")],
            foreground=[("selected", "#FFFFFF")],
        )

    def build_layout(self):
        main_frame = ttk.Frame(self, style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        control_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        ttk.Label(
            control_frame,
            text="OSINT SOCIAL MEDIA TOOL",
            style="Dark.TLabel",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(control_frame, text="Target account", style="Dark.TLabel").pack(anchor="w")
        labels = []
        for t in self.targets:
            label = f"{t.label} ({t.username}, {t.group})"
            labels.append(label)
            self.target_by_label[label] = t
        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(
            control_frame,
            textvariable=self.target_var,
            values=labels,
            state="readonly",
            width=40,
        )
        if labels:
            self.target_combo.current(0)
        self.target_combo.pack(anchor="w", pady=(0, 10))

        ttk.Label(control_frame, text="Time window", style="Dark.TLabel").pack(anchor="w")
        self.window_var = tk.StringVar(value="Last 30 days")
        for text in ["All available", "Last 7 days", "Last 30 days", "Custom range"]:
            rb = ttk.Radiobutton(
                control_frame,
                text=text,
                value=text,
                variable=self.window_var,
                style="Dark.TRadiobutton",
            )
            rb.pack(anchor="w")

        self.custom_frame = ttk.Frame(control_frame, style="Dark.TFrame")
        self.custom_frame.pack(anchor="w", pady=(8, 8))
        ttk.Label(self.custom_frame, text="Start (YYYY-MM-DD)", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self.custom_frame, text="End (YYYY-MM-DD)", style="Dark.TLabel").grid(row=1, column=0, sticky="w")
        self.start_entry = ttk.Entry(self.custom_frame, width=18)
        self.end_entry = ttk.Entry(self.custom_frame, width=18)
        self.start_entry.grid(row=0, column=1, padx=(6, 0), pady=2)
        self.end_entry.grid(row=1, column=1, padx=(6, 0), pady=2)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        self.run_button = ttk.Button(
            control_frame,
            text="RUN ANALYSIS",
            style="Dark.TButton",
            command=self.run_analysis,
            width=25,
        )
        self.run_button.pack(anchor="w", pady=(0, 6))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(
            control_frame,
            textvariable=self.status_var,
            style="Dark.TLabel",
            font=("Segoe UI", 9, "italic"),
        ).pack(anchor="w", pady=(4, 0))

        output_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        output_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(output_frame, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_overview = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.tab_temporal = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.tab_sentiment = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.tab_leakage = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.tab_raw = ttk.Frame(self.notebook, style="Dark.TFrame")

        self.notebook.add(self.tab_overview, text="Overview")
        self.notebook.add(self.tab_temporal, text="Temporal patterns")
        self.notebook.add(self.tab_sentiment, text="Sentiment")
        self.notebook.add(self.tab_leakage, text="Image leakage")
        self.notebook.add(self.tab_raw, text="Raw posts")

        self.build_overview_tab()
        self.build_temporal_tab()
        self.build_sentiment_tab()
        self.build_leakage_tab()
        self.build_raw_tab()

    def build_overview_tab(self):
        frame = self.tab_overview
        top = ttk.Frame(frame, style="Dark.TFrame")
        top.pack(fill=tk.X, pady=8, padx=8)
        self.label_time = ttk.Label(top, text="Time window: –", style="Dark.TLabel", font=("Segoe UI", 10, "italic"))
        self.label_time.pack(anchor="w")
        stats_frame = ttk.Frame(frame, style="Dark.TFrame")
        stats_frame.pack(fill=tk.X, padx=8)
        self.ov_total = ttk.Label(stats_frame, text="Total posts: –", style="Dark.TLabel", font=("Consolas", 11))
        self.ov_days = ttk.Label(stats_frame, text="Days covered: –", style="Dark.TLabel", font=("Consolas", 11))
        self.ov_mean = ttk.Label(stats_frame, text="Mean posts/day: –", style="Dark.TLabel", font=("Consolas", 11))
        self.ov_median = ttk.Label(stats_frame, text="Median posts/day: –", style="Dark.TLabel", font=("Consolas", 11))
        self.ov_busiest = ttk.Label(stats_frame, text="Busiest hour: –", style="Dark.TLabel", font=("Consolas", 11))
        self.ov_busiest_count = ttk.Label(
            stats_frame,
            text="Posts at busiest hour: –",
            style="Dark.TLabel",
            font=("Consolas", 11),
        )
        self.ov_total.grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.ov_days.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.ov_mean.grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.ov_median.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        self.ov_busiest.grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.ov_busiest_count.grid(row=2, column=1, sticky="w", padx=4, pady=2)

        table_frame = ttk.Frame(frame, style="Dark.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 8))
        self.overview_tree = self.make_treeview(
            table_frame,
            ["timestamp", "text"],
            ["Timestamp", "Caption"],
            col_widths=[180, 700],
        )

    def build_temporal_tab(self):
        frame = self.tab_temporal
        charts_frame = ttk.Frame(frame, style="Dark.TFrame")
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.temp_top = ttk.Frame(charts_frame, style="Dark.TFrame")
        self.temp_mid = ttk.Frame(charts_frame, style="Dark.TFrame")
        self.temp_bot = ttk.Frame(charts_frame, style="Dark.TFrame")
        self.temp_top.pack(fill=tk.BOTH, expand=True)
        self.temp_mid.pack(fill=tk.BOTH, expand=True)
        self.temp_bot.pack(fill=tk.BOTH, expand=True)

    def build_sentiment_tab(self):
        frame = self.tab_sentiment
        top = ttk.Frame(frame, style="Dark.TFrame")
        top.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.sent_mean = ttk.Label(top, text="Mean compound: –", style="Dark.TLabel", font=("Consolas", 11))
        self.sent_median = ttk.Label(top, text="Median compound: –", style="Dark.TLabel", font=("Consolas", 11))
        self.sent_min = ttk.Label(top, text="Min compound: –", style="Dark.TLabel", font=("Consolas", 11))
        self.sent_max = ttk.Label(top, text="Max compound: –", style="Dark.TLabel", font=("Consolas", 11))
        self.sent_mean.grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.sent_median.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.sent_min.grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.sent_max.grid(row=1, column=1, sticky="w", padx=4, pady=2)

        chart_frame = ttk.Frame(frame, style="Dark.TFrame")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.sent_chart_frame = chart_frame

        table_frame = ttk.Frame(frame, style="Dark.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.sent_tree = self.make_treeview(
            table_frame,
            ["timestamp", "compound", "text"],
            ["Timestamp", "Compound", "Caption"],
            col_widths=[160, 80, 600],
        )

    def build_leakage_tab(self):
        frame = self.tab_leakage

        top = ttk.Frame(frame, style="Dark.TFrame")
        top.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.leak_total = ttk.Label(top, text="Total images: –", style="Dark.TLabel", font=("Consolas", 11))
        self.leak_gps = ttk.Label(top, text="Images with GPS: –", style="Dark.TLabel", font=("Consolas", 11))
        self.leak_text = ttk.Label(top, text="Images with text: –", style="Dark.TLabel", font=("Consolas", 11))
        self.leak_total.grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.leak_gps.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.leak_text.grid(row=0, column=2, sticky="w", padx=4, pady=2)

        content = ttk.Frame(frame, style="Dark.TFrame")
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.Frame(content, style="Dark.TFrame")
        right = ttk.Frame(content, style="Dark.TFrame")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=(8, 0))

        self.leak_tree = self.make_treeview(
            left,
            ["post_id", "image_filename", "gps_lat", "gps_lon", "text_snippet"],
            ["Post ID", "Image", "GPS lat", "GPS lon", "Text snippet"],
            col_widths=[120, 160, 80, 80, 500],
        )
        self.leak_tree.bind("<<TreeviewSelect>>", self.on_leak_select)

        preview_title = ttk.Label(
            right,
            text="Image preview",
            style="Dark.TLabel",
            font=("Segoe UI", 10, "bold"),
        )
        preview_title.pack(anchor="w", pady=(0, 4))

        self.leak_image_label = tk.Label(
            right,
            bg="#101620",
            fg="#E5F0FF",
            width=45,
            height=18,
            anchor="center",
            text="No image selected",
        )
        self.leak_image_label.pack(fill=tk.BOTH, expand=False)

        text_title = ttk.Label(
            right,
            text="Recognised text (OCR)",
            style="Dark.TLabel",
            font=("Segoe UI", 10, "bold"),
        )
        text_title.pack(anchor="w", pady=(8, 4))

        self.leak_text_widget = tk.Text(
            right,
            height=10,
            bg="#050910",
            fg="#E5F0FF",
            insertbackground="#E5F0FF",
            wrap="word",
        )
        self.leak_text_widget.pack(fill=tk.BOTH, expand=True)

    def build_raw_tab(self):
        frame = self.tab_raw
        table_frame = ttk.Frame(frame, style="Dark.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.raw_tree = self.make_treeview(
            table_frame,
            ["post_id", "timestamp", "text", "image_filename"],
            ["ID", "Timestamp", "Caption", "Image"],
            col_widths=[120, 160, 500, 140],
        )

    def make_treeview(self, parent, columns, headings, col_widths=None):
        frame = ttk.Frame(parent, style="Dark.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
        )
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        for i, col in enumerate(columns):
            width = 120
            if col_widths and i < len(col_widths):
                width = col_widths[i]
            tree.heading(col, text=headings[i])
            tree.column(col, width=width, anchor="w")
        return tree

    def run_analysis(self):
        label = self.target_var.get()
        if not label or label not in self.target_by_label:
            messagebox.showerror("No target", "Please select a target account.")
            return
        target = self.target_by_label[label]
        window_mode = self.window_var.get()
        start_date = None
        end_date = None
        if window_mode == "Custom range":
            s = self.start_entry.get().strip()
            e = self.end_entry.get().strip()
            if not s or not e:
                messagebox.showerror("Invalid dates", "Please enter both start and end dates.")
                return
            try:
                start_date = datetime.strptime(s, "%Y-%m-%d").date()
                end_date = datetime.strptime(e, "%Y-%m-%d").date()
            except Exception:
                messagebox.showerror("Invalid dates", "Dates must be in format YYYY-MM-DD.")
                return
            if start_date > end_date:
                messagebox.showerror("Invalid range", "Start date must be before end date.")
                return
        self.status_var.set("Loading posts...")
        self.update_idletasks()
        try:
            posts_all = get_posts_for_profile(target.profile_url)
        except Exception as e:
            messagebox.showerror("Error", f"Error loading posts:\n{e}")
            self.status_var.set("Error while loading posts.")
            return
        if not posts_all:
            messagebox.showwarning("No posts", "No posts loaded for this target.")
            self.status_var.set("No posts.")
            return
        if window_mode == "All available":
            window = None
        elif window_mode == "Last 7 days":
            window = last_n_days(7)
        elif window_mode == "Last 30 days":
            window = last_n_days(30)
        else:
            window = TimeWindow(start=start_date, end=end_date)
        if window is not None:
            posts = filter_posts(posts_all, window)
            self.time_label = f"{window.start} → {window.end}"
        else:
            posts = posts_all
            full = full_window(posts_all)
            self.time_label = f"{full.start} → {full.end}"
        if not posts:
            messagebox.showwarning("No posts in window", "No posts fall inside the selected time window.")
            self.status_var.set("No posts in window.")
            return
        save_posts(posts)
        self.df_posts = posts_to_dataframe(posts)
        self.df_sent = sentiment_dataframe(posts)
        self.df_daily_sent = daily_sentiment(self.df_sent)
        self.leaks = analyse_image_leaks(posts)
        self.leak_stats = leakage_summary(self.leaks)
        self.stats = posting_summary(self.df_posts)
        self.update_overview()
        self.update_temporal()
        self.update_sentiment()
        self.update_leakage()
        self.update_raw()
        self.status_var.set("Analysis completed.")

    def update_overview(self):
        if self.df_posts is None:
            return
        self.label_time.config(text=f"Time window: {self.time_label}")
        s = self.stats
        self.ov_total.config(text=f"Total posts: {s.get('total_posts', '–')}")
        self.ov_days.config(text=f"Days covered: {s.get('days_covered', '–')}")
        self.ov_mean.config(text=f"Mean posts/day: {s.get('mean_posts_per_day', 0):.2f}")
        self.ov_median.config(text=f"Median posts/day: {s.get('median_posts_per_day', 0):.2f}")
        busiest = s.get("busiest_hour")
        if busiest is None:
            busiest_label = "–"
        else:
            busiest_label = f"{busiest}:00"
        self.ov_busiest.config(text=f"Busiest hour: {busiest_label}")
        self.ov_busiest_count.config(text=f"Posts at busiest hour: {s.get('busiest_hour_count', 0)}")
        tree = self.overview_tree
        for item in tree.get_children():
            tree.delete(item)
        df = self.df_posts.sort_values("timestamp", ascending=False)[["timestamp", "text"]].head(100)
        for _, row in df.iterrows():
            text = row["text"] or ""
            if len(text) > 120:
                text = text[:117] + "..."
            tree.insert("", tk.END, values=[row["timestamp"], text])

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()
        self.chart_canvases = [c for c in self.chart_canvases if c.get_tk_widget().winfo_exists()]

    def draw_chart(self, frame, fig: Figure):
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill=tk.BOTH, expand=True)
        self.chart_canvases.append(canvas)

    def update_temporal(self):
        if self.df_posts is None:
            return
        self.clear_chart_frame(self.temp_top)
        self.clear_chart_frame(self.temp_mid)
        self.clear_chart_frame(self.temp_bot)
        per_day = posts_per_day_df(self.df_posts)
        per_hour = posts_per_hour_df(self.df_posts)
        per_weekday = posts_per_weekday_df(self.df_posts)
        if not per_day.empty:
            fig1 = Figure(figsize=(6, 2.2), dpi=100)
            ax1 = fig1.add_subplot(111)
            ax1.plot(per_day["date"], per_day["posts"])
            ax1.set_facecolor("#101620")
            fig1.patch.set_facecolor("#050910")
            ax1.tick_params(axis="x", labelrotation=45, colors="#E5F0FF")
            ax1.tick_params(axis="y", colors="#E5F0FF")
            ax1.set_title("Posts per day", color="#E5F0FF")
            ax1.grid(alpha=0.2, color="#445")
            self.draw_chart(self.temp_top, fig1)
        if not per_hour.empty:
            fig2 = Figure(figsize=(6, 2.2), dpi=100)
            ax2 = fig2.add_subplot(111)
            ax2.bar(per_hour["hour"], per_hour["posts"])
            ax2.set_facecolor("#101620")
            fig2.patch.set_facecolor("#050910")
            ax2.tick_params(axis="x", colors="#E5F0FF")
            ax2.tick_params(axis="y", colors="#E5F0FF")
            ax2.set_title("Posts by hour of day", color="#E5F0FF")
            ax2.grid(alpha=0.2, color="#445")
            self.draw_chart(self.temp_mid, fig2)
        if not per_weekday.empty:
            fig3 = Figure(figsize=(6, 2.2), dpi=100)
            ax3 = fig3.add_subplot(111)
            ax3.bar(per_weekday["weekday"], per_weekday["posts"])
            ax3.set_facecolor("#101620")
            fig3.patch.set_facecolor("#050910")
            ax3.tick_params(axis="x", labelrotation=20, colors="#E5F0FF")
            ax3.tick_params(axis="y", colors="#E5F0FF")
            ax3.set_title("Posts by weekday", color="#E5F0FF")
            ax3.grid(alpha=0.2, color="#445")
            self.draw_chart(self.temp_bot, fig3)

    def update_sentiment(self):
        if self.df_sent is None:
            return
        if self.df_sent.empty:
            self.sent_mean.config(text="Mean compound: –")
            self.sent_median.config(text="Median compound: –")
            self.sent_min.config(text="Min compound: –")
            self.sent_max.config(text="Max compound: –")
        else:
            s = sentiment_summary(self.df_sent)
            self.sent_mean.config(text=f"Mean compound: {s['mean_compound']:.3f}")
            self.sent_median.config(text=f"Median compound: {s['median_compound']:.3f}")
            self.sent_min.config(text=f"Min compound: {s['min_compound']:.3f}")
            self.sent_max.config(text=f"Max compound: {s['max_compound']:.3f}")
        self.clear_chart_frame(self.sent_chart_frame)
        if self.df_daily_sent is not None and not self.df_daily_sent.empty:
            fig = Figure(figsize=(6, 2.5), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(self.df_daily_sent["date"], self.df_daily_sent["avg_compound"])
            ax.set_facecolor("#101620")
            fig.patch.set_facecolor("#050910")
            ax.tick_params(axis="x", labelrotation=45, colors="#E5F0FF")
            ax.tick_params(axis="y", colors="#E5F0FF")
            ax.set_title("Daily average sentiment", color="#E5F0FF")
            ax.grid(alpha=0.2, color="#445")
            self.draw_chart(self.sent_chart_frame, fig)
        tree = self.sent_tree
        for item in tree.get_children():
            tree.delete(item)
        if self.df_sent is not None and not self.df_sent.empty:
            df = (
                self.df_sent[["timestamp", "compound", "text"]]
                .sort_values("timestamp", ascending=False)
                .head(100)
            )
            for _, row in df.iterrows():
                text = row["text"] or ""
                if len(text) > 100:
                    text = text[:97] + "..."
                tree.insert("", tk.END, values=[row["timestamp"], f"{row['compound']:.3f}", text])

    def update_leakage(self):
        self.leak_total.config(text=f"Total images: {self.leak_stats.get('total_images', 0)}")
        self.leak_gps.config(text=f"Images with GPS: {self.leak_stats.get('images_with_gps', 0)}")
        self.leak_text.config(text=f"Images with text: {self.leak_stats.get('images_with_text', 0)}")
        tree = self.leak_tree
        for item in tree.get_children():
            tree.delete(item)
        self.leak_row_map = {}
        for l in self.leaks:
            text = l.text or ""
            if len(text) > 120:
                text = text[:117] + "..."
            row_id = tree.insert(
                "",
                tk.END,
                values=[
                    l.post_id,
                    l.image_filename,
                    "" if l.gps_lat is None else f"{l.gps_lat:.5f}",
                    "" if l.gps_lon is None else f"{l.gps_lon:.5f}",
                    text,
                ],
            )
            self.leak_row_map[row_id] = l
        self.leak_image_label.config(image="", text="No image selected")
        self.leak_text_widget.delete("1.0", tk.END)

    def on_leak_select(self, event):
        selection = self.leak_tree.selection()
        if not selection:
            return
        row_id = selection[0]
        leak = self.leak_row_map.get(row_id)
        if not leak:
            return
        try:
            path = image_path_for(leak.username, leak.image_filename)
            img = Image.open(path)
            img.thumbnail((420, 420))
            self._leak_img_tk = ImageTk.PhotoImage(img)
            self.leak_image_label.config(image=self._leak_img_tk, text="")
        except Exception:
            self.leak_image_label.config(image="", text="Image not found")
        self.leak_text_widget.delete("1.0", tk.END)
        self.leak_text_widget.insert("1.0", leak.text or "")

    def update_raw(self):
        if self.df_posts is None:
            return
        tree = self.raw_tree
        for item in tree.get_children():
            tree.delete(item)
        df = self.df_posts[["post_id", "timestamp", "text", "image_filename"]].sort_values("timestamp")
        for _, row in df.iterrows():
            text = row["text"] or ""
            if len(text) > 80:
                text = text[:77] + "..."
            tree.insert(
                "",
                tk.END,
                values=[row["post_id"], row["timestamp"], text, row.get("image_filename", "")],
            )


def main():
    ensure_directories()
    initialise_database()
    targets = load_targets()
    if not targets:
        messagebox.showerror("Error", "No targets found in targets.json")
        return
    app = OSINTApp(targets)
    app.mainloop()


if __name__ == "__main__":
    main()
