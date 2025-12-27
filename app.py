import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import time

# Page Config
st.set_page_config(page_title="ADF AEO Scanner", page_icon="🔍", layout="centered")

# Custom Styling (Dark Mode)
st.markdown("""
    <style>
    .main {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        color: #ffffff;
    }
    h1 { color: #00d9ff; text-align: center; font-size: 2.5rem; }
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
    .success-text { color: #00d9ff; font-weight: bold; }
    .fail-text { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("AEO Readiness Scanner 2026")
st.markdown("<p style='text-align: center; color: #a8a8b3;'>Analyze your visibility for ChatGPT, Perplexity, and Gemini.</p>", unsafe_allow_html=True)

# Input
url = st.text_input("Enter Website URL (include https://)", placeholder="https://adigitalfit.com")

def analyze_aeo(target_url):
    score = 0
    feedback = []
    
    # "Fake" Browser Headers to bypass simple anti-bot blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        # 1. CONNECTIVITY CHECK
        response = requests.get(target_url, headers=headers, timeout=15)
        
        # Check if we got blocked
        if response.status_code == 403:
            return 0, ["❌ **Security Block:** The website blocked our scanner (403 Forbidden). This often happens with heavy firewalls (Cloudflare). Try a different URL or check your firewall settings."]
        
        if response.status_code != 200:
            return 0, [f"❌ **Connection Failed:** Status Code {response.status_code}"]

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. SPEED CHECK
        # We give partial points just for being accessible
        score += 10 
        feedback.append("✅ **Access:** Website is accessible to crawlers.")

        # 3. SCHEMA CHECK (The most common failure point)
        schema_tags = soup.find_all('script', type='application/ld+json')
        found_org = False
        
        if schema_tags:
            for tag in schema_tags:
                if "Organization" in tag.text or "Brand" in tag.text or "Corporation" in tag.text:
                    found_org = True
                    break
            
            if found_org:
                score += 30
                feedback.append("✅ **Identity:** 'Organization' Schema found. (Strong Signal)")
            else:
                score += 10 # Points for having SOME schema, even if not Org
                feedback.append("⚠️ **Identity:** Schema found, but no 'Organization' or 'Brand' entity detected.")
        else:
            feedback.append("❌ **Identity:** No JSON-LD Schema found. You are invisible to the Knowledge Graph.")

        # 4. CONTENT STRUCTURE (H1 Check)
        h1 = soup.find('h1')
        if h1:
            score += 20
            h1_text = h1.get_text(strip=True)
            feedback.append(f"✅ **Topic Clarity:** H1 tag detected: '{h1_text[:40]}...'")
        else:
            feedback.append("❌ **Topic Clarity:** No H1 tag found. AI cannot understand the page topic.")

        # 5. METADATA CHECK
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            score += 20
            feedback.append("✅ **Meta:** Description tag is present.")
        else:
            feedback.append("❌ **Meta:** Missing Meta Description.")
            
        # 6. SOCIAL/AUTHORITY CHECK
        # Scan links for common social platforms
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        socials = [l for l in links if 'linkedin.com' in l or 'twitter.com' in l or 'instagram.com' in l or 'youtube.com' in l]
        
        if len(socials) > 0:
            score += 20
            feedback.append("✅ **Authority:** Social media signals detected.")
        else:
            feedback.append("⚠️ **Authority:** No social links found on homepage. Harder to verify 'Entity'.")

        return score, feedback

    except Exception as e:
        return 0, [f"❌ Error: {str(e)}"]

# Button Logic
if st.button("Analyze My Site"):
    if url:
        with st.spinner('Scanning Knowledge Graph Signals...'):
            final_score, report = analyze_aeo(url)
        
        # Display Score (Big & Bold)
        color = "#ff4b4b" if final_score < 50 else "#00d9ff"
        st.markdown(f"<h1 style='font-size: 80px; color: {color}; margin-bottom: 0;'>{final_score}/100</h1>", unsafe_allow_html=True)
        
        # Status Message
        if final_score < 50:
            st.error("INVISIBLE TO AI. Your site lacks the basic language needed for recommendation.")
        elif final_score < 80:
            st.warning("PARTIALLY VISIBLE. You have the basics, but are missing key signals.")
        else:
            st.success("AI READY. Your technical foundation is strong.")
            
        # Detailed Report
        st.markdown("### Analysis Report:")
        for item in report:
            st.markdown(f"<div class='metric-box'>{item}</div>", unsafe_allow_html=True)

        # Call to Action
        st.markdown("---")
        st.markdown("### 🚀 Fix Your Score")
        st.info("Want the templates to reach 100/100? Download the SEO Founder's Playbook 2026.")
        st.markdown("[**Get the Playbook ->**](https://adigitalfit.com/products/the-seo-founder-s-playbook-2026-scale-organic-growth-like-a-pro)")
        
    else:
        st.warning("Please enter a valid URL (including https://).")
