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
