import streamlit as st
import requests
import json
from datetime import datetime, timedelta

# ---- Page Config ----
st.set_page_config(page_title="AI News Summarizer", page_icon="📰", layout="wide")
st.title("📰 AI News Summarizer")
st.write("Enter any topic → fetch latest news → AI summarizes it in bullet points.")

# ---- Sidebar: Ollama Settings ----
st.sidebar.title("⚙️ Ollama Server")
server_ip   = st.sidebar.text_input("Remote Server IP", placeholder="e.g. 192.168.1.100")
server_port = st.sidebar.text_input("Port", value="11434")
model_name  = st.sidebar.selectbox("Model", ["llama3", "mistral", "phi3"])

# ---- Sidebar: NewsAPI Key ----
st.sidebar.title("🔑 NewsAPI")
news_api_key = st.sidebar.text_input("NewsAPI Key", type="password", placeholder="bc84adfac50c462f9e8ba462e9a4e447")

ollama_url = f"http://{server_ip}:{server_port}/api/generate"

# ---- Preset Topics (from your background) ----
st.subheader("📌 Choose or Enter a Topic")

preset_topics = [
    "Real Estate India",
    "Artificial Intelligence",
    "Digital Marketing",
    "Retail Industry India",
    "PropTech",
    "Sales Technology",
    "Startup India",
    "Custom Topic..."
]

selected_preset = st.selectbox("Quick Topics", preset_topics)

if selected_preset == "Custom Topic...":
    topic = st.text_input("Enter Your Topic", placeholder="e.g. Electric Vehicles India")
else:
    topic = selected_preset

# ---- Settings ----
col1, col2, col3 = st.columns(3)
with col1:
    num_articles = st.slider("Number of Articles to Fetch", 3, 10, 5)
with col2:
    days_back = st.slider("News from last N days", 1, 7, 2)
with col3:
    language = st.selectbox("Language", ["en", "hi"])

summary_style = st.selectbox("Summary Style", [
    "Bullet Points (Quick Read)",
    "Executive Summary (1 paragraph)",
    "Detailed Analysis",
    "Key Takeaways for Business"
])

# ---- Fetch + Summarize Button ----
if st.button("🔍 Fetch & Summarize News"):

    if not server_ip:
        st.error("Enter Ollama server IP in the sidebar.")
    elif not news_api_key:
        st.error("Enter your NewsAPI key in the sidebar.")
    elif not topic:
        st.warning("Please enter a topic.")
    else:

        # ---- PART 1: Fetch News ----
        with st.spinner(f"Fetching latest news on '{topic}'..."):
            from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            news_url = "https://newsapi.org/v2/everything"
            params = {
                "q": topic,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": language,
                "pageSize": num_articles,
                "apiKey": news_api_key
            }

            try:
                news_response = requests.get(news_url, params=params, timeout=15)
                news_data     = news_response.json()

                if news_data.get("status") != "ok":
                    st.error(f"NewsAPI Error: {news_data.get('message', 'Unknown error')}")
                    st.stop()

                articles = news_data.get("articles", [])

                if not articles:
                    st.warning("No articles found. Try a different topic or increase the date range.")
                    st.stop()

                # Show fetched articles
                st.subheader(f"📄 {len(articles)} Articles Found")
                article_texts = []

                for i, article in enumerate(articles):
                    title       = article.get("title", "No title")
                    source      = article.get("source", {}).get("name", "Unknown")
                    published   = article.get("publishedAt", "")[:10]
                    description = article.get("description", "") or ""
                    url         = article.get("url", "")

                    with st.expander(f"{i+1}. {title} — {source} ({published})"):
                        st.write(description)
                        st.markdown(f"[Read Full Article]({url})")

                    article_texts.append(f"Title: {title}\nSource: {source}\nSummary: {description}")

            except Exception as e:
                st.error(f"Failed to fetch news: {str(e)}")
                st.stop()

        # ---- PART 2: Summarize with Ollama ----
        combined_articles = "\n\n---\n\n".join(article_texts)

        prompt = f"""
You are a professional news analyst and business intelligence expert.

I have fetched {len(articles)} news articles about: "{topic}"

Here are the articles:

{combined_articles}

Task: Summarize these articles in the style: {summary_style}

Rules:
- Be concise and informative
- Extract the most important insights
- Focus on what matters for business decisions
- If there are trends, highlight them
- Use simple, clear language
- Do NOT repeat the same point multiple times

Write your summary now:
"""

        with st.spinner(f"AI is summarizing via {model_name}..."):
            try:
                response = requests.post(
                    ollama_url,
                    json={"model": model_name, "prompt": prompt, "stream": True},
                    stream=True,
                    timeout=180
                )

                summary    = ""
                output_box = st.empty()

                st.subheader("🧠 AI Summary")
                for line in response.iter_lines():
                    if line:
                        data  = json.loads(line)
                        token = data.get("response", "")
                        summary += token
                        output_box.markdown(summary)
                        if data.get("done"):
                            break

                st.success("✅ Summary Ready!")

                # Download options
                col_a, col_b = st.columns(2)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                with col_a:
                    st.download_button(
                        "📥 Download Summary (.txt)",
                        data=f"Topic: {topic}\nDate: {datetime.now().strftime('%d %b %Y')}\n\n{summary}",
                        file_name=f"news_summary_{topic.replace(' ', '_')}_{timestamp}.txt",
                        mime="text/plain"
                    )
                with col_b:
                    st.download_button(
                        "📋 Download as Markdown",
                        data=f"# News Summary: {topic}\n**Date:** {datetime.now().strftime('%d %b %Y')}\n\n{summary}",
                        file_name=f"news_summary_{topic.replace(' ', '_')}_{timestamp}.md",
                        mime="text/markdown"
                    )

            except requests.exceptions.ConnectionError:
                st.error(f"❌ Cannot connect to Ollama at {ollama_url}. Check your server.")
            except Exception as e:
                st.error(f"Summarization error: {str(e)}")

# ---- Footer ----
st.markdown("---")
st.caption("NewsAPI (free) + Ollama GPU Server | Zero OpenAI cost | Your data stays private")