import os, re, sqlite3, datetime, tempfile, base64
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import httpx
_oc=httpx.Client.__init__; _oa=httpx.AsyncClient.__init__
def _pc(self,*a,**kw): kw.pop("proxies",None); _oc(self,*a,**kw)
def _pa(self,*a,**kw): kw.pop("proxies",None); _oa(self,*a,**kw)
httpx.Client.__init__=_pc; httpx.AsyncClient.__init__=_pa
from flask import Flask,request,jsonify
from flask_cors import CORS
from groq import Groq
import google.generativeai as genai
from elevenlabs.client import ElevenLabs

GROQ_API_KEY=os.getenv("GROQ_API_KEY","")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
ELEVENLABS_KEY=os.getenv("ELEVENLABS_API_KEY","")
VOICE_IDS={
    "english": os.getenv("VOICE_ENGLISH","pzxut4zZz4GImZNlqQ3H"),
    "hindi":   os.getenv("VOICE_HINDI","TRnaQb7q41oL7sV0w6Bu"),
    "gujarati":os.getenv("VOICE_GUJARATI","y3bFrCRcSPphE8Ksv5BW")
}
ELEVEN_LANG={"english":"en","hindi":"hi"}

BASE_DIR=Path(__file__).parent.resolve()
app=Flask(__name__,static_folder=str(BASE_DIR),static_url_path="")
CORS(app)

# =============================================================================
# KNOWLEDGE BASE — Every single Q&A from Chat Board Script (Amara & North Enclave)
# =============================================================================
KNOWLEDGE_BASE = {

    # =========================================================================
    # NORTH ENCLAVE
    # =========================================================================
    "north_enclave": [

        # --- LOCATION & CONNECTIVITY ---
        "Q: Where is North Enclave located? | A: North Enclave is located Next to Vaishnodevi Temple, Nr. Nirma University, S. G. Highway, Khoraj, Ahmedabad.",

        "Q: Distance from nearby railway station and bus stand? | A: Distance from the project: Sabarmati Railway Station - 10 Km. Proposed bullet train stop/multimodal transport hub - 10 kms. Ranip Bus Stop - 9.5 Kms.",

        "Q: What are the nearby vicinities and distances from North Enclave? | A: Distance from the project: KD Multi Specialty Hospital - 300 Mtrs. Osia Hyper Market - 300 Mts. McDonald's - 500 Mts. Zudio - 500 Mts. Zydus Corporate House - 500 Mts. Nirma University - 600 Mts. SGVP - 600 Mts.",

        "Q: Who is the contact person for North Enclave? | A: For more details regarding this project, please contact Mr. Ronak Thaker at 9979997528.",

        # --- PROJECT DETAILS ---
        "Q: What type of project is North Enclave? | A: North Enclave is a Luxurious Apartment project.",

        "Q: What type of apartments are available at North Enclave? | A: Project offers 2 BHK and 3 BHK Apartments. Currently only 3 BHK apartments are available.",

        "Q: Are 2 BHK apartments available at North Enclave? | A: All 2 BHK units are sold out.",

        "Q: What is the carpet area of 3 BHK at North Enclave? | A: Carpet Area of 3 BHK is 802 & 810 Sq. Ft (RERA Carpet + Balcony & Wash Area).",

        "Q: When was North Enclave launched? | A: North Enclave was launched on 1st November 2015.",

        "Q: What is the completion or possession date of North Enclave? | A: North Enclave is ready to move in.",

        "Q: What is the total land area of North Enclave? | A: Total land area of the project is Approx. 14,306 Sq. Mts.",

        "Q: How many total units does North Enclave have? | A: Project offers 613 units in total.",

        "Q: How many floors does North Enclave have? | A: Total number of Floors - 14 Stories.",

        "Q: How many phases does North Enclave have? | A: Total number of Phases - 2.",

        "Q: How many units are on each floor at North Enclave? | A: We have 4 units on each floor.",

        "Q: Is there a model flat at North Enclave? | A: Yes, we have a model flat at our project site.",

        "Q: Is North Enclave RERA approved? What are the project approvals? | A: Project is approved by RERA.",

        "Q: Is car parking available for 3 BHK at North Enclave? | A: We have car parking facility for 3 BHK option.",

        "Q: Is car parking available for 2 BHK at North Enclave? | A: We regret to inform you that we do not have any allotted car parking facility for the 2 BHK option. For more details on this matter, one of our team members will provide further explanation.",

        "Q: What is the RERA number of North Enclave? | A: RERA Numbers: PR/GJ/GANDHINAGAR/GANDHINAGAR/AUDA/RAA04324/A1R/211021. L Block: PR/GJ/GANDHINAGAR/GANDHINAGAR/AUDA/MAA09056/150921.",

        "Q: What amenities are available at North Enclave? | A: Amenities offered at North Enclave are: Lavish Clubhouse, Pickleball Court, Community Hall, Indoor Games, Gym, Swimming Pool, Kids Play Area, Children Library and many more.",

        # --- PRICING & BOOKING ---
        "Q: What is the approximate cost or price of apartments at North Enclave? | A: Approximate cost at North Enclave: 3 BHK Apartments start from Rs. 64,75,000 onwards.",

        "Q: Which banks are affiliated with or have approved North Enclave? | A: Project is approved from all leading banks including govt, private and NBFC.",

        "Q: Is price negotiable at North Enclave? | A: Sorry, prices are fixed. No negotiation.",

        "Q: What are the car parking charges at North Enclave? | A: Car Parking Charges - Rs. 1,50,000/- + GST.",

        "Q: What is the booking amount for North Enclave? | A: Booking Amount is 10% of the agreement value.",

        "Q: Are bank loans available for North Enclave? | A: Project is approved from all leading banks including govt, private and NBFC.",
    ],

    # =========================================================================
    # AMARA
    # =========================================================================
    "amara": [

        # --- LOCATION & CONNECTIVITY ---
        "Q: Where is Amara located? | A: Amara is located besides Gokuldham, Eklavya School Road, Shela Extension, Sanathal, Ahmedabad.",

        "Q: Who is the contact person for Amara? How to contact Amara? | A: For more information on this aspect, please call +91 8123002555.",

        "Q: What is the postal address of Amara? | A: Amara, besides Gokuldham, Eklavya School Road, Shela Extension, Sanathal, Ahmedabad - 382210.",

        "Q: What is the distance from Amara to airport, railway station, and bus stand? | A: Distance from Amara: Airport - 25 kms (40 mins). Railway Station (Ahmedabad) - 15 kms (20 mins). Sarkhej Railway Station - 3.5 kms. Central Bus Station (Ahmedabad) - 15 kms (20 mins). Nehrunagar Bus Station - 9 kms (12 mins).",

        "Q: What are the nearest hospitals to Amara? | A: Distance from Amara to nearest hospitals: Sahyog General Hospital - 2.5 kms. Aadarsh Hospital - 2.5 kms. Sanidhya Multispeciality - 3.8 kms. Krishna Shalby - 5 kms.",

        "Q: What are the nearest schools and educational institutions to Amara? | A: Distance from Amara to nearest educational institutions: Eklavya School - 0.2 kms. Lakshya International - 2 kms. Shanti Asiatic - 3 kms.",

        "Q: What are the nearby vicinities and distances from Amara? | A: Distance from Amara: Sanand - 7 kms. Prahladnagar Junction - 7 kms. YMCA Club - 6 kms. Sarkhej Cross Road - 5 kms.",

        "Q: What are the location highlights of Amara? | A: Amara is a Corner Plot on Proposed 80 Ft road with two side open road, with close proximity to the posh locality of Gokuldham and Safal Vihan.",

        # --- PROJECT DETAILS ---
        "Q: What are the project highlights of Amara? | A: Amara is a Fully Residential Campus with seven 14-storied towers, with all modern amenities like Swimming pool, kids pool, club house, multipurpose gaming courts etc.",

        "Q: What type of project is Amara? | A: Amara is a fully residential project.",

        "Q: What type of flats are available at Amara? | A: Project offers 2 BHK and 3 BHK Apartments.",

        "Q: What is the area of 2 BHK at Amara? | A: Area of 2 BHK (RERA Carpet area) ranges from 575 sqft to 588 sqft. Super built up area ranges from 1047 sqft to 1070 sqft.",

        "Q: What is the area of 3 BHK at Amara? | A: Area of 3 BHK (RERA Carpet area) ranges from 774 sqft to 808 sqft. Super built up area ranges from 1407 sqft to 1469 sqft.",

        "Q: How many total apartments does Amara have? | A: Project has 392 Apartments.",

        "Q: What is the carpet area percentage at Amara? | A: Percentage of Carpet area is approx. 45%.",

        "Q: What is the total land area of Amara? | A: Total land area of the project is 10,334 Sq. Mts (1,11,234 Sq. Ft).",

        "Q: How many floors does Amara have? | A: Project has 14 floors.",

        "Q: How many towers or blocks does Amara have? | A: Project has 7 towers.",

        "Q: How many units are on each floor at Amara? | A: We have 4 units on each floor.",

        "Q: Is Amara approved? What are the project approvals? | A: Project is approved from the concerned authority.",

        "Q: When was Amara launched? | A: Project was launched on 15th March 2021.",

        "Q: What is the completion or possession date of Amara? | A: Amara is expected to complete by 31st December 2025.",

        "Q: Is there a model flat at Amara? | A: Yes, model flat is ready to view.",

        "Q: Is car parking available at Amara? | A: We provide covered and open car parking.",

        "Q: What is the source of water at Amara? | A: Source of Water is through Ground Water.",

        "Q: What amenities are available at Amara? | A: Amenities offered at Amara are: Kids Play Area, GYM, Open Amphitheatre, Community Hall, Lavish Club House, Indoor Sports, Multipurpose Gaming Courts, Pets Area, Swimming Pool, Kids Pool, Yoga Deck, Aesthetically designed entrance gate with 24x7 security monitoring systems.",

        "Q: What is the RERA number of Amara? | A: RERA Number Registration No. - PR/GJ/AHMEDABAD/SANAND/AUDA/RAA07702/241120.",

        # --- PRICING & BOOKING ---
        "Q: What is the rate per sqft at Amara? | A: Rate per sqft at Amara is Rs. 6,190/- on RERA Carpet Area and Rs. 3,400/- on Super Built Up Area. Preferential Location Charge (PLC) is Rs. 100/- per Sq.ft on super built up area.",

        "Q: What is the basic cost or price of apartments at Amara? | A: Basic cost at Amara: 2 BHK ranges from Rs. 35.70 lakhs onwards. 3 BHK ranges from Rs. 47.89 lakhs onwards.",

        "Q: Is price negotiable at Amara? | A: Sorry, we do not negotiate on price.",

        "Q: What are the club membership charges at Amara? | A: No club membership charges.",

        "Q: What is the maintenance fee at Amara? | A: Maintenance fee is Rs. 4/- per sqft on Carpet Area for 24 months.",

        "Q: What are the car parking charges at Amara? | A: As we do not provide allocated car parking, we do not charge for it. However, there is ample car parking space available.",

        "Q: What is the booking amount for Amara? | A: Booking amount is 10% of Total Consideration.",

        "Q: Are bank loans available for Amara? Which banks have approved Amara? | A: Project is approved from major Banks and Financial Institutions.",
    ]
}

# =============================================================================
# Search KB — keyword overlap scoring
# =============================================================================
def search_kb(query, prop, top_k=8):
    qw = set(re.findall(r'\w+', query.lower()))
    scored = []
    for chunk in KNOWLEDGE_BASE.get(prop, []):
        cw = set(re.findall(r'\w+', chunk.lower()))
        score = len(qw & cw)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

# =============================================================================
# Database
# =============================================================================
def init_db():
    conn = sqlite3.connect("conversations.db")
    try:
        conn.execute("SELECT property,language FROM chats LIMIT 1")
    except:
        print("Upgrading DB...")
        conn.execute("DROP TABLE IF EXISTS chats")
    conn.execute("""CREATE TABLE IF NOT EXISTS chats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, timestamp TEXT, role TEXT,
        message TEXT, property TEXT, language TEXT)""")
    conn.commit(); conn.close()

def db_save(sid, role, msg, prop="", lang="english"):
    conn = sqlite3.connect("conversations.db")
    conn.execute("INSERT INTO chats VALUES(NULL,?,?,?,?,?,?)",
                 (sid, datetime.datetime.now().isoformat(), role, msg, prop, lang))
    conn.commit(); conn.close()

def db_history(sid):
    conn = sqlite3.connect("conversations.db")
    rows = conn.execute(
        "SELECT role,message FROM chats WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1]} for r in rows]

# =============================================================================
# Gemini AI
# =============================================================================
LANG_RULE = {
    "english":  "Reply ONLY in English.",
    "hindi":    "केवल हिंदी में जवाब दें।",
    "gujarati": "માત્ર ગુજરાતીમાં જ જવાબ આપો."
}
PROP_NAMES = {"north_enclave": "North Enclave", "amara": "Amara"}
CONTACT    = {"north_enclave": "Mr. Ronak Thaker at 9979997528", "amara": "+91 8123002555"}

def ask_gemini(user_msg, kb_results, history, prop, lang):
    genai.configure(api_key=GEMINI_API_KEY)
    model   = genai.GenerativeModel("gemini-2.5-flash")
    pname   = PROP_NAMES.get(prop, "our project")
    contact = CONTACT.get(prop, "our sales team")
    ctx     = "\n\n".join(kb_results) if kb_results else ""

    system = f"""You are a warm and professional real estate sales assistant for {pname}, Ahmedabad.
{LANG_RULE.get(lang, 'Reply in English.')}

KNOWLEDGE BASE — answer STRICTLY and ONLY from what is written below. Do NOT invent, assume, or add any information not present here:
{ctx if ctx else "No relevant information found in the knowledge base for this query."}

STRICT RULES:
1. Answer ONLY about {pname} using the knowledge base above.
2. Keep answers concise — 2 to 4 sentences. Preserve all numbers, RERA numbers, phone numbers, distances, areas, and prices EXACTLY as written in the knowledge base — never round or alter them.
3. Use "Rs." for all currency values.
4. If the user's question is NOT covered anywhere in the knowledge base, reply: "I'm sorry, I don't have that specific information. For detailed assistance, please contact {contact}."
5. If the user asks about a topic completely unrelated to {pname} (e.g. other properties, general topics), reply: "I can only assist with queries related to {pname}. Is there anything about our project I can help you with?"
6. Never invent or guess prices, areas, dates, names, distances, or any other fact.
7. If the user asks a question that has a partial match, answer only the part that is covered in the knowledge base and say you don't have info on the rest.
"""

    gh   = [{"role": "user" if h["role"] == "user" else "model", "parts": [h["message"]]}
            for h in history[-6:]]
    chat = model.start_chat(history=gh)
    return chat.send_message(f"{system}\n\nUser: {user_msg}").text

# =============================================================================
# TTS / STT
# =============================================================================
def tts(text, lang="english"):
    try:
        client = ElevenLabs(api_key=ELEVENLABS_KEY)
        vid    = VOICE_IDS.get(lang, VOICE_IDS["english"])
        clean  = re.sub(r'[*#_`]', '', text)[:900]
        lc     = ELEVEN_LANG.get(lang)
        kw = dict(
            text=clean, voice_id=vid,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings={"stability": 0.5, "similarity_boost": 0.85,
                            "style": 0.2, "use_speaker_boost": True}
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
def index():
    return app.send_static_file("index.html")

@app.route("/greet", methods=["POST"])
def greet():
    d    = request.json or {}
    sid  = d.get("session_id", "default")
    prop = d.get("property", "north_enclave")
    lang = d.get("language", "english")
    G = {
        "north_enclave": {
            "english":  "Welcome! I'm your assistant for North Enclave — a luxurious ready-to-move apartment project on S.G. Highway, Khoraj, Ahmedabad. It offers spacious 3 BHK apartments. How can I help you today?",
            "hindi":    "स्वागत है! मैं नॉर्थ एन्क्लेव का आपका सहायक हूँ — एस.जी. हाइवे, खोराज, अहमदाबाद पर एक शानदार रेडी-टू-मूव प्रोजेक्ट। यहाँ विशाल 3 BHK अपार्टमेंट उपलब्ध हैं। मैं आपकी कैसे मदद कर सकता हूँ?",
            "gujarati": "સ્વાગત છે! હું નોર્થ એન્ક્લેવ માટે તમારો સહાયક છું — S.G. હાઇવે, ખોરજ, અમદાવાદ પર ભવ્ય રેડી-ટૂ-મૂવ પ્રોજેક્ટ. અહીં વિશાળ 3 BHK ઉપલબ્ધ છે. હું તમને કઈ રીતે મદદ કરી શકું?"
        },
        "amara": {
            "english":  "Welcome! I'm your assistant for Amara — a premium residential project in Shela Extension, Sanathal, Ahmedabad, offering 2 and 3 BHK apartments. How can I help you today?",
            "hindi":    "स्वागत है! मैं अमारा का आपका सहायक हूँ — शेला एक्सटेंशन, सनाथल, अहमदाबाद में एक प्रीमियम आवासीय प्रोजेक्ट जो 2 BHK और 3 BHK अपार्टमेंट प्रदान करता है। मैं आपकी कैसे मदद कर सकता हूँ?",
            "gujarati": "સ્વાગત છે! હું અમારા માટે તમારો સહાયક છું — શેળા એક્સ્ટેન્શન, સાણઠ, અમદાવાદ ખાતે પ્રીમિયમ 2 BHK અને 3 BHK પ્રોજેક્ટ. આજે હું તમને કઈ રીતે મદદ કરી શકું?"
        }
    }
    greeting = G.get(prop, {}).get(lang, "Welcome! How can I help you today?")
    db_save(sid, "assistant", greeting, prop, lang)
    audio = tts(greeting, lang)
    return jsonify({"text": greeting, "audio": audio, "format": "mp3"})

@app.route("/chat", methods=["POST"])
def chat():
    d    = request.json or {}
    msg  = d.get("message", "").strip()
    sid  = d.get("session_id", "default")
    prop = d.get("property", "north_enclave")
    lang = d.get("language", "english")
    if not msg:
        return jsonify({"error": "empty"}), 400
    db_save(sid, "user", msg, prop, lang)
    kb   = search_kb(msg, prop)
    hist = db_history(sid)[:-1]
    try:
        answer = ask_gemini(msg, kb, hist, prop, lang)
    except Exception as e:
        answer = f"Error: {e}"
    db_save(sid, "assistant", answer, prop, lang)
    audio = tts(answer, lang)
    return jsonify({"answer": answer, "audio": audio, "format": "mp3"})

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
    return jsonify(db_history(session_id))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)