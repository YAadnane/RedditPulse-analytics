# 🚀 RedditPulse Analytics
> **Decode the Hivemind. Visualize the Sentiment.**

[![CI/CD](https://github.com/YAadnane/RedditPulse-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/YAadnane/RedditPulse-analytics/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![Spark](https://img.shields.io/badge/Apache%20Spark-Processing-E25A1C.svg)](https://spark.apache.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)

---

## 🧠 What is RedditPulse?

**RedditPulse Analytics** is a robust Big Data pipeline designed to transform chaotic social media noise into actionable business intelligence.

By tapping into Reddit's vast ecosystem, this platform ingests discussions in real-time, processes them through a distributed computing engine (**Spark**), analyzes sentiment using NLP, and delivers insights via an interactive dashboard powered by **AI**.

Whether for product feedback, trend watching, or community sentiment, RedditPulse sees what others miss.

---

## 🏗️ The Big Data Pipeline

We built a scalable architecture to handle data from extraction to insight:

```mermaid
graph LR
    A[Reddit API] -->|Ingestion| B(Python Script)
    B -->|Raw Data| C[(Hadoop HDFS)]
    C -->|Distributed Processing| D{Apache Spark}
    D -->|Cleaning & NLP| D
    D -->|Structured Data| E[(PostgreSQL)]
    E -->|Visualization| F[Streamlit App]
    E -->|Monitoring| G[Grafana]
    H[Google Gemini AI] -.->|Insights| F

## ✨ Features

- **Data Ingestion**: Extracts posts and comments from specific subreddits using the Reddit API.
- **Distributed Processing**: Uses Apache Spark for data cleaning, sentiment analysis (NLP), and metric aggregation.
- **Data Storage**: Stores raw data in HDFS and processed data in a PostgreSQL database.
- **Interactive Dashboard**: A Streamlit app provides dynamic visualizations and detailed analytics.
- **AI Assistant**: Integration with Google Gemini for conversational analysis of data.
- **Monitoring**: Grafana dashboard for system and data monitoring.

## 🏛️ Architecture

The project is fully containerized with Docker and includes the following components:

- **Streamlit**: Web interface for user interaction.
- **Python**: For data extraction (`praw`) and backend logic.
- **HDFS (Hadoop)**: Distributed storage for raw Reddit data.
- **Apache Spark**: Processing engine for cleaning and analysis tasks.
- **PostgreSQL**: Relational database for storing analyzed results.
- **Grafana**: Visualization and monitoring (if data sources are configured).
- **Adminer**: Easy database management interface.

## 🚀 Quick Start

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) and Docker Compose
- A Reddit account with API keys (for extraction)
- (Optional) A Google Gemini API key

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/YAadnane/redditpulse-analytics.git
   cd redditpulse-analytics
   ```

2. **Configure environment variables:**
   Create a `.env` file by copying the `.env.example` template and fill in your values.

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file with your secrets.

3. **Start the application:**

   ```bash
   docker compose up --build
   ```

4. **Access the services:**
   - **Streamlit App**: [http://localhost:8501](http://localhost:8501)
   - **Hadoop Dashboard (NameNode)**: [http://localhost:9870](http://localhost:9870)
   - **Spark Dashboard (Master)**: [http://localhost:8080](http://localhost:8080)
   - **Grafana**: [http://localhost:3000](http://localhost:3000)
   - **Adminer (DB Management)**: [http://localhost:8081](http://localhost:8081)

## 🔧 Customization

- **Subreddits**: Change the subreddits to analyze directly from the Streamlit interface.
- **Spark Configuration**: Adjust Spark resources in `docker-compose.yml`.
- **Grafana Dashboards**: Import or create new dashboards to monitor PostgreSQL or other metrics.

---

## 🚀 Usage Example

```bash
# Extract Reddit data
python extraction_reddit.py --subreddits datascience python --limit 100 --comments_limit 5

# Launch the Streamlit dashboard
streamlit run app.py
```

## 📚 Documentation & APIs

- [Reddit API (PRAW)](https://praw.readthedocs.io/en/latest/)
- [Google Gemini API](https://ai.google.dev/)
- [Streamlit](https://docs.streamlit.io/)
- [Docker](https://docs.docker.com/)

## 🛠️ CI/CD

The CI/CD workflow uses GitHub Actions to:

- Install Python dependencies
- Run linting (flake8)
- Execute tests (test.py)

To customize or add steps, edit `.github/workflows/ci.yml`.

## 🏭 Production Deployment

1. **Build the Streamlit Docker image**
   ```bash
   docker build -t redditpulse-app .
   ```
2. **Start with Docker Compose**
   ```bash
   docker compose up --build -d
   ```
3. **Reverse-proxy & TLS (optional)**

   - Install Nginx and Certbot on your server
   - Configure the proxy to redirect traffic to the Streamlit container
   - Generate a Let's Encrypt SSL certificate

4. **Environment variables**

   - Copy `.env.example` to `.env` and fill in your API keys and passwords

5. **Access dashboards**
   - Streamlit: http://your-domain:8501
   - Grafana: http://your-domain:3000
   - Hadoop: http://your-domain:9870

## 🌐 Landing Page

The `landing_page` folder contains a modern showcase website for RedditPulse: objectives, features, testimonials, and a contact form. It helps present the project to users and partners.

To view the page, open `landing_page/index.html` in your browser.
