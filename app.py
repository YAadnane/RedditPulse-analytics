import streamlit as st
import subprocess
import pandas as pd
import os
import sys
 # import inutilisé supprimé
import shutil
import io
import altair as alt
import re
from collections import Counter
import datetime
import matplotlib.pyplot as plt
import tempfile

try:
    from fpdf import FPDF

    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
except Exception as e:
    # Catch other errors like the python version support one
    print(f"Warning: Gemini module error: {e}")
    GEMINI_AVAILABLE = False

# Optional improved PDF engines availability
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    import pdfkit

    PDFKIT_IMPORTED = True
except Exception:
    PDFKIT_IMPORTED = False

WKHTMLTOPDF_AVAILABLE = shutil.which("wkhtmltopdf") is not None

# Configuration
st.set_page_config(page_title="RedditPulse Analytics", layout="wide", page_icon="📊")

# Custom CSS for better styling
st.markdown(
    """
<style>
    /* Main Layout */
    .stApp {
        background-color: #0E1113; /* Dark Reddit Background */
        color: #D7DADC;
    }
    
    /* Maximize Content Width */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 95rem;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'IBM Plex Sans', sans-serif;
        color: #D7DADC !important;
    }
    h1 {
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #FF4500, #FF8717);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1A1A1B;
        border-right: 1px solid #343536;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #D7DADC !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #FF4500 !important;
    }
    .stMetric {
        background-color: #1A1A1B;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #343536;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stMetric label {
        color: #818384 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1A1A1B;
        padding: 10px 10px;
        border-radius: 12px;
        border: 1px solid #343536;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #818384;
        border: none;
        font-weight: 600;
        font-size: 14px;
        flex-grow: 1;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #D7DADC;
        background-color: rgba(255, 255, 255, 0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF4500 !important;
        color: white !important;
        box-shadow: 0 2px 10px rgba(255, 69, 0, 0.3);
        transform: scale(1.02);
    }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(90deg, #FF4500 0%, #FF8717 100%);
        color: white;
        border: none;
        border-radius: 20px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 69, 0, 0.3);
        color: white !important;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #343536;
        border-radius: 5px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1A1A1B;
        color: #D7DADC;
        border-radius: 5px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📊 RedditPulse Analytics")


# --- DOCKER PATH DETECTION ---
def get_docker_cmd():
    """Trouve l'exécutable docker même s'il n'est pas dans le PATH."""
    docker_path = shutil.which("docker")
    if docker_path:
        return "docker"

    # Chemins communs Windows
    common_paths = [
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        r"C:\Program Files\Docker\Docker\resources\docker.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


DOCKER_CMD = get_docker_cmd()

if not DOCKER_CMD:
    st.error(
        "❌ Docker n'est pas détecté ! Veuillez installer Docker Desktop ou l'ajouter au PATH."
    )
    st.stop()

# --- SESSION STATE INIT ---
if "extraction_done" not in st.session_state:
    st.session_state["extraction_done"] = False
if "spark_done" not in st.session_state:
    st.session_state["spark_done"] = False
if "spark_stdout" not in st.session_state:
    st.session_state["spark_stdout"] = ""
if "spark_stderr" not in st.session_state:
    st.session_state["spark_stderr"] = ""


# --- HELPER FUNCTION (Global) ---
def clean_text_for_pdf(text):
    """Nettoie le texte pour FPDF (latin-1)"""
    if not isinstance(text, str):
        return str(text)
    # Remplace les caractères non-latin-1 par ?
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_pdf_report(df_p, df_s, df_c):
    """Génère un rapport PDF complet avec tous les graphiques"""
    if not FPDF_AVAILABLE:
        return None

    class PDF(FPDF):
        def __init__(self):
            super().__init__(orientation="P", unit="mm", format="A4")

        def header(self):
            self.set_font("Arial", "B", 15)
            self.cell(0, 10, "Rapport d'Analyse RedditPulse", 0, 1, "C")
            self.ln(5)
            self.set_font("Arial", "I", 10)
            self.cell(
                0,
                10,
                f'Genere le {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}',
                0,
                1,
                "C",
            )
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    pdf = PDF()
    pdf.add_page()

    # --- 1. ANALYSE GLOBALE ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Vue d'Ensemble du Marche", 0, 1)
    pdf.ln(5)

    # KPI Table
    pdf.set_font("Arial", "", 11)
    kpis = [
        f"Total Posts: {len(df_p)}",
        f"Score Moyen: {df_p['score'].mean():.1f}",
        f"Sentiment Moyen: {df_p['sentiment'].mean():.3f}",
    ]
    for k in kpis:
        pdf.cell(0, 8, k, 0, 1)
    pdf.ln(5)

    # Chart 1: Sentiment par Subreddit (Bar)
    if df_s is not None:
        try:
            plt.figure(figsize=(10, 4))
            col_sent = (
                "avg_sentiment" if "avg_sentiment" in df_s.columns else df_s.columns[1]
            )
            plt.bar(df_s["subreddit"], df_s[col_sent], color="skyblue")
            plt.title("Sentiment Moyen par Marque")
            plt.xlabel("Marque")
            plt.ylabel("Sentiment")
            plt.grid(axis="y", linestyle="--", alpha=0.7)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                plt.savefig(tmpfile.name, bbox_inches="tight")
                plt.close()
                pdf.image(tmpfile.name, x=10, w=190)
                os.unlink(tmpfile.name)
        except Exception as e:
            pdf.cell(0, 10, f"Erreur graphique 1: {str(e)}", 0, 1)

    pdf.ln(5)

    # Chart 2: Volume Temporel Global (Line)
    if "date" in df_p.columns:
        try:
            plt.figure(figsize=(10, 4))
            # Group by date and subreddit
            pivot_df = (
                df_p.groupby([df_p["date"].dt.date, "subreddit"])
                .size()
                .unstack(fill_value=0)
            )
            pivot_df.plot(kind="line", marker="o")
            plt.title("Evolution du Volume par Marque")
            plt.xlabel("Date")
            plt.ylabel("Nombre de Posts")
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend(title="Marque")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                plt.savefig(tmpfile.name, bbox_inches="tight")
                plt.close()
                pdf.image(tmpfile.name, x=10, w=190)
                os.unlink(tmpfile.name)
        except Exception as e:
            pdf.cell(0, 10, f"Erreur graphique 2: {str(e)}", 0, 1)

    pdf.add_page()

    # Chart 3: Distribution Sentiments (Boxplot)
    try:
        plt.figure(figsize=(10, 5))
        df_p.boxplot(column="sentiment", by="subreddit", grid=True, patch_artist=True)
        plt.title("Distribution des Sentiments (Dispersion)")
        plt.suptitle("")  # Supprime le titre automatique de pandas
        plt.xlabel("Marque")
        plt.ylabel("Sentiment")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            plt.savefig(tmpfile.name, bbox_inches="tight")
            plt.close()
            pdf.image(tmpfile.name, x=10, w=190)
            os.unlink(tmpfile.name)
    except Exception as e:
        pdf.cell(0, 10, f"Erreur graphique 3: {str(e)}", 0, 1)

    pdf.ln(5)

    # Chart 4: Sentiment vs Score (Scatter)
    try:
        plt.figure(figsize=(10, 5))
        groups = df_p.groupby("subreddit")
        for name, group in groups:
            plt.scatter(group["sentiment"], group["score"], label=name, alpha=0.6)
        plt.title("Relation Sentiment vs Popularite (Score)")
        plt.xlabel("Sentiment")
        plt.ylabel("Score")
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.5)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            plt.savefig(tmpfile.name, bbox_inches="tight")
            plt.close()
            pdf.image(tmpfile.name, x=10, w=190)
            os.unlink(tmpfile.name)
    except Exception as e:
        pdf.cell(0, 10, f"Erreur graphique 4: {str(e)}", 0, 1)

    # --- 2. ANALYSE DETAILLEE ---
    subreddits = df_p["subreddit"].unique()

    for sub in subreddits:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"2. Analyse Detaillee : r/{sub}", 0, 1)
        pdf.ln(5)

        sub_df = df_p[df_p["subreddit"] == sub]

        # KPI Local
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Indicateurs Clés", 0, 1)
        pdf.set_font("Arial", "", 11)

        pos_ratio = (sub_df["sentiment"] > 0).mean() * 100
        stats_txt = f"Volume: {len(sub_df)} posts | Score Max: {sub_df['score'].max()} | Positivite: {pos_ratio:.1f}%"
        pdf.cell(0, 8, stats_txt, 0, 1)
        pdf.ln(5)

        # Chart 5: Evolution Volume & Sentiment (Subplot)
        if "date" in sub_df.columns:
            try:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

                # Vol
                daily_counts = sub_df.groupby(
                    sub_df["date"].dt.hour
                ).size()  # Par heure pour voir du détail
                if daily_counts.empty:  # Fallback jour
                    daily_counts = sub_df.groupby(sub_df["date"].dt.date).size()

                daily_counts.plot(kind="line", marker="o", color="orange", ax=ax1)
                ax1.set_title(f"Volume (Posts)")
                ax1.grid(True)

                # Sent
                daily_sent = sub_df.groupby(sub_df["date"].dt.hour)["sentiment"].mean()
                if daily_sent.empty:
                    daily_sent = sub_df.groupby(sub_df["date"].dt.date)[
                        "sentiment"
                    ].mean()

                daily_sent.plot(kind="line", marker="o", color="teal", ax=ax2)
                ax2.set_title(f"Sentiment Moyen")
                ax2.grid(True)

                plt.tight_layout()

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png"
                ) as tmpfile:
                    plt.savefig(tmpfile.name, bbox_inches="tight")
                    plt.close()
                    pdf.image(tmpfile.name, x=10, w=190)
                    os.unlink(tmpfile.name)
            except Exception as e:
                pdf.cell(0, 10, f"Erreur graphiques temporels: {str(e)}", 0, 1)

        pdf.ln(5)

        # Chart 6: Pie Chart Sentiment
        try:
            pos = (sub_df["sentiment"] > 0).sum()
            neg = (sub_df["sentiment"] < 0).sum()
            neu = (sub_df["sentiment"] == 0).sum()

            plt.figure(figsize=(6, 4))
            plt.pie(
                [pos, neg, neu],
                labels=["Positif", "Negatif", "Neutre"],
                autopct="%1.1f%%",
                colors=["#28a745", "#dc3545", "#6c757d"],
            )
            plt.title("Repartition des Avis")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                plt.savefig(tmpfile.name, bbox_inches="tight")
                plt.close()
                pdf.image(tmpfile.name, x=50, w=100)  # Centré plus petit
                os.unlink(tmpfile.name)
        except Exception as e:
            pdf.cell(0, 10, f"Erreur Pie Chart: {str(e)}", 0, 1)

        pdf.ln(5)

        # Chart 7: Top Mots (Barh)
        try:
            all_text = " ".join(
                sub_df["title"].astype(str)
                + " "
                + sub_df["body"].fillna("").astype(str)
            ).lower()
            words = re.findall(r"\b\w+\b", all_text)
            STOPWORDS = set(
                [
                    "the",
                    "a",
                    "an",
                    "in",
                    "on",
                    "at",
                    "for",
                    "to",
                    "of",
                    "is",
                    "are",
                    "was",
                    "were",
                    "be",
                    "been",
                    "and",
                    "or",
                    "but",
                    "if",
                    "then",
                    "else",
                    "when",
                    "where",
                    "why",
                    "how",
                    "all",
                    "any",
                    "both",
                    "each",
                    "few",
                    "more",
                    "most",
                    "other",
                    "some",
                    "such",
                    "no",
                    "nor",
                    "not",
                    "only",
                    "own",
                    "same",
                    "so",
                    "than",
                    "too",
                    "very",
                    "s",
                    "t",
                    "can",
                    "will",
                    "just",
                    "don",
                    "should",
                    "now",
                    "d",
                    "ll",
                    "m",
                    "o",
                    "re",
                    "ve",
                    "y",
                    "ain",
                    "aren",
                    "couldn",
                    "didn",
                    "doesn",
                    "hadn",
                    "hasn",
                    "haven",
                    "isn",
                    "ma",
                    "mightn",
                    "mustn",
                    "needn",
                    "shan",
                    "shouldn",
                    "wasn",
                    "weren",
                    "won",
                    "wouldn",
                    "i",
                    "me",
                    "my",
                    "myself",
                    "we",
                    "our",
                    "ours",
                    "ourselves",
                    "you",
                    "your",
                    "yours",
                    "yourself",
                    "yourselves",
                    "he",
                    "him",
                    "his",
                    "himself",
                    "she",
                    "her",
                    "hers",
                    "herself",
                    "it",
                    "its",
                    "itself",
                    "they",
                    "them",
                    "their",
                    "theirs",
                    "themselves",
                    "what",
                    "which",
                    "who",
                    "whom",
                    "this",
                    "that",
                    "these",
                    "those",
                    "le",
                    "la",
                    "les",
                    "de",
                    "des",
                    "du",
                    "un",
                    "une",
                    "et",
                    "est",
                    "pour",
                    "en",
                    "que",
                    "qui",
                    "dans",
                    "sur",
                    "pas",
                    "plus",
                    "par",
                    "avec",
                    "ce",
                    "ces",
                    "cette",
                    "ont",
                    "il",
                    "ils",
                    "elle",
                    "elles",
                    "nous",
                    "vous",
                    "je",
                    "tu",
                    "mon",
                    "ton",
                    "son",
                    "ma",
                    "ta",
                    "sa",
                    "mes",
                    "tes",
                    "ses",
                    "notre",
                    "votre",
                    "leur",
                    "nos",
                    "vos",
                    "leurs",
                    "aux",
                    "ou",
                    "où",
                    "donc",
                    "or",
                    "ni",
                    "car",
                    "mais",
                    "http",
                    "https",
                    "com",
                    "www",
                    "reddit",
                    "removed",
                    "deleted",
                ]
            )
            filtered_words = [w for w in words if w not in STOPWORDS and len(w) > 3]
            word_counts = Counter(filtered_words).most_common(15)

            if word_counts:
                words_df = pd.DataFrame(word_counts, columns=["Mot", "Freq"])
                plt.figure(figsize=(10, 5))
                plt.barh(words_df["Mot"], words_df["Freq"], color="cornflowerblue")
                plt.title("Top 15 Mots Cles")
                plt.gca().invert_yaxis()

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png"
                ) as tmpfile:
                    plt.savefig(tmpfile.name, bbox_inches="tight")
                    plt.close()
                    pdf.image(tmpfile.name, x=10, w=190)
                    os.unlink(tmpfile.name)
        except Exception as e:
            pdf.cell(0, 10, f"Erreur Word Cloud: {str(e)}", 0, 1)

        pdf.add_page()

        # Top Posts Table
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Top 5 Posts Populaires", 0, 1)
        pdf.set_font("Arial", "", 9)

        top_posts = sub_df.sort_values(by="score", ascending=False).head(5)

        # Header
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(140, 8, "Titre", 1, 0, "C", 1)
        pdf.cell(25, 8, "Score", 1, 0, "C", 1)
        pdf.cell(25, 8, "Sentiment", 1, 1, "C", 1)

        for _, row in top_posts.iterrows():
            title = (
                clean_text_for_pdf(row["title"])[:75] + "..."
                if len(row["title"]) > 75
                else clean_text_for_pdf(row["title"])
            )
            pdf.cell(140, 8, title, 1)
            pdf.cell(25, 8, str(row["score"]), 1, 0, "C")
            pdf.cell(25, 8, f"{row['sentiment']:.2f}", 1, 1, "C")

    return pdf.output(dest="S").encode("latin-1")


def generate_gemini_pdf(chat_history):
    """Génère un PDF A4 portrait contenant l'historique de chat Gemini."""
    if not FPDF_AVAILABLE:
        return None

    class PDFGem(FPDF):
        def __init__(self):
            super().__init__(orientation="P", unit="mm", format="A4")

        def header(self):
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, "Historique de Conversation - Gemini", 0, 1, "C")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    pdf = PDFGem()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "", 11)

    if not chat_history:
        pdf.cell(0, 8, "Aucun message disponible.", 0, 1)
        return pdf.output(dest="S").encode("latin-1")

    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        content = clean_text_for_pdf(content)

        if role == "user":
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, "Utilisateur:", 0, 1)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, content)
            pdf.ln(3)
        else:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, "Assistant (Gemini):", 0, 1)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, content)
            pdf.ln(4)

    return pdf.output(dest="S").encode("latin-1")


def get_postgres_data(query):
    """Exécute une requête SQL via docker exec et retourne un DataFrame."""
    try:
        # On utilise COPY ... TO STDOUT WITH CSV HEADER pour récupérer les données proprement
        cmd = [
            DOCKER_CMD,
            "exec",
            "postgres_db",
            "psql",
            "-U",
            "admin",
            "-d",
            "reddit_db",
            "-c",
            f"COPY ({query}) TO STDOUT WITH CSV HEADER",
        ]
        # Ajout de encoding='utf-8' pour gérer les émojis et caractères spéciaux sur Windows
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if res.returncode == 0:
            if not res.stdout or not res.stdout.strip():
                return None
            return pd.read_csv(io.StringIO(res.stdout))
        else:
            # On ignore les erreurs si la table n'existe pas encore (cas normal au début)
            if "does not exist" not in res.stderr:
                st.error(f"Erreur SQL : {res.stderr}")
            return None
    except Exception as e:
        st.error(f"Erreur Python : {e}")
        return None


def generate_pdf_report_reportlab(df_p, df_s, df_c):
    """Générateur minimal PDF via reportlab (UTF-8 friendly)."""
    if not REPORTLAB_AVAILABLE:
        return None

    import io
    # import inutilisé supprimé

    buffer = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    # Cover
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2.0, height - 100, "RedditPulse - Rapport d'Analyse")
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        width / 2.0,
        height - 120,
        f"Généré le {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    c.showPage()

    # Résumé exécutif
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 80, "Résumé Exécutif")
    c.setFont("Helvetica", 11)
    y = height - 110
    try:
        total_posts = len(df_p) if df_p is not None else 0
        avg_score = (
            f"{df_p['score'].mean():.1f}"
            if (df_p is not None and "score" in df_p.columns)
            else "N/A"
        )
        avg_sent = (
            f"{df_p['sentiment'].mean():.3f}"
            if (df_p is not None and "sentiment" in df_p.columns)
            else "N/A"
        )
        lines = [
            f"Total Posts: {total_posts}",
            f"Score Moyen: {avg_score}",
            f"Sentiment Moyen: {avg_sent}",
        ]
    except Exception:
        lines = ["Aucune statistique disponible"]

    for ln in lines:
        c.drawString(50, y, f"- {ln}")
        y -= 18

    c.showPage()

    # Small plot: sentiment histogram (matplotlib -> image)
    if df_p is not None and "sentiment" in df_p.columns:
        try:
            plt.figure(figsize=(8, 3))
            plt.hist(df_p["sentiment"].dropna(), bins=20, color="#4C72B0")
            plt.title("Distribution des sentiments")
            plt.xlabel("Sentiment")
            plt.ylabel("Nombre")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                plt.savefig(tmp.name, bbox_inches="tight", dpi=150)
                plt.close()
                img = ImageReader(tmp.name)
                iw, ih = img.getSize()
                aspect = ih / float(iw)
                draw_w = width - 80
                draw_h = draw_w * aspect
                c.drawImage(img, 40, height - 150 - draw_h, width=draw_w, height=draw_h)
                os.unlink(tmp.name)
        except Exception as e:
            c.drawString(40, height - 150, f"Erreur génération graphique: {e}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_report_html(df_p, df_s, df_c):
    """Générateur HTML->PDF minimal via pdfkit (wkhtmltopdf)."""
    if not (PDFKIT_IMPORTED and WKHTMLTOPDF_AVAILABLE):
        return None

    # Build simple HTML
    html = f"""
    <html>
    <head>
      <meta charset='utf-8'/>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #FF4500; }}
        .kpi {{ margin-bottom: 8px; }}
      </style>
    </head>
    <body>
      <h1>RedditPulse - Rapport d'Analyse</h1>
      <p>Généré le {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
      <h2>Résumé</h2>
      <div class='kpi'>Total Posts: {len(df_p) if df_p is not None else 0}</div>
      <div class='kpi'>Score Moyen: {df_p['score'].mean():.1f if (df_p is not None and 'score' in df_p.columns) else 'N/A'}</div>
      <div class='kpi'>Sentiment Moyen: {df_p['sentiment'].mean():.3f if (df_p is not None and 'sentiment' in df_p.columns) else 'N/A'}</div>
    </body>
    </html>
    """

    # pdfkit returns bytes when output_path=False
    config = None
    try:
        if PDFKIT_IMPORTED:
            if WKHTMLTOPDF_AVAILABLE:
                config = pdfkit.configuration(wkhtmltopdf=shutil.which("wkhtmltopdf"))
            return pdfkit.from_string(html, False, configuration=config)
    except Exception as e:
        raise

    return None


# --- SIDEBAR ---
st.sidebar.header("Configuration")
subreddits = st.sidebar.text_input("Subreddits", "datascience,python")
limit = st.sidebar.number_input("Limite Posts", min_value=1, value=100)
comments_limit = st.sidebar.number_input(
    "Limite Commentaires/Post", min_value=0, value=5
)

st.sidebar.markdown("---")
st.sidebar.header("Maintenance")
if st.sidebar.button("🗑️ Vider HDFS & BD"):
    with st.sidebar.status("Nettoyage en cours...") as status:
        # 1. Vider HDFS
        st.write("Suppression HDFS...")
        subprocess.run(
            [
                DOCKER_CMD,
                "exec",
                "namenode",
                "hdfs",
                "dfs",
                "-rm",
                "-r",
                "-f",
                "/reddit_data",
            ]
        )

        # 2. Vider PostgreSQL
        st.write("Suppression Tables PostgreSQL...")
        cmd_truncate = [
            DOCKER_CMD,
            "exec",
            "postgres_db",
            "psql",
            "-U",
            "admin",
            "-d",
            "reddit_db",
            "-c",
            "DROP TABLE IF EXISTS reddit_posts; DROP TABLE IF EXISTS reddit_stats; DROP TABLE IF EXISTS reddit_comments;",
        ]
        subprocess.run(cmd_truncate)

        status.update(label="Nettoyage terminé ! (Tables supprimées)", state="complete")
        st.sidebar.success("Données et Tables supprimées.")

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📥 Data Ingestion",
        "⚙️ Spark Processing",
        "📈 Strategic Dashboard",
        "🧠 Gemini AI",
        "📊 Grafana Monitor",
    ]
)

# 1. EXTRACTION
with tab1:
    st.header("📥 Data Ingestion Pipeline")

    if st.button("Lancer l'extraction"):
        with st.status("Exécution...") as status:
            # 1. Extraction locale
            st.write("Extraction Reddit (Posts & Commentaires)...")
            # On sépare par virgule et on enlève les espaces inutiles
            subs = [s.strip() for s in subreddits.split(",")]
            cmd = (
                [sys.executable, "extraction_reddit.py", "--subreddits"]
                + subs
                + ["--limit", str(limit), "--comments_limit", str(comments_limit)]
            )
            res_extract = subprocess.run(cmd, capture_output=True, text=True)

            if res_extract.returncode != 0:
                st.error("Erreur lors de l'extraction :")
                st.code(res_extract.stderr)
                st.stop()

            if not os.path.exists("posts.csv"):
                st.error("Le fichier posts.csv n'a pas été généré.")
                st.stop()

            # 2. Upload HDFS (via Docker Exec)
            st.write("Upload vers HDFS...")

            # Créer dossier si existe pas
            subprocess.run(
                [
                    DOCKER_CMD,
                    "exec",
                    "namenode",
                    "hdfs",
                    "dfs",
                    "-mkdir",
                    "-p",
                    "/reddit_data",
                ]
            )

            # Upload Posts
            cmd_copy_posts = [DOCKER_CMD, "cp", "posts.csv", "namenode:/tmp/posts.csv"]
            subprocess.run(cmd_copy_posts)
            cmd_hdfs_posts = [
                DOCKER_CMD,
                "exec",
                "namenode",
                "hdfs",
                "dfs",
                "-put",
                "-f",
                "/tmp/posts.csv",
                "/reddit_data/",
            ]
            subprocess.run(cmd_hdfs_posts)

            # Upload Comments (si existe)
            if os.path.exists("comments.csv"):
                cmd_copy_coms = [
                    DOCKER_CMD,
                    "cp",
                    "comments.csv",
                    "namenode:/tmp/comments.csv",
                ]
                subprocess.run(cmd_copy_coms)
                cmd_hdfs_coms = [
                    DOCKER_CMD,
                    "exec",
                    "namenode",
                    "hdfs",
                    "dfs",
                    "-put",
                    "-f",
                    "/tmp/comments.csv",
                    "/reddit_data/",
                ]
                subprocess.run(cmd_hdfs_coms)

            status.update(label="Succès !", state="complete")
            st.session_state["extraction_done"] = True

    # Affichage Persistant
    if st.session_state["extraction_done"]:
        st.success("Données sur HDFS (/reddit_data/posts.csv & comments.csv)")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Aperçu Posts")
            if os.path.exists("posts.csv"):
                st.dataframe(pd.read_csv("posts.csv"))
        with col2:
            st.subheader("Aperçu Commentaires")
            if os.path.exists("comments.csv"):
                st.dataframe(pd.read_csv("comments.csv"))

# 2. SPARK
with tab2:
    st.header("⚙️ Distributed Processing (Spark)")
    st.info(
        "Ce job lit HDFS (Posts + Commentaires), nettoie les données et écrit dans PostgreSQL."
    )

    if st.button("Lancer Job Spark"):
        with st.spinner("Traitement Spark en cours..."):
            # 0. Installation des dépendances NLP dans le conteneur
            st.write("Installation de TextBlob (NLP) dans le conteneur Spark...")
            subprocess.run(
                [
                    DOCKER_CMD,
                    "exec",
                    "--user",
                    "root",
                    "spark-master",
                    "pip",
                    "install",
                    "textblob",
                ]
            )

            # On lance le script spark_processor.py DANS le conteneur spark-master
            # On passe le DOSSIER HDFS en argument

            cmd_spark = [
                DOCKER_CMD,
                "exec",
                "--user",
                "root",
                "-e",
                "HOME=/tmp",
                "spark-master",
                "/opt/spark/bin/spark-submit",
                "--packages",
                "org.postgresql:postgresql:42.2.18",
                "/app/spark_processor.py",
                "hdfs://namenode:9000/reddit_data",
            ]

            res = subprocess.run(cmd_spark, capture_output=True, text=True)

            # Stockage des résultats dans la session
            st.session_state["spark_stdout"] = res.stdout
            st.session_state["spark_stderr"] = res.stderr

            if res.returncode == 0:
                st.session_state["spark_done"] = True
            else:
                st.session_state["spark_done"] = False  # Ou True mais avec erreur
                st.error("Erreur Spark")
                st.text("Sortie Standard (Debug) :")
                st.code(res.stdout)
                st.text("Erreur (Stderr) :")
                st.code(res.stderr)

    # Affichage Persistant
    if st.session_state["spark_done"]:
        st.success("Job Spark terminé !")

        st.subheader("🔍 Aperçu des Données Traitées (PostgreSQL)")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top 5 Posts (Nettoyés & Analysés)**")
            df_clean_posts = get_postgres_data(
                "SELECT title, clean_body, sentiment, score FROM reddit_posts LIMIT 5"
            )
            if df_clean_posts is not None:
                st.dataframe(df_clean_posts)

        with col2:
            st.markdown("**Statistiques par Subreddit**")
            df_clean_stats = get_postgres_data("SELECT * FROM reddit_stats")
            if df_clean_stats is not None:
                st.dataframe(df_clean_stats)

        st.markdown("---")
        st.text("Sortie Standard :")
        st.code(st.session_state["spark_stdout"])


# 3. STRATEGIC DASHBOARD
with tab3:
    col_title, col_pdf = st.columns([3, 1])
    with col_title:
        st.header("📈 Dashboard Stratégique")
        st.markdown("### 🧠 Intelligence Artificielle & Analyse de Données")

    with col_pdf:
        st.write("")  # Spacer
        st.write("")
        if st.session_state.get("viz_data_loaded"):
            if FPDF_AVAILABLE:
                if st.button("📄 Générer Rapport PDF"):
                    with st.spinner("Génération du PDF..."):
                        pdf_bytes = generate_pdf_report(
                            st.session_state.get("viz_posts"),
                            st.session_state.get("viz_stats"),
                            st.session_state.get("viz_comments"),
                        )
                        if pdf_bytes:
                            st.download_button(
                                label="⬇️ Télécharger le Rapport",
                                data=pdf_bytes,
                                file_name="reddit_pulse_report.pdf",
                                mime="application/pdf",
                            )
            else:
                st.warning("Installez 'fpdf' pour le PDF")

    st.info(
        "Explorez les tendances, sentiments et performances de vos marques sur Reddit via notre moteur d'analyse."
    )

    # --- CHARGEMENT DES DONNEES ---
    if st.button("🔄 Charger / Rafraîchir les Données", key="btn_load_viz"):
        with st.spinner("Récupération des données depuis la base PostgreSQL..."):
            # 1. Récupération des Posts (Tout)
            try:
                # On essaie de récupérer num_comments s'il existe
                df_posts = get_postgres_data("SELECT * FROM reddit_posts")
            except Exception as e:
                st.error(f"Erreur chargement Posts: {e}")
                df_posts = None

            # 2. Récupération des Stats (Pré-calculées par Spark)
            try:
                # On renomme les colonnes pour être sûr
                df_stats = get_postgres_data(
                    'SELECT subreddit, "avg(sentiment)" as avg_sentiment, "avg(score)" as avg_score FROM reddit_stats'
                )
            except:
                # Fallback si la table a une structure différente
                df_stats = get_postgres_data("SELECT * FROM reddit_stats")

            # 3. Récupération des Commentaires (Limitée pour la perf)
            try:
                df_comments = get_postgres_data(
                    "SELECT * FROM reddit_comments LIMIT 2000"
                )
            except:
                df_comments = None

            # Stockage en Session
            st.session_state["viz_posts"] = df_posts
            st.session_state["viz_stats"] = df_stats
            st.session_state["viz_comments"] = df_comments
            st.session_state["viz_data_loaded"] = True

    # --- AFFICHAGE ---
    if st.session_state.get("viz_data_loaded"):
        df_p = st.session_state.get("viz_posts")
        df_s = st.session_state.get("viz_stats")
        df_c = st.session_state.get("viz_comments")

        if df_p is None or df_p.empty:
            st.warning("Aucune donnée trouvée dans la table 'reddit_posts'.")
        else:
            # Pré-traitement Dates
            if "created_utc" in df_p.columns:
                df_p["date"] = pd.to_datetime(df_p["created_utc"], unit="s")
                df_p["hour"] = df_p["date"].dt.hour
                df_p["day"] = df_p["date"].dt.date

            # SÉLECTEUR DE MODE
            mode_analyse = st.radio(
                "🎯 Choisissez votre vue :",
                [
                    "🌍 Comparatif Global (Tous les sujets)",
                    "🔍 Analyse Détaillée par Sujet",
                ],
                horizontal=True,
            )
            st.markdown("---")

            # --- VUE 1 : COMPARATIF GLOBAL ---
            if mode_analyse == "🌍 Comparatif Global (Tous les sujets)":
                st.subheader("🌍 Vue d'ensemble du Marché")

                # 1. KPI GLOBAUX
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Total Posts", len(df_p), delta="Global")
                kpi2.metric(
                    "Total Commentaires",
                    len(df_c) if df_c is not None else 0,
                    delta="Echantillon",
                )
                kpi3.metric("Score Moyen", f"{df_p['score'].mean():.1f}")
                kpi4.metric(
                    "Sentiment Moyen",
                    f"{df_p['sentiment'].mean():.3f}",
                    delta_color="normal",
                )

                st.markdown("### ⏳ Analyse Temporelle")
                # Line Chart: Volume par Subreddit dans le temps
                if "date" in df_p.columns:
                    chart_time = (
                        alt.Chart(df_p)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X(
                                "date:T",
                                timeUnit="yearmonthdatehours",
                                title="Date & Heure",
                            ),  # Groupement par Heure
                            y=alt.Y("count()", title="Nombre de Posts"),
                            color="subreddit",
                            tooltip=[
                                alt.Tooltip(
                                    "date:T",
                                    timeUnit="yearmonthdatehours",
                                    title="Heure",
                                ),
                                "subreddit",
                                "count()",
                            ],
                        )
                        .properties(height=300)
                        .interactive()
                    )
                    st.altair_chart(chart_time, use_container_width=True)

                st.markdown("### 🎭 Analyse des Sentiments")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Sentiment Moyen par Marque**")
                    if df_s is not None and not df_s.empty:
                        col_sent = (
                            "avg_sentiment"
                            if "avg_sentiment" in df_s.columns
                            else df_s.columns[1]
                        )
                        chart_bar = (
                            alt.Chart(df_s)
                            .mark_bar()
                            .encode(
                                x=alt.X("subreddit", sort="-y"),
                                y=alt.Y(col_sent, title="Sentiment Moyen"),
                                color=alt.Color(
                                    col_sent, scale=alt.Scale(scheme="redyellowgreen")
                                ),
                                tooltip=["subreddit", col_sent],
                            )
                        )
                        st.altair_chart(chart_bar, use_container_width=True)
                    else:
                        st.info("Pas de stats pré-calculées.")

                with c2:
                    st.markdown("**Distribution des Sentiments (Boxplot)**")
                    # Boxplot pour voir la variance
                    chart_box = (
                        alt.Chart(df_p)
                        .mark_boxplot(extent="min-max")
                        .encode(
                            x=alt.X("subreddit"),
                            y=alt.Y("sentiment", title="Sentiment"),
                            color="subreddit",
                        )
                    )
                    st.altair_chart(chart_box, use_container_width=True)

                st.markdown("### 📢 Engagement & Impact")
                e1, e2 = st.columns(2)
                with e1:
                    st.markdown("**Relation Sentiment vs Popularité**")
                    scatter = (
                        alt.Chart(df_p)
                        .mark_circle(size=60)
                        .encode(
                            x=alt.X("sentiment", title="Sentiment (-1 à 1)"),
                            y=alt.Y("score", title="Score (Upvotes)"),
                            color="subreddit",
                            tooltip=["title", "subreddit", "score", "sentiment"],
                        )
                        .interactive()
                    )
                    st.altair_chart(scatter, use_container_width=True)

                with e2:
                    st.markdown("**Volume de Commentaires par Marque**")
                    if df_c is not None:
                        # Join pour avoir le subreddit dans les comments si pas présent
                        # On suppose que df_c a 'subreddit'
                        if "subreddit" in df_c.columns:
                            chart_coms = (
                                alt.Chart(df_c)
                                .mark_bar()
                                .encode(
                                    x=alt.X("subreddit", sort="-y"),
                                    y=alt.Y("count()", title="Nb Commentaires"),
                                    color="subreddit",
                                )
                            )
                            st.altair_chart(chart_coms, use_container_width=True)
                        else:
                            st.warning(
                                "Colonne 'subreddit' manquante dans les commentaires."
                            )

            # --- VUE 2 : ANALYSE PAR SUJET ---
            else:
                # Sélecteur de Subreddit
                sub_list = df_p["subreddit"].unique()
                selected_sub = st.selectbox(
                    "📂 Sélectionner un Subreddit à analyser :", sub_list
                )

                # Filtrage
                sub_df = df_p[df_p["subreddit"] == selected_sub]

                st.subheader(f"🔍 Analyse Approfondie : r/{selected_sub}")

                # KPI LOCAL
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Posts", len(sub_df))
                k2.metric("Score Max", sub_df["score"].max())
                k3.metric("Sentiment Moyen", f"{sub_df['sentiment'].mean():.3f}")
                pos_ratio = (sub_df["sentiment"] > 0).mean() * 100
                k4.metric("Taux de Positivité", f"{pos_ratio:.1f}%")

                # 1. EVOLUTION TEMPORELLE
                st.markdown("### 📈 Évolution Temporelle")
                if "date" in sub_df.columns:
                    t1, t2 = st.columns(2)
                    with t1:
                        st.markdown("**Volume de Posts (par heure)**")
                        line_vol = (
                            alt.Chart(sub_df)
                            .mark_line(point=True, color="#FFA500")
                            .encode(
                                x=alt.X(
                                    "date:T",
                                    timeUnit="yearmonthdatehours",
                                    title="Date & Heure",
                                ),
                                y=alt.Y("count()", title="Nombre de Posts"),
                                tooltip=[
                                    alt.Tooltip(
                                        "date:T", timeUnit="yearmonthdatehours"
                                    ),
                                    "count()",
                                ],
                            )
                            .interactive()
                        )
                        st.altair_chart(line_vol, use_container_width=True)
                    with t2:
                        st.markdown("**Sentiment Moyen (par heure)**")
                        # On agrège par jour ou heure pour lisser
                        line_sent = (
                            alt.Chart(sub_df)
                            .mark_line(point=True, color="#00CED1")
                            .encode(
                                x=alt.X(
                                    "date:T",
                                    timeUnit="yearmonthdatehours",
                                    title="Date & Heure",
                                ),
                                y=alt.Y("mean(sentiment)", title="Sentiment Moyen"),
                                tooltip=[
                                    alt.Tooltip(
                                        "date:T", timeUnit="yearmonthdatehours"
                                    ),
                                    "mean(sentiment)",
                                ],
                            )
                            .interactive()
                        )
                        st.altair_chart(line_sent, use_container_width=True)

                # 2. ANALYSE DE CONTENU (Mots clés)
                st.markdown("### 📝 Analyse du Contenu")
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown("**Top 20 Mots les plus fréquents**")
                    # Extraction des mots
                    all_text = " ".join(
                        sub_df["title"].astype(str)
                        + " "
                        + sub_df["body"].fillna("").astype(str)
                    ).lower()
                    # Nettoyage basique
                    words = re.findall(r"\b\w+\b", all_text)
                    # Stopwords (Liste basique anglais/français)
                    STOPWORDS = set(
                        [
                            "the",
                            "a",
                            "an",
                            "in",
                            "on",
                            "at",
                            "for",
                            "to",
                            "of",
                            "is",
                            "are",
                            "was",
                            "were",
                            "be",
                            "been",
                            "and",
                            "or",
                            "but",
                            "if",
                            "then",
                            "else",
                            "when",
                            "where",
                            "why",
                            "how",
                            "all",
                            "any",
                            "both",
                            "each",
                            "few",
                            "more",
                            "most",
                            "other",
                            "some",
                            "such",
                            "no",
                            "nor",
                            "not",
                            "only",
                            "own",
                            "same",
                            "so",
                            "than",
                            "too",
                            "very",
                            "s",
                            "t",
                            "can",
                            "will",
                            "just",
                            "don",
                            "should",
                            "now",
                            "d",
                            "ll",
                            "m",
                            "o",
                            "re",
                            "ve",
                            "y",
                            "ain",
                            "aren",
                            "couldn",
                            "didn",
                            "doesn",
                            "hadn",
                            "hasn",
                            "haven",
                            "isn",
                            "ma",
                            "mightn",
                            "mustn",
                            "needn",
                            "shan",
                            "shouldn",
                            "wasn",
                            "weren",
                            "won",
                            "wouldn",
                            "i",
                            "me",
                            "my",
                            "myself",
                            "we",
                            "our",
                            "ours",
                            "ourselves",
                            "you",
                            "your",
                            "yours",
                            "yourself",
                            "yourselves",
                            "he",
                            "him",
                            "his",
                            "himself",
                            "she",
                            "her",
                            "hers",
                            "herself",
                            "it",
                            "its",
                            "itself",
                            "they",
                            "them",
                            "their",
                            "theirs",
                            "themselves",
                            "what",
                            "which",
                            "who",
                            "whom",
                            "this",
                            "that",
                            "these",
                            "those",
                            "le",
                            "la",
                            "les",
                            "de",
                            "des",
                            "du",
                            "un",
                            "une",
                            "et",
                            "est",
                            "pour",
                            "en",
                            "que",
                            "qui",
                            "dans",
                            "sur",
                            "pas",
                            "plus",
                            "par",
                            "avec",
                            "ce",
                            "ces",
                            "cette",
                            "ont",
                            "il",
                            "ils",
                            "elle",
                            "elles",
                            "nous",
                            "vous",
                            "je",
                            "tu",
                            "mon",
                            "ton",
                            "son",
                            "ma",
                            "ta",
                            "sa",
                            "mes",
                            "tes",
                            "ses",
                            "notre",
                            "votre",
                            "leur",
                            "nos",
                            "vos",
                            "leurs",
                            "aux",
                            "ou",
                            "où",
                            "donc",
                            "or",
                            "ni",
                            "car",
                            "mais",
                            "http",
                            "https",
                            "com",
                            "www",
                            "reddit",
                            "removed",
                            "deleted",
                        ]
                    )

                    filtered_words = [
                        w for w in words if w not in STOPWORDS and len(w) > 3
                    ]
                    word_counts = Counter(filtered_words).most_common(20)

                    df_words = pd.DataFrame(word_counts, columns=["Mot", "Fréquence"])

                    chart_words = (
                        alt.Chart(df_words)
                        .mark_bar()
                        .encode(
                            x=alt.X("Fréquence"),
                            y=alt.Y("Mot", sort="-x"),
                            color=alt.Color(
                                "Fréquence", scale=alt.Scale(scheme="blues")
                            ),
                            tooltip=["Mot", "Fréquence"],
                        )
                    )
                    st.altair_chart(chart_words, use_container_width=True)

                with c2:
                    st.markdown("**Répartition Sentiments**")
                    pos = sub_df[sub_df["sentiment"] > 0].shape[0]
                    neg = sub_df[sub_df["sentiment"] < 0].shape[0]
                    neu = sub_df[sub_df["sentiment"] == 0].shape[0]

                    df_pie = pd.DataFrame(
                        {
                            "Sentiment": ["Positif", "Négatif", "Neutre"],
                            "Nombre": [pos, neg, neu],
                        }
                    )

                    pie = (
                        alt.Chart(df_pie)
                        .mark_arc(innerRadius=45)
                        .encode(
                            theta=alt.Theta("Nombre", stack=True),
                            color=alt.Color(
                                "Sentiment",
                                scale=alt.Scale(
                                    domain=["Positif", "Négatif", "Neutre"],
                                    range=["#28a745", "#dc3545", "#6c757d"],
                                ),
                            ),
                            tooltip=["Sentiment", "Nombre"],
                        )
                    )
                    st.altair_chart(pie, use_container_width=True)

                # 3. AUTEURS & POSTS
                st.markdown("### 👥 Communauté & Top Posts")
                a1, a2 = st.columns([1, 2])
                with a1:
                    st.markdown("**Top 10 Auteurs Actifs**")
                    top_authors = sub_df["author"].value_counts().head(10).reset_index()
                    top_authors.columns = ["Auteur", "Posts"]
                    st.dataframe(top_authors, hide_index=True, use_container_width=True)

                with a2:
                    st.markdown("**Top 5 Posts les plus populaires**")
                    top_posts = sub_df.sort_values(by="score", ascending=False).head(5)
                    st.dataframe(
                        top_posts[
                            (
                                ["title", "score", "sentiment", "num_comments"]
                                if "num_comments" in top_posts.columns
                                else ["title", "score", "sentiment"]
                            )
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )

                # 4. COMMENTAIRES
                if df_c is not None:
                    st.markdown("### 💬 Analyse des Commentaires")
                    post_ids = sub_df["id"].tolist()
                    sub_coms = df_c[df_c["post_id"].isin(post_ids)]

                    if not sub_coms.empty:
                        kc1, kc2 = st.columns(2)
                        kc1.metric("Nombre de Commentaires analysés", len(sub_coms))
                        kc2.metric(
                            "Sentiment Moyen des Commentaires",
                            f"{sub_coms['sentiment'].mean():.3f}",
                        )

                        st.markdown("**Top Commentaires (les mieux notés) :**")
                        st.dataframe(
                            sub_coms.sort_values(by="score", ascending=False)[
                                ["body", "author", "score", "sentiment"]
                            ].head(10),
                            hide_index=True,
                            use_container_width=True,
                        )
                    else:
                        st.info(
                            "Aucun commentaire trouvé pour ce subreddit dans l'échantillon chargé."
                        )

            # --- TABLEAU DE DONNEES BRUTES (Commun) ---
            with st.expander("📋 Voir les données brutes complètes"):
                st.dataframe(df_p)

    else:
        st.info(
            "Cliquez sur le bouton ci-dessus pour charger les données et démarrer l'analyse."
        )

# 4. GEMINI (Adapté)
with tab4:
    col_header, col_reset = st.columns([3, 1])
    with col_header:
        st.header("🧠 AI Assistant (Gemini)")
        st.caption("Analysez vos données Reddit avec la puissance de Google Gemini.")

    if not GEMINI_AVAILABLE:
        st.error(
            "⚠️ Le module `google.generativeai` n'est pas installé ou incompatible."
        )
        st.info("Installez-le via : `pip install google-generativeai`")
    else:
        # API Key Management
        if "gemini_api_key" not in st.session_state:
            st.session_state.gemini_api_key = ""

        with st.expander(
            "🔑 Configuration API Gemini", expanded=not st.session_state.gemini_api_key
        ):
            api_key_input = st.text_input(
                "Entrez votre clé API Google Gemini :",
                type="password",
                value=st.session_state.gemini_api_key,
            )
            if api_key_input:
                st.session_state.gemini_api_key = api_key_input

        if st.session_state.gemini_api_key and os.path.exists("posts.csv"):
            genai.configure(api_key=st.session_state.gemini_api_key)

            # Chat History Init
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            # Reset + Export Buttons (placed together)
            with col_reset:
                if st.button(
                    "🗑️ Effacer l'historique",
                    use_container_width=True,
                    key="clear_history",
                ):
                    st.session_state.chat_history = []
                    st.rerun()

                # Génération PDF de la conversation (placée à côté)
                if "chat_history" in st.session_state and st.session_state.get(
                    "chat_history"
                ):
                    if FPDF_AVAILABLE:
                        if st.button(
                            "📄 Générer Conversation PDF",
                            use_container_width=True,
                            key="gen_convo_pdf",
                        ):
                            with st.spinner("Génération du PDF de conversation..."):
                                pdf_bytes = generate_gemini_pdf(
                                    st.session_state.get("chat_history")
                                )
                                if pdf_bytes:
                                    st.download_button(
                                        label="⬇️ Télécharger la Conversation (PDF)",
                                        data=pdf_bytes,
                                        file_name="gemini_conversation.pdf",
                                        mime="application/pdf",
                                    )
                    else:
                        st.warning(
                            "Installez 'fpdf' pour exporter la conversation en PDF"
                        )

            # Data Context Loading
            df = pd.read_csv("posts.csv")
            # On augmente un peu le contexte
            sample_df = df.groupby("subreddit").head(15)
            # On inclut num_comments si dispo
            cols_to_keep = ["title", "body", "subreddit", "score"]
            if "num_comments" in df.columns:
                cols_to_keep.append("num_comments")

            sample_data = sample_df[cols_to_keep].to_csv(index=False)

            # Quick Actions
            st.markdown("###### ⚡ Actions Rapides")
            col_q1, col_q2, col_q3 = st.columns(3)

            prompt_to_run = None

            if col_q1.button("📊 Analyse Globale", use_container_width=True):
                prompt_to_run = "Fais une analyse globale détaillée de ces données Reddit (tendances, sentiments, sujets clés, anomalies)."

            if col_q2.button("😡 Identifier les Crises", use_container_width=True):
                prompt_to_run = "Identifie les posts avec un sentiment très négatif ou polémique. Quels sont les sujets de mécontentement ?"

            if col_q3.button("💡 Idées de Contenu", use_container_width=True):
                prompt_to_run = "Basé sur les sujets populaires, suggère 3 idées de contenu ou d'articles qui pourraient intéresser cette audience."

            # Handle Quick Actions
            if prompt_to_run:
                st.session_state.chat_history.append(
                    {"role": "user", "content": prompt_to_run}
                )
                with st.spinner("Analyse IA en cours..."):
                    try:
                        model = genai.GenerativeModel("gemini-pro-latest")
                        full_prompt = f"""
                        Tu es un expert Senior Data Analyst spécialisé dans les réseaux sociaux.
                        Tu analyses des données Reddit. Sois professionnel, structuré et perspicace.
                        Utilise du Markdown pour formater ta réponse (titres, listes, gras).
                        
                        Voici les données (CSV) :
                        {sample_data}
                        
                        Instruction : {prompt_to_run}
                        """
                        response = model.generate_content(full_prompt)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": response.text}
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur Gemini : {e}")

            # Chat Display
            container = st.container()
            with container:
                for message in st.session_state.chat_history:
                    with st.chat_message(
                        message["role"],
                        avatar="🧑‍💻" if message["role"] == "user" else "🧠",
                    ):
                        st.markdown(message["content"])

            # Chat Input
            if user_input := st.chat_input("Posez une question sur vos données..."):
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input}
                )
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(user_input)

                with st.chat_message("assistant", avatar="🧠"):
                    with st.spinner("Analyse en cours..."):
                        try:
                            model = genai.GenerativeModel("gemini-pro-latest")
                            full_prompt = f"""
                            Tu es un expert Senior Data Analyst.
                            Contexte données (CSV) :
                            {sample_data}
                            
                            Question utilisateur : {user_input}
                            """
                            response = model.generate_content(full_prompt)
                            st.markdown(response.text)
                            st.session_state.chat_history.append(
                                {"role": "assistant", "content": response.text}
                            )
                        except Exception as e:
                            st.error(f"Erreur : {e}")

            # Export conversation PDF (Gemini)
            if st.session_state.get("chat_history"):
                if FPDF_AVAILABLE:
                    if st.button("📄 Générer Conversation PDF"):
                        with st.spinner("Génération du PDF de conversation..."):
                            pdf_bytes = generate_gemini_pdf(
                                st.session_state.get("chat_history")
                            )
                            if pdf_bytes:
                                st.download_button(
                                    label="⬇️ Télécharger la Conversation (PDF)",
                                    data=pdf_bytes,
                                    file_name="gemini_conversation.pdf",
                                    mime="application/pdf",
                                )
                else:
                    st.warning("Installez 'fpdf' pour exporter la conversation en PDF")

        elif st.session_state.gemini_api_key:
            st.warning(
                "⚠️ Fichier 'posts.csv' introuvable. Veuillez lancer l'extraction dans l'onglet 'Data Ingestion'."
            )

# 5. VISUALISATION STREAMLIT
with tab5:
    st.header("📊 Grafana Monitor")
    st.markdown("### 🕵️ Surveillance Temps Réel")
    st.info(
        "Accédez aux tableaux de bord Grafana pour visualiser les métriques système et applicatives."
    )

    # Option pour ouvrir dans un nouvel onglet
    st.markdown(
        """
        <a href="http://localhost:3000" target="_blank">
            <button style="
                background-color: #FF4500; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer;
                margin-bottom: 20px;
                font-weight: bold;">
                🔗 Ouvrir Grafana en Plein Écran
            </button>
        </a>
    """,
        unsafe_allow_html=True,
    )

    # Intégration Iframe
    st.markdown(
        """
        <iframe src="http://localhost:3000" width="100%" height="1200" frameborder="0"></iframe>
    """,
        unsafe_allow_html=True,
    )
