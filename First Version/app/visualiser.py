from __future__ import annotations  # Import necessary module or component

from datetime import date  # Import necessary module or component

import pandas as pd  # Import necessary module or component
import streamlit as st  # Import necessary module or component

from app.config import ensure_directories  # Import necessary module or component
from app.database import initialise_database, save_posts  # Import necessary module or component
from app.scraper import get_posts_for_profile  # Import necessary module or component
from app.targets import load_targets, TargetAccount  # Import necessary module or component
from app.timefilters import last_n_days, full_window, filter_posts, TimeWindow  # Import necessary module or component
from app.timestamp_analyser import (  # Import necessary module or component
    posts_to_dataframe,  # Execute statement or expression
    posting_summary,  # Execute statement or expression
)  # Close bracket/parenthesis
from app.sentiment_analyser import (  # Import necessary module or component
    sentiment_dataframe,  # Execute statement or expression
    daily_sentiment,  # Execute statement or expression
    sentiment_summary,  # Execute statement or expression
)  # Close bracket/parenthesis
from app.leakage_analyser import analyse_image_leaks, leakage_summary  # Import necessary module or component


def choose_target(targets: list[TargetAccount]) -> TargetAccount | None:  # Define function choose_target
    labels = [f"{t.label} ({t.username}, {t.group})" for t in targets]  # Assign value to labels
    choice = st.sidebar.selectbox("Target account", labels)  # Assign value to choice
    for t, label in zip(targets, labels):  # Iterate in a loop
        if label == choice:  # Check conditional statement
            return t  # Return value from function
    return None  # Return value from function


def choose_time_window() -> str:  # Define function choose_time_window
    options = ["All available", "Last 7 days", "Last 30 days", "Custom range"]  # Assign value to options
    choice = st.sidebar.selectbox("Time window", options)  # Assign value to choice
    return choice  # Return value from function


def get_time_window(choice: str, posts_all) -> TimeWindow | None:  # Define function get_time_window
    if choice == "All available":  # Check conditional statement
        return None  # Return value from function
    if choice == "Last 7 days":  # Check conditional statement
        return last_n_days(7)  # Return value from function
    if choice == "Last 30 days":  # Check conditional statement
        return last_n_days(30)  # Return value from function
    today = date.today()  # Assign value to today
    full = full_window(posts_all)  # Assign value to full
    start_default = full.start  # Assign value to start_default
    end_default = full.end if full.end <= today else today  # Assign value to end_default
    start = st.sidebar.date_input("Start date", start_default)  # Assign value to start
    end = st.sidebar.date_input("End date", end_default)  # Assign value to end
    if start and end and start <= end:  # Check conditional statement
        return TimeWindow(start=start, end=end)  # Return value from function
    return full  # Return value from function


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


def leaks_to_df(leaks):  # Define function leaks_to_df
    rows = []  # Assign value to rows
    for l in leaks:  # Iterate in a loop
        rows.append(  # Execute statement or expression
            {  # Execute statement or expression
                "post_id": l.post_id,  # Execute statement or expression
                "image_filename": l.image_filename,  # Execute statement or expression
                "gps_lat": l.gps_lat,  # Execute statement or expression
                "gps_lon": l.gps_lon,  # Execute statement or expression
                "text_snippet": (l.text[:120] + "…") if len(l.text) > 120 else l.text,  # Execute statement or expression
            }  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
    if not rows:  # Check conditional statement
        # Return value from function
        # Return value from function
        return pd.DataFrame(columns=["post_id", "image_filename", "gps_lat", "gps_lon", "text_snippet"])
    return pd.DataFrame(rows)  # Return value from function


def run_app():  # Define function run_app
    ensure_directories()  # Call function ensure_directories
    initialise_database()  # Call function initialise_database
    st.set_page_config(page_title="OSINT Social Media Analysis", layout="wide")  # Close bracket/parenthesis
    st.title("OSINT Social Media Analysis Tool")  # Close bracket/parenthesis
    st.write(  # Execute statement or expression
        # Execute statement or expression
        # Execute statement or expression
        "Select a configured target and time window in the sidebar, then run the analysis to see timeline, sentiment, and image leakage patterns."
    )  # Close bracket/parenthesis
    targets = load_targets()  # Assign value to targets
    if not targets:  # Check conditional statement
        st.error("No targets found in targets.json.")  # Close bracket/parenthesis
        return  # Return value from function
    st.sidebar.header("Analysis controls")  # Close bracket/parenthesis
    target = choose_target(targets)  # Assign value to target
    if target is None:  # Check conditional statement
        st.stop()  # Close bracket/parenthesis
    st.sidebar.write(f"Selected: `{target.username}` ({target.group})")  # Close bracket/parenthesis
    time_choice = choose_time_window()  # Assign value to time_choice
    run_button = st.sidebar.button("Run analysis")  # Assign value to run_button
    if not run_button:  # Check conditional statement
        st.stop()  # Close bracket/parenthesis
    try:  # Start of try block for exception handling
        posts_all = get_posts_for_profile(target.profile_url)  # Assign value to posts_all
    except Exception as e:  # Handle specific exceptions
        st.error(f"Error loading posts: {e}")  # Close bracket/parenthesis
        st.stop()  # Close bracket/parenthesis
    if not posts_all:  # Check conditional statement
        st.warning("No posts loaded for this target.")  # Close bracket/parenthesis
        st.stop()  # Close bracket/parenthesis
    window = get_time_window(time_choice, posts_all)  # Assign value to window
    if window is not None:  # Check conditional statement
        posts = filter_posts(posts_all, window)  # Assign value to posts
        time_label = f"{window.start} → {window.end}"  # Assign value to time_label
    else:  # Execute if preceding conditions are false
        posts = posts_all  # Assign value to posts
        full = full_window(posts_all)  # Assign value to full
        time_label = f"{full.start} → {full.end}"  # Assign value to time_label
    if not posts:  # Check conditional statement
        st.warning("No posts in the selected time window.")  # Close bracket/parenthesis
        st.stop()  # Close bracket/parenthesis
    save_posts(posts)  # Call function save_posts
    df_posts = posts_to_dataframe(posts)  # Assign value to df_posts
    df_sent = sentiment_dataframe(posts)  # Assign value to df_sent
    df_daily_sent = daily_sentiment(df_sent)  # Assign value to df_daily_sent
    leaks = analyse_image_leaks(posts)  # Assign value to leaks
    leak_stats = leakage_summary(leaks)  # Assign value to leak_stats
    st.subheader("Overview")  # Close bracket/parenthesis
    col1, col2, col3 = st.columns(3)  # Close bracket/parenthesis
    stats = posting_summary(df_posts)  # Assign value to stats
    with col1:  # Use context manager
        st.metric("Total posts in window", stats["total_posts"])  # Close bracket/parenthesis
        st.metric("Days covered", stats["days_covered"])  # Close bracket/parenthesis
    with col2:  # Use context manager
        st.metric("Mean posts/day", f"{stats['mean_posts_per_day']:.2f}")  # Close bracket/parenthesis
        st.metric("Median posts/day", f"{stats['median_posts_per_day']:.2f}")  # Close bracket/parenthesis
    with col3:  # Use context manager
        busiest = stats["busiest_hour"]  # Assign value to busiest
        count = stats["busiest_hour_count"]  # Assign value to count
        busiest_label = f"{busiest}:00" if busiest is not None else "-"  # Assign value to busiest_label
        st.metric("Busiest posting hour", busiest_label)  # Close bracket/parenthesis
        st.metric("Posts at busiest hour", count)  # Close bracket/parenthesis
    st.write(f"Time window: **{time_label}**")  # Close bracket/parenthesis
    st.markdown("#### Posts table")
    st.dataframe(  # Execute statement or expression
        df_posts[["timestamp", "text"]]  # Close bracket/parenthesis
        .sort_values("timestamp", ascending=False)  # Close bracket/parenthesis
        .reset_index(drop=True)  # Close bracket/parenthesis
    )  # Close bracket/parenthesis
    tab1, tab2, tab3 = st.tabs(["Temporal patterns", "Sentiment analysis", "Image leakage"])  # Close bracket/parenthesis
    with tab1:  # Use context manager
        st.subheader("Temporal patterns")  # Close bracket/parenthesis
        per_day = posts_per_day_df(df_posts)  # Assign value to per_day
        per_hour = posts_per_hour_df(df_posts)  # Assign value to per_hour
        per_weekday = posts_per_weekday_df(df_posts)  # Assign value to per_weekday
        c1, c2 = st.columns(2)  # Close bracket/parenthesis
        with c1:  # Use context manager
            st.markdown("##### Posts per day")
            if per_day.empty:  # Check conditional statement
                st.info("No data for posts per day.")  # Close bracket/parenthesis
            else:  # Execute if preceding conditions are false
                st.line_chart(per_day.set_index("date")["posts"])  # Close bracket/parenthesis
        with c2:  # Use context manager
            st.markdown("##### Posts by hour of day")
            if per_hour.empty:  # Check conditional statement
                st.info("No data for posts per hour.")  # Close bracket/parenthesis
            else:  # Execute if preceding conditions are false
                st.bar_chart(per_hour.set_index("hour")["posts"])  # Close bracket/parenthesis
        st.markdown("##### Posts by weekday")
        if per_weekday.empty:  # Check conditional statement
            st.info("No data for posts by weekday.")  # Close bracket/parenthesis
        else:  # Execute if preceding conditions are false
            st.bar_chart(per_weekday.set_index("weekday")["posts"])  # Close bracket/parenthesis
    with tab2:  # Use context manager
        st.subheader("Sentiment analysis")  # Close bracket/parenthesis
        if df_sent.empty:  # Check conditional statement
            st.info("No textual posts available in this window.")  # Close bracket/parenthesis
        else:  # Execute if preceding conditions are false
            s_stats = sentiment_summary(df_sent)  # Assign value to s_stats
            c1, c2, c3, c4 = st.columns(4)  # Close bracket/parenthesis
            with c1:  # Use context manager
                st.metric("Mean compound", f"{s_stats['mean_compound']:.3f}")  # Close bracket/parenthesis
            with c2:  # Use context manager
                st.metric("Median compound", f"{s_stats['median_compound']:.3f}")  # Close bracket/parenthesis
            with c3:  # Use context manager
                st.metric("Min compound", f"{s_stats['min_compound']:.3f}")  # Close bracket/parenthesis
            with c4:  # Use context manager
                st.metric("Max compound", f"{s_stats['max_compound']:.3f}")  # Close bracket/parenthesis
            st.markdown("##### Sentiment over time (daily average)")
            if df_daily_sent.empty:  # Check conditional statement
                st.info("No daily sentiment data.")  # Close bracket/parenthesis
            else:  # Execute if preceding conditions are false
                st.line_chart(df_daily_sent.set_index("date")["avg_compound"])  # Close bracket/parenthesis
            st.markdown("##### Sample posts with sentiment")
            sample = (  # Assign value to sample
                df_sent[["timestamp", "compound", "text"]]  # Close bracket/parenthesis
                .sort_values("timestamp", ascending=False)  # Close bracket/parenthesis
                .head(50)  # Close bracket/parenthesis
                .reset_index(drop=True)  # Close bracket/parenthesis
            )  # Close bracket/parenthesis
            st.dataframe(sample)  # Close bracket/parenthesis
    with tab3:  # Use context manager
        st.subheader("Secondary leakage from images")  # Close bracket/parenthesis
        st.write(  # Execute statement or expression
            f"Total images analysed: **{leak_stats['total_images']}**, "  # Execute statement or expression
            f"with GPS: **{leak_stats['images_with_gps']}**, "  # Execute statement or expression
            f"with visible text: **{leak_stats['images_with_text']}**"  # Execute statement or expression
        )  # Close bracket/parenthesis
        df_leaks = leaks_to_df(leaks)  # Assign value to df_leaks
        if df_leaks.empty:  # Check conditional statement
            st.info("No EXIF GPS or OCR text detected in images for this window.")  # Close bracket/parenthesis
        else:  # Execute if preceding conditions are false
            st.markdown("##### Detailed leakage table")
            st.dataframe(df_leaks.head(100))  # Close bracket/parenthesis


if __name__ == "__main__":  # Check conditional statement
    run_app()  # Call function run_app

