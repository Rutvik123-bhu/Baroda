import os, re, sqlite3, datetime, tempfile, base64, requests
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

# =============================================================================
# API Keys — set all four in your .env file
# =============================================================================
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",       "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY",      "")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY",  "")   # English only
SARVAM_KEY     = os.getenv("SARVAM_API_KEY",      "")   # Hindi + Gujarati

# =============================================================================
# TTS provider config
# =============================================================================

# ── ElevenLabs (English only) ─────────────────────────────────────────────────
ELEVEN_VOICE_EN  = os.getenv("VOICE_ENGLISH", "FaqthkZu1EWxXxUFbAfb")

# ── Sarvam AI — bulbul:v3, handles numbers/currency natively ─────────────────
SARVAM_TTS_URL   = "https://api.sarvam.ai/text-to-speech"
SARVAM_MODEL     = "bulbul:v3"

# Hindi  — roopa: warm female, recommended for Hindi customer support
SARVAM_HINDI_SPEAKER    = os.getenv("SARVAM_HINDI_SPEAKER",    "roopa")
SARVAM_HINDI_LANG       = "hi-IN"

# Gujarati — pooja: encouraging female, built for assistance flows
SARVAM_GUJARATI_SPEAKER = os.getenv("SARVAM_GUJARATI_SPEAKER", "pooja")
SARVAM_GUJARATI_LANG    = "gu-IN"


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
- Launch Date: 1/11/2015
- Status: Ready to Move In
- Total Land Area: Approximately 14,306 Sq. Mts
- Total Units: 613 units
- Total Floors: 14 Stories
- Total Phases: 2
- Units per Floor: 4
- Model Flat: Yes, we have a model flat at our project site
- Project Approvals: Approved by RERA

RERA NUMBERS:
- PR/GJ/GANDHINAGAR/GANDHINAGAR/AUDA/RAA04324/A1R/211021
- L Block:: PR/GJ/GANDHINAGAR/GANDHINAGAR/AUDA/MAA09056/150921

AMENITIES: Lavish Clubhouse, Pickle ball Court, Community Hall, Indoor Games, Gym, Swimming Pool, Kids Play Area, Children Library, and many more.

CAR PARKING:
- 3 BHK: Car parking facility available. Charges: Rs. 1,50,000/- + GST
- 2 BHK: We regret to inform you that we do not have any allotted car parking facility for the 2 BHK option. For more details, one of our team members will provide further explanation.

PRICING:
- 3 BHK Apartments: Starting from Rs. 64,75,000 onwards
- Booking Amount: 10% of the agreement value
- Price Negotiation: Sorry, prices are fixed.
- Banks Affiliated: Approved from all leading banks including govt, private and NBFC
- Bank Approvals: Project is approved from all leading banks including govt, private and NBFC""",

    "amara": """AMARA — Complete Property Information

LOCATION:
Amara is located besides Gokuldham, Eklavya School Road, Shela Extension, Sanathal, Ahmedabad.
Postal Address: Amara, besides Gokuldham, Eklavya School Road, Shela Extension, Sanathal, Ahmedabad - 382210.

CONTACT:
For more information, request you to please call on +91 8123002555.

LOCATION HIGHLIGHTS:
Corner Plot on Proposed 80 Ft road so two side open road, close proximity with Posh locality of Gokuldham and Safal Vihan.

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

PROJECT HIGHLIGHTS: Fully Residential Campus with seven 14-storied towers, with all the modern amenities like Swimming pool, kids pool, club house, multipurpose gaming courts etc.

APARTMENTS AVAILABLE: Project offers 2 and 3 BHK Apartments. May I know your preference please?

APARTMENT SIZES:
- 2 BHK RERA Carpet Area: 575 sqft to 588 sqft | Super Built Up Area: 1047 sqft to 1070 sqft
- 3 BHK RERA Carpet Area: 774 sqft to 808 sqft | Super Built Up Area: 1407 sqft to 1469 sqft

PROJECT DETAILS:
- Launch Date: 15th March 2021
- Expected Completion: 31st Dec 2025
- Total Apartments: 392
- Carpet Area Percentage: approximately 45%
- Total Land Area: 10334 Sq. Mts (1,11,234 Sq. Ft)
- Total Floors: 14
- Total Towers: 7
- Units per Floor: 4
- Model Flat: Model Flat is ready to view
- Project Approval: Project is approved from the concerned authority

RERA NUMBER: PR/GJ/AHMEDABAD/SANAND/AUDA/RAA07702/241120

AMENITIES:
- Kid's Play Area, GYM, Open Amphitheatre, Community Hall, Lavish Club House
- Indoor Sports, Multipurpose Gaming Courts, Pet's Area
- Swimming Pool, Kid's Pool, Yoga Deck
- Aesthetically designed entrance gate with 24x7 security monitoring systems

CAR PARKING: We provide covered and open car parking. No allocated parking charges — ample parking space available.
SOURCE OF WATER: Source of Water is through Ground Water.

PRICING:
- Rate: Rs. 6,190/- per sqft on RERA Carpet Area
- Rate: Rs. 3,400/- per sqft on Super Built Up Area
- Preferential Location Charge (PLC): Rs. 100/- per Sq.ft on Super Built Up Area
- 2 BHK: Starting from Rs. 35.70 lakhs onwards
- 3 BHK: Starting from Rs. 47.89 lakhs onwards
- Club Membership Charges: No Club membership charges
- Maintenance Fee: Rs. 4/- per sqft on Carpet Area for 24 months
- Booking Amount: 10% of Total Consideration
- Price Negotiation: Sorry, we do not negotiate on price.
- Bank Approvals: Project is approved from major Banks / Financial Institutions""",
}

# =============================================================================
# Database
# =============================================================================
def init_db():
    conn = sqlite3.connect("conversations.db")
    try:
        conn.execute("SELECT property, language FROM chats LIMIT 1")
    except Exception:
        conn.execute("DROP TABLE IF EXISTS chats")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, timestamp TEXT, role TEXT,
            message TEXT, property TEXT, language TEXT)""")
    conn.commit()
    conn.close()

def db_save(sid, role, msg, prop="", lang="english"):
    try:
        conn = sqlite3.connect("conversations.db")
        conn.execute("INSERT INTO chats VALUES(NULL,?,?,?,?,?,?)",
                     (sid, datetime.datetime.now().isoformat(), role, msg, prop, lang))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB save error: {e}")

def db_history(sid, lang):
    try:
        conn = sqlite3.connect("conversations.db")
        rows = conn.execute(
            "SELECT role, message FROM chats WHERE session_id=? AND language=? ORDER BY id",
            (sid, lang),
        ).fetchall()
        conn.close()
        return [{"role": r[0], "message": r[1]} for r in rows]
    except Exception as e:
        print(f"DB history error: {e}")
        return []

# =============================================================================
# Gemini
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
5. If not in KB: NE: Mr. Ronak Thaker 9979997528 | Amara: +91 8123002555.
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
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_text,
            temperature=0.3,
            max_output_tokens=1024,
        ),
        contents=contents,
    )
    return response.text

# =============================================================================
# TTS helpers
# =============================================================================

def _wav_to_mp3_b64(wav_bytes: bytes) -> str:
    """
    Convert WAV bytes to base64 MP3.
    Falls back to base64 WAV if pydub/ffmpeg is not installed —
    modern browsers play WAV fine so this is a safe fallback.
    """
    try:
        from pydub import AudioSegment
        import io
        seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        buf = io.BytesIO()
        seg.export(buf, format="mp3", bitrate="128k")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return base64.b64encode(wav_bytes).decode()

# =============================================================================
# TTS — ElevenLabs  (English ONLY)
# Number pre-processor applied here since ElevenLabs needs help with numbers.
# =============================================================================

# Digit → English word for phone number reading
_DIGIT_WORDS = {
    '0': 'zero', '1': 'one',   '2': 'two',   '3': 'three', '4': 'four',
    '5': 'five', '6': 'six',   '7': 'seven', '8': 'eight', '9': 'nine',
}

def _phone_to_words(digits: str) -> str:
    return ' '.join(_DIGIT_WORDS[d] for d in digits if d in _DIGIT_WORDS)

def _to_indian_english(n: int) -> str:
    """6475000 -> '64 lakh 75 thousand'  |  6190 -> '6 thousand 1 hundred 90'"""
    if n == 0: return "0"
    parts = []
    crore = n // 10_000_000; n = n % 10_000_000
    lakh  = n // 100_000;    n = n % 100_000
    thou  = n // 1_000;      n = n % 1_000
    hund  = n // 100;        rest = n % 100
    if crore: parts.append(f"{crore} crore")
    if lakh:  parts.append(f"{lakh} lakh")
    if thou:  parts.append(f"{thou} thousand")
    if hund:  parts.append(f"{hund} hundred")
    if rest:  parts.append(str(rest))
    return " ".join(parts)

def _fix_number_en(m: re.Match) -> str:
    raw    = m.group(0)
    digits = raw.replace(",", "")
    if not digits.isdigit(): return raw
    if len(digits) >= 10: return _phone_to_words(digits)   # phone
    n = int(digits)
    if n >= 1_000: return _to_indian_english(n)            # price/area
    return digits                                           # small numbers

def _prepare_english_tts(text: str) -> str:
    """Pre-process for ElevenLabs English voice."""
    text = re.sub(r"[*#_`]", "", text)[:900]
    # +91 phone numbers
    text = re.sub(
        r"(\+91)[\s\-]?(\d{10})",
        lambda m: "plus nine one " + _phone_to_words(m.group(2)),
        text,
    )
    # all other number tokens
    text = re.sub(r"\b[\d,]+\b", _fix_number_en, text)
    return text

def tts_elevenlabs(text: str) -> str | None:
    """ElevenLabs TTS for English. Returns base64 mp3 or None."""
    try:
        if not ELEVENLABS_KEY:
            print("TTS-EL: No API key"); return None
        client = ElevenLabs(api_key=ELEVENLABS_KEY)
        clean  = _prepare_english_tts(text)
        kw = dict(
            text=clean,
            voice_id=ELEVEN_VOICE_EN,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings={
                "stability":         0.5,
                "similarity_boost":  0.85,
                "style":             0.2,
                "use_speaker_boost": True,
            },
            language_code="en",
        )
        audio_bytes = b"".join(client.text_to_speech.convert(**kw))
        return base64.b64encode(audio_bytes).decode()
    except Exception as e:
        print(f"TTS-EL error: {e}"); return None

# =============================================================================
# TTS — Sarvam AI  (Hindi + Gujarati)
# bulbul:v3 normalises numbers, currencies, dates natively — no preprocessing.
#   Hindi    → roopa  (hi-IN) — warm female, recommended for customer support
#   Gujarati → pooja  (gu-IN) — encouraging female, assistance flows
# =============================================================================
def tts_sarvam(text: str, lang: str) -> str | None:
    """Sarvam AI TTS for Hindi/Gujarati. Returns base64 mp3 or None."""
    try:
        if not SARVAM_KEY:
            print("TTS-Sarvam: No API key"); return None

        # Choose speaker + language code
        if lang == "hindi":
            speaker   = SARVAM_HINDI_SPEAKER
            lang_code = SARVAM_HINDI_LANG
        else:  # gujarati
            speaker   = SARVAM_GUJARATI_SPEAKER
            lang_code = SARVAM_GUJARATI_LANG

        # Strip markdown only — Sarvam handles numbers natively
        clean = re.sub(r"[*#_`]", "", text)[:2500]

        payload = {
            "inputs":               [clean],
            "target_language_code": lang_code,
            "speaker":              speaker,
            "model":                SARVAM_MODEL,
            "pace":                 1.0,
            "enable_preprocessing": True,   # handles Rs., %, phone numbers, dates
        }
        headers = {
            "api-subscription-key": SARVAM_KEY,
            "Content-Type":         "application/json",
        }

        resp = requests.post(SARVAM_TTS_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

        b64wav    = resp.json()["audios"][0]
        wav_bytes = base64.b64decode(b64wav)
        return _wav_to_mp3_b64(wav_bytes)

    except Exception as e:
        print(f"TTS-Sarvam error ({lang}): {e}"); return None

# =============================================================================
# TTS — unified router
# =============================================================================
def tts(text: str, lang: str = "english") -> tuple:
    """
    Route to correct TTS provider:
      english   → ElevenLabs  (FaqthkZu1EWxXxUFbAfb)
      hindi     → Sarvam AI   (roopa,  hi-IN, bulbul:v3)
      gujarati  → Sarvam AI   (pooja,  gu-IN, bulbul:v3)

    Returns (base64_audio | None, format_string)
    """
    if lang == "english":
        return tts_elevenlabs(text), "mp3"
    else:
        return tts_sarvam(text, lang), "mp3"

# =============================================================================
# STT
# =============================================================================
def stt(filepath, filename):
    client = Groq(api_key=GROQ_API_KEY)
    with open(filepath, "rb") as f:
        r = client.audio.transcriptions.create(
            file=(filename, f),
            model="whisper-large-v3-turbo",
            response_format="text"
        )
    return r if isinstance(r, str) else r.text

# =============================================================================
# Routes
# =============================================================================
@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/greet", methods=["POST"])
def greet():
    try:
        d    = request.json or {}
        sid  = d.get("session_id", "default")
        lang = d.get("language", "english").strip().lower()

        GREETINGS = {
            "english":  "Welcome! I'm your property assistant for North Enclave and Amara — two premium residential projects in Ahmedabad. Ask me anything about either project — location, price, amenities, RERA, booking, and more. How can I help you today?",
            "hindi":    "स्वागत है! मैं नॉर्थ एन्क्लेव और अमारा — अहमदाबाद के दो प्रीमियम आवासीय प्रोजेक्ट्स का आपका सहायक हूँ। आप किसी भी प्रोजेक्ट के बारे में — स्थान, कीमत, सुविधाएं, RERA, बुकिंग — कुछ भी पूछ सकते हैं। मैं आपकी कैसे मदद कर सकता हूँ?",
            "gujarati": "સ્વાગત છે! હું નોર્થ એન્ક્લેવ અને અમારા — અમદાવાદના બે પ્રીમિયમ રહેઠાણ પ્રોજેક્ટ્સ માટે તમારો સહાયક છું. તમે કોઈ પણ પ્રોજેક્ટ વિશે — સ્થળ, ભાવ, સુવિધા, RERA, બુકિંગ — કંઈ પણ પૂછી શકો છો. હું તમને કઈ રીતે મદદ કરી શકું?",
        }
        greeting   = GREETINGS.get(lang, GREETINGS["english"])
        db_save(sid, "assistant", greeting, "both", lang)
        audio, fmt = tts(greeting, lang)
        return jsonify({"text": greeting, "audio": audio, "format": fmt})

    except Exception as e:
        print(f"Greet route error: {e}")
        return jsonify({"text": "Welcome! Ask me about North Enclave or Amara.",
                        "audio": None, "format": "mp3"}), 200

@app.route("/chat", methods=["POST"])
def chat():
    try:
        d    = request.json or {}
        msg  = d.get("message", "").strip()
        sid  = d.get("session_id", "default")
        lang = d.get("language", "english").strip().lower()

        if not msg:
            return jsonify({"error": "empty"}), 400

        db_save(sid, "user", msg, "auto", lang)
        hist = db_history(sid, lang)
        if hist and hist[-1]["role"] == "user":
            hist = hist[:-1]

        # Gemini
        try:
            answer = ask_gemini(msg, hist, lang)
        except Exception as e:
            print(f"Gemini error: {e}")
            answer = {
                "english":  "I'm sorry, I encountered an error. Please try again.",
                "hindi":    "मुझे खेद है, एक त्रुटि हुई। कृपया पुनः प्रयास करें।",
                "gujarati": "મને માફ કરો, એક ભૂલ આવી. કૃपा करी ફरी प्रयास करो.",
            }.get(lang, "Sorry, please try again.")

        db_save(sid, "assistant", answer, "auto", lang)

        audio, fmt = tts(answer, lang)
        return jsonify({"answer": answer, "audio": audio, "format": fmt})

    except Exception as e:
        print(f"Chat route error: {e}")
        lang_safe = (request.json or {}).get("language", "english")
        return jsonify({
            "answer": {
                "english":  "Server error. Please try again.",
                "hindi":    "सर्वर त्रुटि। कृपया पुनः प्रयास करें।",
                "gujarati": "સर्वर ભૂল. કृपा करी ફरी प्रयास करो.",
            }.get(lang_safe, "Server error."),
            "audio": None,
            "format": "mp3",
        }), 200

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "no audio"}), 400
    f = request.files["audio"]
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            f.save(tmp.name)
        text = stt(tmp.name, f.filename or "audio.webm")
        os.unlink(tmp.name)
        return jsonify({"text": text})
    except Exception as e:
        print(f"STT error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/history/<session_id>")
def get_history(session_id):
    conn = sqlite3.connect("conversations.db")
    rows = conn.execute(
        "SELECT role, message FROM chats WHERE session_id=? ORDER BY id",
        (session_id,)
    ).fetchall()
    conn.close()
    return jsonify([{"role": r[0], "message": r[1]} for r in rows])

# =============================================================================
# Startup
# =============================================================================
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Running on port {port}")
    app.run(host="0.0.0.0", port=port)