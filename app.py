
import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import json
import re

# Page Config
st.set_page_config(page_title="ADF AEO Scanner", page_icon="🔍", layout="centered")

# Custom Styling to match your Brand (Dark Mode)
st.markdown("""
    <style>
    .main {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        color: #ffffff;
    }
    h1 { color: #00d9ff; text-align: center; }
    h2, h3 { color: #5b4fff; }
    .stTextInput>div>div>input {
        color: #000;
    }
    .metric-box {
        background-color: rgba(255,255,255,0.05);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("AEO Readiness Scanner 2026")
st.markdown("<p style='text-align: center; color: #a8a8b3;'>Analyze your visibility for ChatGPT, Perplexity, and Gemini.</p>", unsafe_allow_html=True)

# Input
url = st.text_input("Enter Website URL (e.g., https://example.com)")

def analyze_aeo(url):
    score = 0
    feedback = []
    
    # 1. Connectivity Check
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        load_time = time.time() - start_time
        
        if response.status_code != 200:
            return 0, ["❌ Could not access site. Check URL."]
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. CHECK: Load Speed (Critical for AI Crawlers)
        # Weight: 10 points
        if load_time < 1.5:
            score += 10
            feedback.append("✅ **Speed:** Excellent load time for AI bots.")
        elif load_time < 3:
            score += 5
            feedback.append("⚠️ **Speed:** Acceptable, but could be faster.")
        else:
            feedback.append("❌ **Speed:** Too slow. AI bots may time out.")

        # 3. CHECK: Schema Markup (The Language of LLMs)
        # Weight: 40 points (Most Important)
        schema_tags = soup.find_all('script', type='application/ld+json')
        found_org = False
        found_product = False
        
        if schema_tags:
            score += 20 # Base points for having any schema
            for tag in schema_tags:
                try:
                    data = json.loads(tag.string)
                    # Check for Organization or Brand
                    if isinstance(data, dict):
                        if data.get('@type') in ['Organization', 'Corporation', 'Brand', 'LocalBusiness']:
                            found_org = True
                        if data.get('@type') in ['Product', 'Service']:
                            found_product = True
                    # Handle lists of schema
                    elif isinstance(data, list):
                        for item in data:
                            if item.get('@type') in ['Organization', 'Corporation', 'Brand']:
                                found_org = True
                except:
                    pass
            
            if found_org:
                score += 20
                feedback.append("✅ **Identity:** 'Organization' Schema found. LLMs know who you are.")
            else:
                feedback.append("❌ **Identity:** No 'Organization' Schema found. You are hard for AI to verify.")
        else:
            feedback.append("❌ **Identity:** Critical Fail. No JSON-LD Schema detected.")

        # 4. CHECK: AEO Structure (Inverted Pyramid)
        # Weight: 30 points
        h1 = soup.find('h1')
        if h1:
            score += 10
            feedback.append(f"✅ **Topic Clarity:** H1 tag found: '{h1.get_text(strip=True)[:30]}...'")
            
            # Check the first paragraph content
            # Finds the first p tag after the h1
            first_p = h1.find_next('p')
            if first_p:
                text = first_p.get_text(strip=True)
                word_count = len(text.split())
                
                # AI likes concise answers (under 50 words) immediately after header
                if 10 < word_count < 60:
                    score += 20
                    feedback.append("✅ **AEO Structure:** Direct answer detected immediately after H1.")
                else:
                    score += 5
                    feedback.append("⚠️ **AEO Structure:** Intro paragraph is too long or too short. Optimize for 'Direct Answers'.")
            else:
                feedback.append("❌ **AEO Structure:** No content found immediately after H1.")
        else:
            feedback.append("❌ **Topic Clarity:** No H1 tag found. AI cannot determine page topic.")

        # 5. CHECK: Metadata (Title & Desc)
        # Weight: 20 points
        if soup.title:
            score += 10
        if soup.find("meta", attrs={"name": "description"}):
            score += 10
            feedback.append("✅ **Meta:** Title and Description present.")
        else:
            feedback.append("⚠️ **Meta:** Missing Meta Description.")

        return score, feedback

    except Exception as e:
        return 0, [f"❌ Error analyzing site: {str(e)}"]

# Button
if st.button("Analyze My Site"):
    if url:
        with st.spinner('Scanning Knowledge Graph Signals...'):
            final_score, report = analyze_aeo(url)
        
        # Display Score
        st.markdown(f"<h1 style='font-size: 72px; margin-bottom: 0;'>{final_score}/100</h1>", unsafe_allow_html=True)
        
        # Result Interpretation
        if final_score < 50:
            st.error("INVISIBLE TO AI. Your site lacks the basic language (Schema) needed for recommendation.")
        elif final_score < 80:
            st.warning("PARTIALLY VISIBLE. You have basics, but content isn't optimized for Answer Engines.")
        else:
            st.success("AI READY. Your technical foundation is strong.")
            
        # Display Checklist
        st.markdown("### Analysis Report:")
        for item in report:
            st.markdown(f"<div class='metric-box'>{item}</div>", unsafe_allow_html=True)
            
        # Call to Action
        st.markdown("---")
        st.markdown("### 🚀 Fix Your Score")
        st.info("Want the exact templates to reach 100/100? Download the SEO Founder's Playbook 2026.")
        st.markdown("[**Get the Playbook ->**](https://adigitalfit.com/products/the-seo-founder-s-playbook-2026-scale-organic-growth-like-a-pro)")

    else:
        st.warning("Please enter a URL.")
