import re
import logging
from typing import Optional, Tuple
from pathlib import Path
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import reverse_geocoder as rg
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)
tf = TimezoneFinder()

def infer_location_data(lat: Optional[float], lon: Optional[float], location_string: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Infers city, country, and timezone based on latitude and longitude using reverse geocoding.

    Args:
        lat (Optional[float]): The latitude coordinate.
        lon (Optional[float]): The longitude coordinate.
        location_string (Optional[str]): A fallback location string if coordinates are unavailable.

    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: A tuple containing (city, country, timezone).
    """
    if lat is not None and lon is not None:
        try:
            results = rg.search((lat, lon), mode=1)
            if results:
                location = results[0]
                city = location.get('name')
                country = location.get('country')
                timezone = tf.timezone_at(lng=lon, lat=lat)
                return city, country, timezone
        except Exception as e:
            logger.error(f"Geocoding failed for {lat},{lon}: {e}")
            return None, None, None
    if location_string:
        return location_string, None, None
    return None, None, None

def categorize_location(df: pd.DataFrame) -> pd.DataFrame:
    """
    Categorizes the location of posts into assumed categories (Work, Home, Travel) based on caption keywords.

    Args:
        df (pd.DataFrame): The dataframe containing post data with captions.

    Returns:
        pd.DataFrame: The dataframe with an added 'location_category' column.
    """
    df_out = df.copy()
    lexicons = {
        "Work": ["office", "grind", "meeting", "work", "job", "desk", "colleagues"],
        "Home": ["couch", "living room", "neighborhood", "home", "relaxing", "chilling", "sofa"],
        "Travel": ["airport", "vacation", "explore", "travel", "holiday", "sightseeing", "tourist"]
    }
    df_out['location_category'] = "Uncategorized"
    for category, keywords in lexicons.items():
        pattern = '|'.join(keywords)
        mask = df_out['caption'].str.contains(pattern, case=False, na=False)
        df_out.loc[mask, 'location_category'] = f"Assumed: {category}"
    return df_out

def generate_sna_graph(df: pd.DataFrame, target_user: str, output_dir: Path) -> Optional[Path]:
    """
    Generates and saves a Social Network Analysis (SNA) graph of associated entities.

    Args:
        df (pd.DataFrame): The dataframe containing associated entities data.
        target_user (str): The main user to map connections for.
        output_dir (Path): The directory to save the output graph image.

    Returns:
        Optional[Path]: The file path to the saved SNA graph image, or None if it fails or there are insufficient nodes.
    """
    if 'associated_entities' not in df.columns:
        return None

    G = nx.Graph()
    G.add_node(target_user, size=50, color='red')
    edge_weights = {}

    for _, row in df.iterrows():
        entities = row['associated_entities']
        if not isinstance(entities, list):
            continue
        for entity in entities:
            if entity == target_user:
                continue
            if not G.has_node(entity):
                G.add_node(entity, size=10, color='skyblue')
            edge = tuple(sorted((target_user, entity)))
            edge_weights[edge] = edge_weights.get(edge, 0) + 1

    for edge, weight in edge_weights.items():
        G.add_edge(edge[0], edge[1], weight=weight)

    if len(G.nodes) <= 1:
        return None

    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    node_sizes = [d['size']*20 for n, d in G.nodes(data=True)]
    node_colors = [d['color'] for n, d in G.nodes(data=True)]
    
    nx.draw(G, pos, with_labels=True, node_size=node_sizes, node_color=node_colors, font_size=10, font_weight='bold')
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    plt.title(f"Social Network Analysis for {target_user}")
    
    sna_path = output_dir / f"sna_{target_user}.png"
    try:
        plt.savefig(sna_path, format="PNG", bbox_inches="tight")
    except IOError as e:
        logger.error(f"Failed to save SNA graph: {e}")
        sna_path = None
    finally:
        plt.close()
    return sna_path

class SentimentEngine:
    def __init__(self):
        """
        Initializes the SentimentEngine, prioritizing vaderSentiment and falling back to a basic lexicon.

        Args:
            None

        Returns:
            None
        """
        self.mode = "fallback"
        self.analyzer = None
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.analyzer = SentimentIntensityAnalyzer()
            self.mode = "vader"
        except ImportError:
            logger.warning("vaderSentiment not found. Using fallback lexicon.")
            
        self.pos_words = {"good", "great", "amazing", "love", "happy", "nice", "excellent", "fun", "win"}
        self.neg_words = {"bad", "terrible", "hate", "sad", "angry", "awful", "worst", "fail", "disgusting", "pain"}

    def score(self, text: str) -> float:
        """
        Calculates the sentiment score of a given text string.

        Args:
            text (str): The text content to analyze.

        Returns:
            float: The sentiment score, ranging from -1.0 (most negative) to 1.0 (most positive).
        """
        text = (text or "").strip()
        if not text:
            return 0.0
        if self.mode == "vader" and self.analyzer is not None:
            return float(self.analyzer.polarity_scores(text).get("compound", 0.0))
        
        words = re.findall(r"[A-Za-z']+", text.lower())
        if not words:
            return 0.0
        pos = sum(1 for w in words if w in self.pos_words)
        neg = sum(1 for w in words if w in self.neg_words)
        raw = pos - neg
        return max(-1.0, min(1.0, raw / max(5, len(words) / 2)))
