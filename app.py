import os, re, sqlite3, datetime, tempfile, base64
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import httpx
_oc=httpx.Client.__init__; _oa=httpx.AsyncClient.__init__
def _pc(self,*a,**kw): kw.pop("proxies",None); _oc(self,*a,**kw)
def _pa(self,*a,**kw): kw.pop("proxies",None); _oa(self,*a,**kw)
httpx.Client.__init__=_pc; httpx.AsyncClient.__init__=_pa
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs

GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_IDS = {
    "english":  os.getenv("VOICE_ENGLISH",  "pzxut4zZz4GImZNlqQ3H"),
    "hindi":    os.getenv("VOICE_HINDI",    "TRnaQb7q41oL7sV0w6Bu"),
    "gujarati": os.getenv("VOICE_GUJARATI", "y3bFrCRcSPphE8Ksv5BW"),
}
ELEVEN_LANG = {"english": "en", "hindi": "hi"}

BASE_DIR = Path(__file__).parent.resolve()
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)

LANG_SYSTEM = {
    "english": (
        "CRITICAL LANGUAGE RULE: You MUST reply in ENGLISH ONLY. "
        "Every single word of your response must be in English. No exceptions."
    ),
    "hindi": (
        "अत्यंत महत्वपूर्ण भाषा नियम: आपको केवल और केवल हिंदी में जवाब देना है। "
        "आपके जवाब का हर एक शब्द हिंदी में होना चाहिए। "
        "अंग्रेजी में एक भी शब्द मत लिखो। "
        "RERA नंबर, फोन नंबर, कीमतें — ये संख्याएं और कोड यथावत रख सकते हैं "
        "लेकिन बाकी सब हिंदी में होना चाहिए।"
    ),
    "gujarati": (
        "અત્યંત મહત્વપૂર્ણ ભાષા નિયમ: તમારે ફક્ત અને ફક્ત ગુજરાતીમાં જ જવાબ આપવાનો છે. "
        "તમારા જવાબનો દરેક શબ્દ ગુજરાતીમાં હોવો જોઈએ. "
        "અંગ્રેજીમાં એક પણ શબ્દ ન લખો. "
        "RERA નંબર, ફોન નંબર, કિંમતો — આ સંખ્યાઓ અને કોડ યથાવત રાખી શકો છો "
        "પણ બાકી બધું ગુજરાતીમાં હોવું જોઈએ."
    ),
}

LANG_REMINDER = {
    "english":  "REMEMBER: Your entire reply must be in ENGLISH only.",
    "hindi":    "याद रखें: आपका पूरा जवाब केवल हिंदी में होना चाहिए। अंग्रेजी में मत लिखो।",
    "gujarati": "યાદ રાખો: તમારો સંપૂર્ણ જવાબ ફક્ત ગુજરાતીમાં જ હોવો જોઈએ. અંગ્રેજીમાં ન લખો.",
}

KNOWLEDGE_BASE = {
    "north_enclave": """NORTH ENCLAVE — Complete Property Information

LOCATION:
North Enclave is located Next to Vaishnodevi Temple, Nr. Nirma University, S. G. Highway, Khoraj, Ahmedabad.

CONTACT:
Contact Mr. Ronak Thaker at 9979997528 for all North Enclave enquiries.

DISTANCES FROM NORTH ENCLAVE:
- Sabarmati Railway Station: 10 Km
- Proposed Bullet Train Stop / Multimodal Transport Hub: 10 Kms
- Ranip Bus Stop: 9.5 Kms
- KD Multi Specialty Hospital: 300 Mtrs
- Osia Hyper Market: 300 Mts
- McDonald's: 500 Mts
- Zudio: 500 Mts
- Zydus Corporate House: 500 Mts
- Nirma University: 600 Mts
- SGVP: 600 Mts

PROJECT TYPE: Luxurious Apartment project.

APARTMENTS AVAILABLE:
- Project offers 2 BHK and 3 BHK Apartments. Currently ONLY 3 BHK apartments are available. All 2 BHK units are SOLD OUT.
- 3 BHK Carpet Area: 802 & 810 Sq. Ft (RERA Carpet + Balcony & Wash Area)

PROJECT DETAILS:
- Launch Date: 1st November 2015
- Status: Ready to Move In
- Total Land Area: Approximately 14,306 Sq. Mts
- Total Units: 613 units
- Total Floors: 14 Stories
- Total Phases: 2
- Units per Floor: 4
- Model Flat: Available at project site
- Project Approvals: Approved by RERA

RERA NUMBERS:
- PR/GJ/GANDHINAGAR/GANDHINAGAR/AUDA/RAA04324/A1R/211021
- L Block: PR/GJ/GANDHINAGAR/GANDHINAGAR/AUDA/MAA09056/150921

AMENITIES: Lavish Clubhouse, Pickleball Court, Community Hall, Indoor Games, Gym, Swimming Pool, Kids Play Area, Children Library, and many more.

CAR PARKING:
- 3 BHK: Car parking available. Charges: Rs. 1,50,000/- + GST
- 2 BHK: No allotted car parking facility. Team member will explain further.

PRICING:
- 3 BHK Apartments: Starting from Rs. 64,75,000 onwards
- Booking Amount: 10% of the agreement value
- Price Negotiation: NOT possible. Prices are fixed.
- Bank Approvals: Approved from all leading banks including govt, private and NBFC""",

    "amara": """AMARA — Complete Property Information

LOCATION:
Amara is located besides Gokuldham, Eklavya School Road, Shela Extension, Sanathal, Ahmedabad.
Postal Address: Amara, besides Gokuldham, Eklavya School Road, Shela Extension, Sanathal, Ahmedabad - 382210.

CONTACT:
Call +91 8123002555 for all Amara enquiries.

LOCATION HIGHLIGHTS:
Corner Plot on Proposed 80 Ft road so two side open road. Close proximity to posh locality of Gokuldham and Safal Vihan.

DISTANCES FROM AMARA:
- Airport: 25 kms (40 mins)
- Railway Station (Ahmedabad): 15 kms (20 mins)
- Sarkhej Railway Station: 3.5 kms
- Central Bus Station (Ahmedabad): 15 kms (20 mins)
- Nehrunagar Bus Station: 9 kms (12 mins)
- Sahyog General Hospital: 2.5 kms
- Aadarsh Hospital: 2.5 kms
- Sanidhya Multispeciality: 3.8 kms
- Krishna Shalby: 5 kms
- Eklavya School: 0.2 kms
- Lakshya International: 2 kms
- Shanti Asiatic: 3 kms
- Sanand: 7 kms
- Prahladnagar Junction: 7 kms
- YMCA Club: 6 kms
- Sarkhej Cross Road: 5 kms

PROJECT TYPE: Fully residential project.

PROJECT HIGHLIGHTS: Fully Residential Campus with seven 14-storied towers with all modern amenities like Swimming pool, kids pool, club house, multipurpose gaming courts.

APARTMENTS AVAILABLE: Project offers 2 BHK and 3 BHK Apartments.

APARTMENT SIZES:
- 2 BHK RERA Carpet Area: 575 sqft to 588 sqft | Super Built Up Area: 1047 sqft to 1070 sqft
- 3 BHK RERA Carpet Area: 774 sqft to 808 sqft | Super Built Up Area: 1407 sqft to 1469 sqft

PROJECT DETAILS:
- Launch Date: 15th March 2021
- Expected Completion: 31st December 2025
- Total Apartments: 392
- Carpet Area Percentage: approximately 45%
- Total Land Area: 10,334 Sq. Mts (1,11,234 Sq. Ft)
- Total Floors: 14
- Total Towers: 7
- Units per Floor: 4
- Model Flat: Ready to view
- Project Approval: Approved from the concerned authority

RERA NUMBER: PR/GJ/AHMEDABAD/SANAND/AUDA/RAA07702/241120

AMENITIES:
- Kids Play Area, GYM, Open Amphitheatre, Community Hall, Lavish Club House
- Indoor Sports, Multipurpose Gaming Courts, Pets Area
- Swimming Pool, Kids Pool, Yoga Deck
- Aesthetically designed entrance gate with 24x7 security monitoring systems

CAR PARKING: Covered and open car parking provided. No allocated parking charges — ample parking space available.
SOURCE OF WATER: Ground Water.

PRICING:
- Rate: Rs. 6,190/- per sqft on RERA Carpet Area
- Rate: Rs. 3,400/- per sqft on Super Built Up Area
- Preferential Location Charge (PLC): Rs. 100/- per sqft on super built up area
- 2 BHK: Starting from Rs. 35.70 lakhs onwards
- 3 BHK: Starting from Rs. 47.89 lakhs onwards
- Club Membership Charges: NONE
- Maintenance Fee: Rs. 4/- per sqft on Carpet Area for 24 months
- Booking Amount: 10% of Total Consideration
- Price Negotiation: NOT possible.
- Bank Approvals: Approved from major Banks and Financial Institutions""",
}

# =============================================================================
# Database
# =============================================================================
def init_db():
    conn = sqlite3.connect("conversations.db")
    try:
        conn.execute("SELECT property, language FROM chats LIMIT 1")
    except:
        conn.execute("DROP TABLE IF EXISTS chats")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, timestamp TEXT, role TEXT,
            message TEXT, property TEXT, language TEXT)""")
    conn.commit()
    conn.close()

def db_save(sid, role, msg, prop="", lang="english"):
    conn = sqlite3.connect("conversations.db")
    conn.execute("INSERT INTO chats VALUES(NULL,?,?,?,?,?,?)",
                 (sid, datetime.datetime.now().isoformat(), role, msg, prop, lang))
    conn.commit()
    conn.close()

def db_history(sid, lang):
    conn = sqlite3.connect("conversations.db")
    rows = conn.execute(
        "SELECT role, message FROM chats WHERE session_id=? AND language=? ORDER BY id",
        (sid, lang),
    ).fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1]} for r in rows]

# =============================================================================
# Gemini — google.genai new SDK (works on Python 3.11)
# =============================================================================
def ask_gemini(user_msg, history, lang):
    lang_rule     = LANG_SYSTEM.get(lang, LANG_SYSTEM["english"])
    lang_reminder = LANG_REMINDER.get(lang, LANG_REMINDER["english"])
    kb_ne         = KNOWLEDGE_BASE["north_enclave"]
    kb_amara      = KNOWLEDGE_BASE["amara"]

    system_text = f"""{lang_rule}

You are a warm, professional real estate sales assistant for TWO residential projects in Ahmedabad:
1. North Enclave — S.G. Highway, Khoraj (3 BHK, Ready to Move)
2. Amara — Shela Extension, Sanathal (2 & 3 BHK, completion Dec 2025)

==================== NORTH ENCLAVE — FULL KNOWLEDGE BASE ====================
{kb_ne}
=============================================================================

======================= AMARA — FULL KNOWLEDGE BASE ========================
{kb_amara}
=============================================================================

HOW TO ANSWER:
1. PROPERTY DETECTION:
   - Amara / अमारा / અમારા / shela / sanathal / gokuldham / eklavya / 8123002555 / 392 apartments / 7 towers / yoga deck / amphitheatre / 35.70 / 47.89 / 6190 / 3400 → AMARA only.
   - North Enclave / नॉर्थ एन्क्लेव / નોર્થ એન્ક્લેવ / khoraj / vaishnodevi / ronak / 9979997528 / 613 units / pickleball / children library / 64,75,000 / 802 sqft / 810 sqft → NORTH ENCLAVE only.
   - General question → answer BOTH separately.
2. Reproduce all numbers, RERA, phone, distances, areas, prices EXACTLY. Never change them.
3. Use "Rs." for all currency.
4. Warm, clear answers. 2-5 sentences or clean list for distances/amenities.
5. If not in KB: NE contact Mr. Ronak Thaker 9979997528 | Amara: +91 8123002555.
6. NEVER invent any fact.

{lang_reminder}"""

    client = genai.Client(api_key=GEMINI_API_KEY)

    contents = []
    for h in history[-6:]:
        role = "user" if h["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=h["message"])]))

    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=f"{user_msg}\n\n[IMPORTANT — {lang_reminder}]")]
    ))

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_text,
            temperature=0.3,
            max_output_tokens=1024,
        ),
        contents=contents,
    )
    return response.text

# =============================================================================
# TTS / STT
# =============================================================================
def tts(text, lang="english"):
    try:
        client = ElevenLabs(api_key=ELEVENLABS_KEY)
        vid    = VOICE_IDS.get(lang, VOICE_IDS["english"])
        clean  = re.sub(r"[*#_`]", "", text)[:900]
        lc     = ELEVEN_LANG.get(lang)
        kw = dict(
            text=clean, voice_id=vid,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings={"stability":0.5,"similarity_boost":0.85,
                            "style":0.2,"use_speaker_boost":True},
        )
        if lc:
            kw["language_code"] = lc
        return base64.b64encode(b"".join(client.text_to_speech.convert(**kw))).decode()
    except Exception as e:
        print(f"TTS error: {e}"); return None

def stt(filepath, filename):
    client = Groq(api_key=GROQ_API_KEY)
    with open(filepath, "rb") as f:
        r = client.audio.transcriptions.create(
            file=(filename, f), model="whisper-large-v3-turbo", response_format="text")
    return r if isinstance(r, str) else r.text

# =============================================================================
# Routes
# =============================================================================
@app.route("/")
def index(): return app.send_static_file("index.html")

@app.route("/greet", methods=["POST"])
def greet():
    d    = request.json or {}
    sid  = d.get("session_id", "default")
    lang = d.get("language", "english").strip().lower()
    GREETINGS = {
        "english":  "Welcome! I'm your property assistant for North Enclave and Amara — two premium residential projects in Ahmedabad. Ask me anything about either project — location, price, amenities, RERA, booking, and more. How can I help you today?",
        "hindi":    "स्वागत है! मैं नॉर्थ एन्क्लेव और अमारा — अहमदाबाद के दो प्रीमियम आवासीय प्रोजेक्ट्स का आपका सहायक हूँ। आप किसी भी प्रोजेक्ट के बारे में — स्थान, कीमत, सुविधाएं, RERA, बुकिंग — कुछ भी पूछ सकते हैं। मैं आपकी कैसे मदद कर सकता हूँ?",
        "gujarati": "સ્વાગત છે! હું નોર્થ એન્ક્લેવ અને અમારા — અમદાવાદના બે પ્રીમિયમ રહેઠાણ પ્રોજેક્ટ્સ માટે તમારો સહાયક છું. તમે કોઈ પણ પ્રોજેક્ટ વિશે — સ્થળ, ભાવ, સુવિધા, RERA, બુકિંગ — કંઈ પણ પૂછી શકો છો. હું તમને કઈ રીતે મદદ કરી શકું?",
    }
    greeting = GREETINGS.get(lang, GREETINGS["english"])
    db_save(sid, "assistant", greeting, "both", lang)
    return jsonify({"text": greeting, "audio": tts(greeting, lang), "format": "mp3"})

@app.route("/chat", methods=["POST"])
def chat():
    d    = request.json or {}
    msg  = d.get("message", "").strip()
    sid  = d.get("session_id", "default")
    lang = d.get("language", "english").strip().lower()
    if not msg: return jsonify({"error": "empty"}), 400

    db_save(sid, "user", msg, "auto", lang)
    hist = db_history(sid, lang)
    if hist and hist[-1]["role"] == "user":
        hist = hist[:-1]

    try:
        answer = ask_gemini(msg, hist, lang)
    except Exception as e:
        print(f"Gemini error: {e}")
        answer = {
            "english":  "I'm sorry, I encountered an error. Please try again.",
            "hindi":    "मुझे खेद है, एक त्रुटि हुई। कृपया पुनः प्रयास करें।",
            "gujarati": "મને માફ કરો, એક ભૂલ આવી. કૃપા કરી ફરી પ્રયાસ કરો.",
        }.get(lang, "Sorry, please try again.")

    db_save(sid, "assistant", answer, "auto", lang)
    return jsonify({"answer": answer, "audio": tts(answer, lang), "format": "mp3"})

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files: return jsonify({"error": "no audio"}), 400
    f = request.files["audio"]
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            f.save(tmp.name)
        text = stt(tmp.name, f.filename or "audio.webm")
        os.unlink(tmp.name)
        return jsonify({"text": text})
    except Exception as e:
        print(f"STT error: {e}"); return jsonify({"error": str(e)}), 500

@app.route("/history/<session_id>")
def get_history(session_id):
    conn = sqlite3.connect("conversations.db")
    rows = conn.execute(
        "SELECT role, message FROM chats WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    conn.close()
    return jsonify([{"role": r[0], "message": r[1]} for r in rows])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)