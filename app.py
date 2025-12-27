import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
# Page Setup
st.set_page_config(page_title="ADF AEO Scanner", page_icon="🧠", layout="centered")

# Custom Styling
st.markdown("""
    <style>
    .main { background: linear-gradient(145deg, #0f0c29, #302b63, #24243e); color: #ffffff; }
    h1 { color: #00d9ff; text-align: center; }
    .metric-box { background-color: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #5b4fff; }
    .stTextInput>div>div>input { color: #000; }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND FUNCTIONS ---
def save_lead_to_gsheet(email, website, score):
    """Saves the lead to Google Sheets. Requires st.secrets to be set up."""
    try:
        # Define the scope
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Get credentials from Streamlit Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # Authorize client
        client = gspread.authorize(creds)
        
        # Open the sheet (Make sure you share your sheet with the client_email from json)
        sheet = client.open("ADF_Leads").sheet1
        
        # Append Row
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, email, website, score])
        return True
    except Exception as e:
        # If secrets aren't set up, just print to console so app doesn't crash
        print(f"Backend Error (Data not saved): {e}")
        return False

# --- ANALYSIS FUNCTIONS (Same as before) ---
def check_robots_txt(domain):
    try:
        robots_url = f"{domain.scheme}://{domain.netloc}/robots.txt"
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200:
            content = response.text.lower()
            if "disallow: /" in content and ("gptbot" in content or "ccbot" in content):
                return False, "❌ **Critical:** You are blocking AI Bots (GPTBot)."
            return True, "✅ **Crawlability:** AI Bots are allowed."
        return True, "⚠️ **Crawlability:** No robots.txt found."
    except:
        return True, "⚠️ **Crawlability:** Could not verify robots.txt."

def analyze_site(url):
    score = 0
    feedback = []
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        domain = urlparse(url)
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return 0, [f"❌ Connection Failed: {response.status_code}"]
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Robots Check
        is_crawlable, msg = check_robots_txt(domain)
        feedback.append(msg)
        score += 15 if is_crawlable else -10
        
        # 2. Schema Check
        schema_text = str(soup.find_all('script', type='application/ld+json'))
        if "Organization" in schema_text or "Brand" in schema_text:
            score += 25
            feedback.append("✅ **Identity:** Organization Schema detected.")
        else:
            feedback.append("❌ **Identity:** No Organization Schema found.")
            
        if "FAQPage" in schema_text:
            score += 15
            feedback.append("✅ **AEO Signal:** FAQPage Schema found.")
            
        # 3. Content Depth
        word_count = len(soup.get_text(strip=True).split())
        if word_count > 600:
            score += 15
            feedback.append(f"✅ **Depth:** Rich content ({word_count} words).")
        else:
            feedback.append(f"❌ **Depth:** Thin content ({word_count} words).")
            
        # 4. H1 Check
        if soup.find('h1'):
            score += 15
            feedback.append("✅ **Topic:** H1 tag present.")
        else:
            feedback.append("❌ **Topic:** No H1 tag.")
            
        # 5. Author Check
        if soup.find("meta", attrs={"name": "author"}):
            score += 15
            feedback.append("✅ **Authority:** Author tag found.")
        else:
            feedback.append("⚠️ **Authority:** No Author tag.")

        return max(0, min(100, score)), feedback

    except Exception as e:
        return 0, [f"❌ Error: {str(e)}"]

# --- FRONTEND UI ---
st.title("Advanced AEO Scanner 2.0")
st.markdown("Unlock your **AI Readiness Score** for 2026.")

# THE FORM (Gating the Results)
with st.form("lead_capture_form"):
    url_input = st.text_input("Website URL (e.g., https://yoursite.com)")
    email_input = st.text_input("Your Work Email")
    
    submitted = st.form_submit_button("Analyze & Get Score")

if submitted:
    if not url_input or "http" not in url_input:
        st.error("Please enter a valid URL starting with http:// or https://")
    elif not email_input or "@" not in email_input:
        st.error("Please enter a valid email address to view results.")
    else:
        # 1. Show Spinner
        with st.spinner(f"Scanning {url_input} for AEO signals..."):
            final_score, report = analyze_site(url_input)
            
            # 2. Save Lead to Backend
            is_saved = save_lead_to_gsheet(email_input, url_input, final_score)
            
            # 3. Display Results
            color = "#ff4b4b" if final_score < 50 else "#00d9ff"
            st.markdown(f"<h1 style='font-size: 80px; color: {color};'>{final_score}/100</h1>", unsafe_allow_html=True)
            
            if final_score < 50:
                st.error("INVISIBLE TO AI.")
            elif final_score < 80:
                st.warning("PARTIALLY VISIBLE.")
            else:
                st.success("AI READY.")

            st.markdown("### 🔍 Technical Breakdown")
            for item in report:
                st.markdown(f"<div class='metric-box'>{item}</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.info("Want to fix these errors? Download the Playbook.")
            st.markdown("[**Get the AEO Playbook 2026 ->**](https://adigitalfit.com/products/the-seo-founder-s-playbook-2026-scale-organic-growth-like-a-pro)")
