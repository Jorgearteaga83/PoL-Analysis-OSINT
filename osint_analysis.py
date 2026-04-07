import re  # Import necessary module or component
import logging  # Import necessary module or component
from typing import Optional, Tuple  # Import necessary module or component
from pathlib import Path  # Import necessary module or component
import pandas as pd  # Import necessary module or component
import networkx as nx  # Import necessary module or component
import matplotlib  # Import necessary module or component
matplotlib.use('Agg')  # Close bracket/parenthesis
import matplotlib.pyplot as plt  # Import necessary module or component
import reverse_geocoder as rg  # Import necessary module or component
from timezonefinder import TimezoneFinder  # Import necessary module or component

logger = logging.getLogger(__name__)  # Assign value to logger
tf = TimezoneFinder()  # Assign value to tf

# Define function infer_location_data
# Define function infer_location_data
def infer_location_data(lat: Optional[float], lon: Optional[float], location_string: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if lat is not None and lon is not None:  # Check conditional statement
        try:  # Start of try block for exception handling
            results = rg.search((lat, lon), mode=1)  # Assign value to results
            if results:  # Check conditional statement
                location = results[0]  # Assign value to location
                city = location.get('name')  # Assign value to city
                country = location.get('country')  # Assign value to country
                timezone = tf.timezone_at(lng=lon, lat=lat)  # Assign value to timezone
                return city, country, timezone  # Return value from function
        except Exception as e:  # Handle specific exceptions
            logger.error(f"Geocoding failed for {lat},{lon}: {e}")  # Close bracket/parenthesis
            return None, None, None  # Return value from function
    if location_string:  # Check conditional statement
        return location_string, None, None  # Return value from function
    return None, None, None  # Return value from function

def categorize_location(df: pd.DataFrame) -> pd.DataFrame:  # Define function categorize_location
    df_out = df.copy()  # Assign value to df_out
    lexicons = {  # Assign value to lexicons
        "Work": ["office", "grind", "meeting", "work", "job", "desk", "colleagues"],  # Execute statement or expression
        "Home": ["couch", "living room", "neighborhood", "home", "relaxing", "chilling", "sofa"],  # Execute statement or expression
        "Travel": ["airport", "vacation", "explore", "travel", "holiday", "sightseeing", "tourist"]  # Close bracket/parenthesis
    }  # Close bracket/parenthesis
    df_out['location_category'] = "Uncategorized"  # Assign value to df_out['location_category']
    for category, keywords in lexicons.items():  # Iterate in a loop
        pattern = '|'.join(keywords)  # Assign value to pattern
        mask = df_out['caption'].str.contains(pattern, case=False, na=False)  # Assign value to mask
        df_out.loc[mask, 'location_category'] = f"Assumed: {category}"  # Execute statement or expression
    return df_out  # Return value from function

def generate_sna_graph(df: pd.DataFrame, target_user: str, output_dir: Path) -> Optional[Path]:  # Define function generate_sna_graph
    if 'associated_entities' not in df.columns:  # Check conditional statement
        return None  # Return value from function

    G = nx.Graph()  # Assign value to G
    G.add_node(target_user, size=50, color='red')  # Close bracket/parenthesis
    edge_weights = {}  # Assign value to edge_weights

    for _, row in df.iterrows():  # Iterate in a loop
        entities = row['associated_entities']  # Assign value to entities
        if not isinstance(entities, list):  # Check conditional statement
            continue  # Skip to next loop iteration
        for entity in entities:  # Iterate in a loop
            if entity == target_user:  # Check conditional statement
                continue  # Skip to next loop iteration
            if not G.has_node(entity):  # Check conditional statement
                G.add_node(entity, size=10, color='skyblue')  # Close bracket/parenthesis
            edge = tuple(sorted((target_user, entity)))  # Assign value to edge
            edge_weights[edge] = edge_weights.get(edge, 0) + 1  # Assign value to edge_weights[edge]

    for edge, weight in edge_weights.items():  # Iterate in a loop
        G.add_edge(edge[0], edge[1], weight=weight)  # Close bracket/parenthesis

    if len(G.nodes) <= 1:  # Check conditional statement
        return None  # Return value from function

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
    except IOError as e:  # Handle specific exceptions
        logger.error(f"Failed to save SNA graph: {e}")  # Close bracket/parenthesis
        sna_path = None  # Assign value to sna_path
    finally:  # Execute cleanup code regardless of exceptions
        plt.close()  # Close bracket/parenthesis
    return sna_path  # Return value from function

class SentimentEngine:  # Define class SentimentEngine
    def __init__(self):  # Define function __init__
        self.mode = "fallback"  # Assign value to self.mode
        self.analyzer = None  # Assign value to self.analyzer
        try:  # Start of try block for exception handling
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # Import necessary module or component
            self.analyzer = SentimentIntensityAnalyzer()  # Assign value to self.analyzer
            self.mode = "vader"  # Assign value to self.mode
        except ImportError:  # Handle specific exceptions
            logger.warning("vaderSentiment not found. Using fallback lexicon.")  # Close bracket/parenthesis
            
        # Assign value to self.pos_words
        # Assign value to self.pos_words
        self.pos_words = {"good", "great", "amazing", "love", "happy", "nice", "excellent", "fun", "win"}
        # Assign value to self.neg_words
        # Assign value to self.neg_words
        self.neg_words = {"bad", "terrible", "hate", "sad", "angry", "awful", "worst", "fail", "pain"}

    def score(self, text: str) -> float:  # Define function score
        text = (text or "").strip()  # Assign value to text
        if not text:  # Check conditional statement
            return 0.0  # Return value from function
        if self.mode == "vader" and self.analyzer is not None:  # Check conditional statement
            return float(self.analyzer.polarity_scores(text).get("compound", 0.0))  # Return value from function
        
        words = re.findall(r"[A-Za-z']+", text.lower())  # Assign value to words
        if not words:  # Check conditional statement
            return 0.0  # Return value from function
        pos = sum(1 for w in words if w in self.pos_words)  # Assign value to pos
        neg = sum(1 for w in words if w in self.neg_words)  # Assign value to neg
        raw = pos - neg  # Assign value to raw
        return max(-1.0, min(1.0, raw / max(5, len(words) / 2)))  # Return value from function
