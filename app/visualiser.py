from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.config import ensure_directories
from app.database import initialise_database, save_posts
from app.scraper import get_posts_for_profile
from app.targets import load_targets, TargetAccount
from app.timefilters import last_n_days, full_window, filter_posts, TimeWindow
from app.timestamp_analyser import (
    posts_to_dataframe,
    posting_summary,
)
from app.sentiment_analyser import (
    sentiment_dataframe,
    daily_sentiment,
    sentiment_summary,
)
from app.leakage_analyser import analyse_image_leaks, leakage_summary


def choose_target(targets: list[TargetAccount]) -> TargetAccount | None:
    labels = [f"{t.label} ({t.username}, {t.group})" for t in targets]
    choice = st.sidebar.selectbox("Target account", labels)
    for t, label in zip(targets, labels):
        if label == choice:
            return t
    return None


def choose_time_window() -> str:
    options = ["All available", "Last 7 days", "Last 30 days", "Custom range"]
    choice = st.sidebar.selectbox("Time window", options)
    return choice


def get_time_window(choice: str, posts_all) -> TimeWindow | None:
    if choice == "All available":
        return None
    if choice == "Last 7 days":
        return last_n_days(7)
    if choice == "Last 30 days":
        return last_n_days(30)
    today = date.today()
    full = full_window(posts_all)
    start_default = full.start
    end_default = full.end if full.end <= today else today
    start = st.sidebar.date_input("Start date", start_default)
    end = st.sidebar.date_input("End date", end_default)
    if start and end and start <= end:
        return TimeWindow(start=start, end=end)
    return full


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


def leaks_to_df(leaks):
    rows = []
    for l in leaks:
        rows.append(
            {
                "post_id": l.post_id,
                "image_filename": l.image_filename,
                "gps_lat": l.gps_lat,
                "gps_lon": l.gps_lon,
                "text_snippet": (l.text[:120] + "…") if len(l.text) > 120 else l.text,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["post_id", "image_filename", "gps_lat", "gps_lon", "text_snippet"])
    return pd.DataFrame(rows)


def run_app():
    ensure_directories()
    initialise_database()
    st.set_page_config(page_title="OSINT Social Media Analysis", layout="wide")
    st.title("OSINT Social Media Analysis Tool")
    st.write(
        "Select a configured target and time window in the sidebar, then run the analysis to see timeline, sentiment, and image leakage patterns."
    )
    targets = load_targets()
    if not targets:
        st.error("No targets found in targets.json.")
        return
    st.sidebar.header("Analysis controls")
    target = choose_target(targets)
    if target is None:
        st.stop()
    st.sidebar.write(f"Selected: `{target.username}` ({target.group})")
    time_choice = choose_time_window()
    run_button = st.sidebar.button("Run analysis")
    if not run_button:
        st.stop()
    try:
        posts_all = get_posts_for_profile(target.profile_url)
    except Exception as e:
        st.error(f"Error loading posts: {e}")
        st.stop()
    if not posts_all:
        st.warning("No posts loaded for this target.")
        st.stop()
    window = get_time_window(time_choice, posts_all)
    if window is not None:
        posts = filter_posts(posts_all, window)
        time_label = f"{window.start} → {window.end}"
    else:
        posts = posts_all
        full = full_window(posts_all)
        time_label = f"{full.start} → {full.end}"
    if not posts:
        st.warning("No posts in the selected time window.")
        st.stop()
    save_posts(posts)
    df_posts = posts_to_dataframe(posts)
    df_sent = sentiment_dataframe(posts)
    df_daily_sent = daily_sentiment(df_sent)
    leaks = analyse_image_leaks(posts)
    leak_stats = leakage_summary(leaks)
    st.subheader("Overview")
    col1, col2, col3 = st.columns(3)
    stats = posting_summary(df_posts)
    with col1:
        st.metric("Total posts in window", stats["total_posts"])
        st.metric("Days covered", stats["days_covered"])
    with col2:
        st.metric("Mean posts/day", f"{stats['mean_posts_per_day']:.2f}")
        st.metric("Median posts/day", f"{stats['median_posts_per_day']:.2f}")
    with col3:
        busiest = stats["busiest_hour"]
        count = stats["busiest_hour_count"]
        busiest_label = f"{busiest}:00" if busiest is not None else "-"
        st.metric("Busiest posting hour", busiest_label)
        st.metric("Posts at busiest hour", count)
    st.write(f"Time window: **{time_label}**")
    st.markdown("#### Posts table")
    st.dataframe(
        df_posts[["timestamp", "text"]]
        .sort_values("timestamp", ascending=False)
        .reset_index(drop=True)
    )
    tab1, tab2, tab3 = st.tabs(["Temporal patterns", "Sentiment analysis", "Image leakage"])
    with tab1:
        st.subheader("Temporal patterns")
        per_day = posts_per_day_df(df_posts)
        per_hour = posts_per_hour_df(df_posts)
        per_weekday = posts_per_weekday_df(df_posts)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Posts per day")
            if per_day.empty:
                st.info("No data for posts per day.")
            else:
                st.line_chart(per_day.set_index("date")["posts"])
        with c2:
            st.markdown("##### Posts by hour of day")
            if per_hour.empty:
                st.info("No data for posts per hour.")
            else:
                st.bar_chart(per_hour.set_index("hour")["posts"])
        st.markdown("##### Posts by weekday")
        if per_weekday.empty:
            st.info("No data for posts by weekday.")
        else:
            st.bar_chart(per_weekday.set_index("weekday")["posts"])
    with tab2:
        st.subheader("Sentiment analysis")
        if df_sent.empty:
            st.info("No textual posts available in this window.")
        else:
            s_stats = sentiment_summary(df_sent)
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Mean compound", f"{s_stats['mean_compound']:.3f}")
            with c2:
                st.metric("Median compound", f"{s_stats['median_compound']:.3f}")
            with c3:
                st.metric("Min compound", f"{s_stats['min_compound']:.3f}")
            with c4:
                st.metric("Max compound", f"{s_stats['max_compound']:.3f}")
            st.markdown("##### Sentiment over time (daily average)")
            if df_daily_sent.empty:
                st.info("No daily sentiment data.")
            else:
                st.line_chart(df_daily_sent.set_index("date")["avg_compound"])
            st.markdown("##### Sample posts with sentiment")
            sample = (
                df_sent[["timestamp", "compound", "text"]]
                .sort_values("timestamp", ascending=False)
                .head(50)
                .reset_index(drop=True)
            )
            st.dataframe(sample)
    with tab3:
        st.subheader("Secondary leakage from images")
        st.write(
            f"Total images analysed: **{leak_stats['total_images']}**, "
            f"with GPS: **{leak_stats['images_with_gps']}**, "
            f"with visible text: **{leak_stats['images_with_text']}**"
        )
        df_leaks = leaks_to_df(leaks)
        if df_leaks.empty:
            st.info("No EXIF GPS or OCR text detected in images for this window.")
        else:
            st.markdown("##### Detailed leakage table")
            st.dataframe(df_leaks.head(100))


if __name__ == "__main__":
    run_app()

