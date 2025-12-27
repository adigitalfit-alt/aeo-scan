import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse

# Page Config
st.set_page_config(page_title="Advanced AEO Scanner", page_icon="🧠", layout="centered")

# Custom Styling (Dark Mode & AI Aesthetic)
st.markdown("""
    <style>
    .main {
        background: linear-gradient(145deg, #0f0c29, #302b63, #24243e);
        color: #ffffff;
    }
    h1 { color: #00d9ff; text-align: center; font-family: 'Helvetica Neue', sans-serif; }
    .metric-box {
        background-color: rgba(0, 0, 0, 0.3);
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 5px solid #5b4fff;
    }
    .score-high { color: #00d9ff; }
    .score-med { color: #f2c94c; }
    .score-low { color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

st.title("Advanced AEO Scanner 2.0")
st.markdown("Analyze your brand's readiness for **ChatGPT, Gemini, and Perplexity**.")

# Input
target_url = st.text_input("Enter Website URL:", placeholder="https://yourbrand.com")

def check_robots_txt(domain):
    """Checks if GPTBot or CCBot are blocked in robots.txt"""
    try:
        robots_url = f"{domain.scheme}://{domain.netloc}/robots.txt"
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200:
            content = response.text.lower()
            if "disallow: /" in content and ("gptbot" in content or "ccbot" in content):
                return False, "❌ **Critical:** You are blocking AI Bots (GPTBot) in robots.txt."
            return True, "✅ **Crawlability:** AI Bots are allowed to scan your site."
        return True, "⚠️ **Crawlability:** No robots.txt found (Assumed Open)."
    except:
        return True, "⚠️ **Crawlability:** Could not verify robots.txt."

def analyze_advanced_aeo(url):
    score = 0
    feedback = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 1. BASE CONNECTIVITY
        domain = urlparse(url)
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        load_time = time.time() - start_time
        
        if response.status_code != 200:
            return 0, [f"❌ Connection Failed: {response.status_code}"]

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- NEW PARAMETER 1: ROBOTS/AI PERMISSION (Critical) ---
        # Weight: 15
        is_crawlable, robot_msg = check_robots_txt(domain)
        feedback.append(robot_msg)
        if is_crawlable:
            score += 15
        else:
            score -= 10 # Penalty for blocking AI

        # --- NEW PARAMETER 2: LLMS.TXT STANDARD ---
        # Weight: 10
        try:
            llms_url = f"{domain.scheme}://{domain.netloc}/llms.txt"
            llms_resp = requests.get(llms_url, timeout=3)
            if llms_resp.status_code == 200:
                score += 10
                feedback.append("✅ **AI Standard:** Found '/llms.txt' file. Excellent.")
            else:
                feedback.append("⚠️ **AI Standard:** No '/llms.txt' file found. (Recommended for 2026).")
        except:
            pass

        # --- PARAMETER 3: ENTITY SCHEMA (Organization/Brand) ---
        # Weight: 20
        schema_tags = soup.find_all('script', type='application/ld+json')
        found_org = False
        found_faq = False # New check
        
        if schema_tags:
            for tag in schema_tags:
                txt = tag.text
                if "Organization" in txt or "Brand" in txt:
                    found_org = True
                if "FAQPage" in txt:
                    found_faq = True
        
        if found_org:
            score += 20
            feedback.append("✅ **Identity:** Organization Schema detected.")
        else:
            feedback.append("❌ **Identity:** No Organization Schema. You are hard to verify.")

        # --- NEW PARAMETER 4: FAQ SCHEMA (Direct Answers) ---
        # Weight: 15
        if found_faq:
            score += 15
            feedback.append("✅ **AEO Signal:** FAQPage Schema found. Great for direct answers.")
        else:
            feedback.append("⚠️ **AEO Signal:** No FAQ Schema. You are missing 'Direct Answer' opportunities.")

        # --- NEW PARAMETER 5: CONTENT DEPTH (For Training) ---
        # Weight: 15
        # AI needs text to understand context. Thin pages (under 500 words) get ignored.
        text_content = soup.get_text(strip=True)
        word_count = len(text_content.split())
        
        if word_count > 1000:
            score += 15
            feedback.append(f"✅ **Content Depth:** Rich content detected ({word_count} words).")
        elif word_count > 500:
            score += 10
            feedback.append(f"✅ **Content Depth:** Acceptable content length ({word_count} words).")
        else:
            feedback.append(f"❌ **Content Depth:** Thin content ({word_count} words). AI cannot learn enough here.")

        # --- NEW PARAMETER 6: AUTHOR AUTHORITY (E-E-A-T) ---
        # Weight: 10
        # AI looks for WHO wrote this to assign trust.
        author_tag = soup.find("meta", attrs={"name": "author"})
        if author_tag:
            score += 10
            feedback.append(f"✅ **Authority:** Author attribution found ('{author_tag.get('content')}').")
        else:
            feedback.append("⚠️ **Authority:** No Author meta tag found. LLMs trust verified experts.")

        # --- PARAMETER 7: TOPIC CLARITY (H1) ---
        # Weight: 15
        h1 = soup.find('h1')
        if h1:
            score += 15
            feedback.append("✅ **Topic:** H1 tag is present and clear.")
        else:
            feedback.append("❌ **Topic:** No H1 tag found.")

        return score, feedback

    except Exception as e:
        return 0, [f"❌ Error: {str(e)}"]

# Button Logic
if st.button("Run Advanced Scan"):
    if target_url:
        with st.spinner('Analyzing Robots.txt, Schema, and Content Tokens...'):
            final_score, report = analyze_advanced_aeo(target_url)
        
        # Color Logic
        color_class = "score-low"
        if final_score > 50: color_class = "score-med"
        if final_score > 80: color_class = "score-high"
        
        # Display Score
        st.markdown(f"<h1 style='font-size: 90px;' class='{color_class}'>{final_score}/100</h1>", unsafe_allow_html=True)
        
        # Status
        if final_score < 50:
            st.error("INVISIBLE. Your site blocks AI or lacks the data structure they need.")
        elif final_score < 80:
            st.warning("PARTIALLY VISIBLE. Good for Search 1.0, but missing AEO signals.")
        else:
            st.success("AEO READY. You are optimized for the Generative Web.")
            
        # Report
        st.markdown("### 🔍 Technical Breakdown")
        for item in report:
            st.markdown(f"<div class='metric-box'>{item}</div>", unsafe_allow_html=True)

        # CTA
        st.markdown("---")
        st.markdown("### 🛠 Fix Your Signals")
        st.info("Missing 'llms.txt' or 'FAQ Schema'? The Playbook has the copy-paste code.")
        st.markdown("[**Get the AEO Playbook 2026 ->**](https://adigitalfit.com/products/the-seo-founder-s-playbook-2026-scale-organic-growth-like-a-pro)")

    else:
        st.warning("Please enter a URL.")
