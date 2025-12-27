import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
st.set_page_config(page_title="ADF AEO Scanner", page_icon="🧠", layout="centered")

st.markdown("""
    <style>
    .main { background: linear-gradient(145deg, #0f0c29, #302b63, #24243e); color: #ffffff; }
    h1 { color: #00d9ff; text-align: center; font-family: 'Helvetica Neue', sans-serif; }
    .metric-box { background-color: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #5b4fff; }
    .score-high { color: #00d9ff; }
    .score-med { color: #f2c94c; }
    .score-low { color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND: GOOGLE SHEETS ---
def save_lead_to_gsheet(email, website, score):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Load secrets safely
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("ADF_Leads").sheet1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, email, website, score])
            return True
        else:
            print("Secrets not configured.")
            return False
    except Exception as e:
        print(f"Backend Error: {e}")
        return False

# --- 10-POINT ANALYSIS LOGIC ---
def analyze_10_point_aeo(url):
    score = 0
    feedback = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }

    try:
        domain = urlparse(url)
        start_time = time.time()
        
        # 1. CONNECTIVITY
        response = requests.get(url, headers=headers, timeout=15)
        load_duration = time.time() - start_time
        
        if response.status_code == 403:
             return 0, ["❌ **Critical:** Security Block (403 Forbidden)."]
        if response.status_code != 200:
            return 0, [f"❌ Connection Failed: Status {response.status_code}"]

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- CHECK 1: ROBOTS PERMISSION (10 pts) ---
        try:
            robots_url = f"{domain.scheme}://{domain.netloc}/robots.txt"
            rob_resp = requests.get(robots_url, timeout=5)
            if rob_resp.status_code == 200:
                txt = rob_resp.text.lower()
                if "disallow: /" in txt and ("gptbot" in txt or "ccbot" in txt):
                    feedback.append("❌ **1. Bot Access:** You are Blocking AI.")
                else:
                    score += 10
                    feedback.append("✅ **1. Bot Access:** AI Bots allowed.")
            else:
                score += 10 # Assume open if no file
                feedback.append("✅ **1. Bot Access:** No robots.txt (Assumed Open).")
        except:
            score += 5
            feedback.append("⚠️ **1. Bot Access:** Could not verify.")

        # --- CHECK 2: LLMS.TXT (10 pts) ---
        try:
            llms_url = f"{domain.scheme}://{domain.netloc}/llms.txt"
            llms_resp = requests.get(llms_url, timeout=3)
            if llms_resp.status_code == 200:
                score += 10
                feedback.append("✅ **2. AI Standard:** Found 'llms.txt'.")
            else:
                feedback.append("⚠️ **2. AI Standard:** No 'llms.txt' file.")
        except:
            pass

        # --- CHECK 3: ENTITY SCHEMA (15 pts) ---
        schema_tags = soup.find_all('script', type='application/ld+json')
        schema_text = ""
        for s in schema_tags: schema_text += str(s.string)
        
        if "Organization" in schema_text or "Brand" in schema_text:
            score += 15
            feedback.append("✅ **3. Identity:** Organization Schema found.")
        else:
            feedback.append("❌ **3. Identity:** No Organization Schema.")

        # --- CHECK 4: FAQ SCHEMA (10 pts) ---
        if "FAQPage" in schema_text:
            score += 10
            feedback.append("✅ **4. Q&A Capability:** FAQPage Schema found.")
        else:
            feedback.append("⚠️ **4. Q&A Capability:** No FAQ Schema.")

        # --- CHECK 5: SOCIAL SIGNALS (10 pts) ---
        # Look for links to linkedin, twitter, etc.
        page_links = str(soup.find_all('a', href=True)).lower()
        if "linkedin.com" in page_links or "twitter.com" in page_links or "instagram.com" in page_links:
            score += 10
            feedback.append("✅ **5. Knowledge Graph:** Social profiles linked.")
        else:
            feedback.append("⚠️ **5. Knowledge Graph:** No social signals found.")

        # --- CHECK 6: CONTENT DEPTH (10 pts) ---
        text_content = soup.get_text(strip=True)
        word_count = len(text_content.split())
        if word_count > 600:
            score += 10
            feedback.append(f"✅ **6. Content Depth:** Rich data ({word_count} words).")
        else:
            feedback.append(f"❌ **6. Content Depth:** Thin content ({word_count} words).")

        # --- CHECK 7: AUTHOR AUTHORITY (5 pts) ---
        if soup.find("meta", attrs={"name": "author"}):
            score += 5
            feedback.append("✅ **7. Authority:** Author tag found.")
        else:
            feedback.append("⚠️ **7. Authority:** No Author tag.")

        # --- CHECK 8: FRESHNESS (10 pts) ---
        # Look for date metadata
        meta_html = str(soup.find_all('meta')).lower()
        if "published_time" in meta_html or "modified_time" in meta_html or "date" in meta_html:
            score += 10
            feedback.append("✅ **8. Freshness:** Date stamps detected.")
        else:
            feedback.append("⚠️ **8. Freshness:** No date metadata found.")

        # --- CHECK 9: TOPIC CLARITY (10 pts) ---
        if soup.find('h1'):
            score += 10
            feedback.append("✅ **9. Topic:** H1 tag is clear.")
        else:
            feedback.append("❌ **9. Topic:** Missing H1 tag.")

        # --- CHECK 10: VELOCITY (10 pts) ---
        if load_duration < 1.5:
            score += 10
            feedback.append(f"✅ **10. Speed:** Fast ({round(load_duration, 2)}s).")
        elif load_duration < 3.0:
            score += 5
            feedback.append(f"⚠️ **10. Speed:** Average ({round(load_duration, 2)}s).")
        else:
            feedback.append(f"❌ **10. Speed:** Slow ({round(load_duration, 2)}s).")

        return max(0, min(100, score)), feedback

    except Exception as e:
        return 0, [f"❌ Error: {str(e)}"]

# --- FRONTEND UI ---
st.title("Advanced AEO Scanner 2.0")
st.markdown("Unlock your **AI Readiness Score** for 2026.")

with st.form("lead_capture_form"):
    url_input = st.text_input("Website URL (e.g., https://yoursite.com)")
    email_input = st.text_input("Your Work Email")
    submitted = st.form_submit_button("Analyze & Get Score")

if submitted:
    if not url_input or "http" not in url_input:
        st.error("Please enter a valid URL starting with http:// or https://")
    elif not email_input or "@" not in email_input:
        st.error("Please enter a valid email.")
    else:
        with st.spinner(f"Running 10-Point AEO Audit on {url_input}..."):
            final_score, report = analyze_10_point_aeo(url_input)
            
            # Save to Google Sheet
            save_lead_to_gsheet(email_input, url_input, final_score)
            
            # Display Score
            color_class = "score-low"
            if final_score > 50: color_class = "score-med"
            if final_score > 80: color_class = "score-high"
            
            st.markdown(f"<h1 style='font-size: 90px;' class='{color_class}'>{final_score}/100</h1>", unsafe_allow_html=True)
            
            if final_score < 50:
                st.error("INVISIBLE TO AI. Your site blocks AI or lacks structure.")
            elif final_score < 80:
                st.warning("PARTIALLY VISIBLE. Missing key AEO signals.")
            else:
                st.success("AEO READY. You are optimized for the Generative Web.")

            st.markdown("### 🔍 10-Point Technical Audit")
            for item in report:
                st.markdown(f"<div class='metric-box'>{item}</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.info("Want to fix these errors? Get the templates in the Playbook.")
            st.markdown("[**Get the AEO Playbook 2026 ->**](https://adigitalfit.com/products/the-seo-founder-s-playbook-2026-scale-organic-growth-like-a-pro)")
