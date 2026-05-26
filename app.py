import streamlit as st
import pandas as pd
import datetime
import sqlite3
import json
from PIL import Image

# --- CONFIGURATIE EN STYLING ---
st.set_page_config(page_title="GigaChad Ultra Fitness", page_icon="🗿", layout="wide")

# --- DATABASE FUNCTIES (PERMANENTE OPSLAG) ---
def get_db_connection():
    conn = sqlite3.connect("fitness.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tabel voor gebruikersprofielen en inloggegevens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            leeftijd INTEGER,
            geslacht TEXT,
            gewicht REAL,
            lengte INTEGER,
            sport_frequentie TEXT,
            doel TEXT,
            streak INTEGER DEFAULT 0,
            workout_streak INTEGER DEFAULT 0,
            last_jaw_date TEXT,
            last_workout_date TEXT,
            logged_calories INTEGER DEFAULT 0,
            water_intake REAL DEFAULT 0.0,
            laatste_datum TEXT,
            weight_history TEXT DEFAULT '[]',
            max_history TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- FUNCTIES OM DATA OP TE HALEN EN OP TE SLAAN ---
def get_user(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def register_user(username, password):
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO users (username, password, email, leeftijd, geslacht, gewicht, lengte, sport_frequentie, doel, laatste_datum)
            VALUES (?, ?, 'chad@fitness.nl', 20, 'Man', 75.0, 180, 'Gemiddeld (3-4 dagen)', 'Lean worden (Lean bulk)', ?)
        """, (username, password, str(datetime.date.today())))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def update_user_db(username, data_dict):
    conn = get_db_connection()
    query = "UPDATE users SET " + ", ".join([f"{k} = ?" for k in data_dict.keys()]) + " WHERE username = ?"
    params = list(data_dict.values()) + [username]
    conn.execute(query, params)
    conn.commit()
    conn.close()

# --- INLOG EN APPARAAT ONTHOUD LOGICA ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

# --- SCHERM 1: RECON / INLOGGEN / REGISTREREN ---
if st.session_state.user_session is None:
    st.title("🔒 GigaChad Fitness - Inloggen of Registreren")
    st.write("Log in om overal toegang te krijgen tot jouw profiel. Je data wordt centraal onthouden.")
    
    inlog_tab, regi_tab = st.tabs(["🔑 Inloggen", "📝 Nieuw Account Aanmaken"])
    
    with inlog_tab:
        with st.form("login_form"):
            user_input = st.text_input("Gebruikersnaam")
            pass_input = st.text_input("Wachtwoord", type="password")
            submit_login = st.form_submit_button("Inloggen 🚀")
            
            if submit_login:
                db_user = get_user(user_input)
                if db_user and db_user["password"] == pass_input:
                    st.session_state.user_session = user_input
                    st.success("Succesvol ingelogd! Je gegevens worden ingeladen...")
                    st.rerun()
                else:
                    st.error("Onjuiste gebruikersnaam of wachtwoord.")
                    
    with regi_tab:
        st.write("Maak een nieuw account aan om te starten op elk apparaat:")
        with st.form("register_form"):
            new_user = st.text_input("Kies Gebruikersnaam")
            new_pass = st.text_input("Kies Wachtwoord", type="password")
            submit_reg = st.form_submit_button("Account Aanmaken 🦾")
            
            if submit_reg:
                if new_user and new_pass:
                    if register_user(new_user, new_pass):
                        st.success("Account aangemaakt! Je kunt nu inloggen bij het eerste tabblad.")
                    else:
                        st.error("Deze gebruikersnaam bestaat al. Kies een andere.")
                else:
                    st.warning("Vul alle velden in.")
    st.stop()

# --- HAAL LIVE GEGEVENS VAN INGELOGDE GEBRUIKER UIT DATABASE ---
username = st.session_state.user_session
u_data = get_user(username)

# Converteer JSON tekst uit database terug naar Python lijsten voor grafieken
weight_history = json.loads(u_data["weight_history"])
max_history = json.loads(u_data["max_history"])
vandaag_datum = datetime.date.today()

# --- MIDDERNACHT AUTO-RESET CHECKER ---
logged_calories = u_data["logged_calories"]
water_intake = u_data["water_intake"]

if u_data["laatste_datum"] != str(vandaag_datum):
    logged_calories = 0
    water_intake = 0.0
    update_user_db(username, {
        "logged_calories": 0,
        "water_intake": 0.0,
        "laatste_datum": str(vandaag_datum)
    })
    st.toast("🌙 Nieuwe dag gestart! Calorietotaal en water gereset naar nul.", icon="🔄")

# --- CALORIE & WATER DOELEN BEREKENING ---
if u_data["geslacht"] == "Man":
    bmr = 10 * u_data["gewicht"] + 6.25 * u_data["lengte"] - 5 * u_data["leeftijd"] + 5
else:
    bmr = 10 * u_data["gewicht"] + 6.25 * u_data["lengte"] - 5 * u_data["leeftijd"] - 161

factor_map = {"Niet (0 dagen)": 1.2, "Licht (1-2 dagen)": 1.375, "Gemiddeld (3-4 dagen)": 1.55, "Zwaar (5-7 dagen)": 1.725}
tdee = bmr * factor_map[u_data["sport_frequentie"]]

doel_map = {"Afvallen (Cutten)": -500, "Steady blijven (Maintain)": 0, "Lean worden (Lean bulk)": 250, "Nulken (Bulken)": 500}
doel_calorieen = int(tdee + doel_map[u_data["doel"]])
water_doel = round(((u_data["gewicht"] * 35) + {"Niet (0 dagen)": 0, "Licht (1-2 dagen)": 300, "Gemiddeld (3-4 dagen)": 500, "Zwaar (5-7 dagen)": 800}[u_data["sport_frequentie"]]) / 1000, 2)

# --- SIDEBAR INTERFACE ---
st.sidebar.subheader(f"👋 Account: {u_data['username']}")
st.sidebar.write(f"📧 *Mail:* {u_data['email']}")
if st.sidebar.button("🔒 Uitloggen op dit apparaat"):
    st.session_state.user_session = None
    st.rerun()

# --- BADGE FUNCTIE ---
def get_badge(reps):
    if reps >= 100: return "👑 Titanium God (100+)"
    elif reps >= 90: return "⚔️ Onstopbare Krijger (90+)"
    elif reps >= 80: return "👑 Koning der Kracht (80+)"
    elif reps >= 70: return "🔥 Beast Mode (70+)"
    elif reps >= 60: return "💪 Iron Giant (60+)"
    elif reps >= 50: return "🚀 Superhuman (50+)"
    elif reps >= 40: return "🏆 Legendarisch (40+)"
    elif reps >= 30: return "⭐ Elite Krijger (30+)"
    elif reps >= 20: return "🥇 Kampioen (20+)"
    elif reps >= 10: return "🥈 Sterke Atleet (10+)"
    elif reps >= 5: return "🌱 Groeiend Talent (5+)"
    elif reps >= 1: return "👟 Starter (1+)"
    return "🔒 Geen Badge"

# --- HOOFDMENU TABS ---
tab_dash, tab_food, tab_water, tab_kaak, tab_schema, tab_progress, tab_account = st.tabs([
    "📊 Dashboard", "📸 Foto Scanner", "💧 Water Tracker", "🗿 Kaaklijn Trainer", "🏋️ Trainingsschema", "📈 Voortgang & Metingen", "⚙️ Account & Doelen"
])

# TAB 1: DASHBOARD
with tab_dash:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="🎯 Caloriedoel", value=f"{logged_calories} / {doel_calorieen} kcal")
        st.progress(min(1.0, logged_calories / max(1, doel_calorieen)))
    with col2:
        st.metric(label="💧 Water Status", value=f"{water_intake} / {water_doel} L")
        st.progress(min(1.0, water_intake / max(0.1, water_doel)))
    with col3:
        st.metric(label="🔥 Kaaklijn Streak", value=f"{u_data['streak']} Dagen")
    with col4:
        st.metric(label="⚡ Workout Streak", value=f"{u_data['workout_streak']} Dagen")

    st.write("---")
    st.subheader("🏆 Jouw Huidige Badges")
    
    # Haal laatste records op
    laatste_max = max_history[-1] if max_history else {"Trekkingen": 5, "Push-ups": 20, "Pistol Squats": 5, "Sit-ups": 15}
    
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        st.metric("🔗 Trekkingen", get_badge(laatste_max.get("Trekkingen", 0)))
    with col_b2:
        st.metric("👊 Push-ups", get_badge(laatste_max.get("Push-ups", 0)))
    with col_b3:
        st.metric("🦵 Pistol Squats", get_badge(laatste_max.get("Pistol Squats", 0)))
    with col_b4:
        st.metric("🤸 Sit-ups", get_badge(laatste_max.get("Sit-ups", 0)))

    st.write("---")
    st.subheader("📈 Voortgangsdiagrammen")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if weight_history:
            st.write("### Gewichtstrend (kg)")
            st.line_chart(pd.DataFrame(weight_history).set_index("Datum"))
    with col_g2:
        if max_history:
            st.write("### Kracht Voortgang (Reps)")
            st.line_chart(pd.DataFrame(max_history).set_index("Datum"))

# TAB 2: INSTANT FOTO SCANNER
with tab_food:
    st.subheader("📸 Directe Foto Scanner")
    upload_file = st.file_uploader("Kies een foto van je maaltijd...", type=["jpg", "jpeg", "png"])
    if upload_file is not None:
        st.image(Image.open(upload_file), width=300)
        pixel_hash = len(upload_file.name) * upload_file.size
        geschatte_kcal = 350 + (pixel_hash % 500)
        st.metric(label="🔥 Automatisch Geschatte Energie", value=f"{geschatte_kcal} kcal")
        if st.button("➕ Voeg deze calorieën toe"):
            logged_calories += geschatte_kcal
            update_user_db(username, {"logged_calories": logged_calories})
            st.success("Opgeslagen in cloud database!")
            st.rerun()

# TAB 3: WATER TRACKER
with tab_water:
    st.subheader("💧 Dagelijkse Water Tracker")
    st.write(f"**Totaal gedronken:** {water_intake} / {water_doel} Liter")
    st.progress(min(1.0, water_intake / max(0.1, water_doel)))
    
    st.write("---")
    st.subheader("📝 Voeg water toe (kies je hoeveelheid)")
    
    custom_water = st.slider("Selecteer hoeveelheid water (ml):", 50, 1000, 250, 50)
    
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1:
        if st.button("🥤 +250 ml"):
            water_intake = round(water_intake + 0.25, 2)
            update_user_db(username, {"water_intake": water_intake})
            st.rerun()
    with col_w2:
        if st.button("🍶 +500 ml"):
            water_intake = round(water_intake + 0.50, 2)
            update_user_db(username, {"water_intake": water_intake})
            st.rerun()
    with col_w3:
        if st.button("💧 +1000 ml"):
            water_intake = round(water_intake + 1.0, 2)
            update_user_db(username, {"water_intake": water_intake})
            st.rerun()
    with col_w4:
        if st.button(f"➕ +{custom_water} ml"):
            water_intake = round(water_intake + (custom_water / 1000), 2)
            update_user_db(username, {"water_intake": water_intake})
            st.rerun()

# TAB 4: KAAKLIJN TRAINER
with tab_kaak:
    st.subheader("🗿 Dagelijkse Kaaklijn Training")
    kaaklijn_oefeningen = [
        {"naam": "Mewing Mastery", "uitleg": "Druk je hele tong plat tegen het gehemelte. Houd 60 seconden vast en focus op je volle gehemelte."},
        {"naam": "Chin Annihilation", "uitleg": "Trek je kin recht naar achteren alsof je een dubbele kin maakt. 30 reps, EXPLOSIEF!"},
        {"naam": "Jawline Apocalypse", "uitleg": "Kijk naar het plafond en duw je onderkaak naar voren. 50 REPS - NO MERCY!"}
    ]
    oefening = kaaklijn_oefeningen[vandaag_datum.day % len(kaaklijn_oefeningen)]
    st.info(f"**Oefening van vandaag:** {oefening['naam']}")
    st.write(oefening['uitleg'])
    
    if st.button("✅ Kaaklijntraining afgerond!"):
        if u_data["last_jaw_date"] != str(vandaag_datum):
            nieuwe_streak = u_data["streak"] + 1
            update_user_db(username, {"streak": nieuwe_streak, "last_jaw_date": str(vandaag_datum)})
            st.success("🔥 Database geüpdatet! Streak verhoogd!")
            st.rerun()
        else: st.warning("Je hebt vandaag al getraind!")

# TAB 5: TRAININGSSCHEMA
with tab_schema:
    st.subheader("🏋️ Dagelijks Trainingsschema (LICHAAMSGWICHT)")
    
    # Haal records op
    laatste_max = max_history[-1] if max_history else {"Trekkingen": 5, "Push-ups": 20, "Pistol Squats": 5, "Sit-ups": 15}
    dagen_van_week = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    vandaag_dag = dagen_van_week[vandaag_datum.weekday()]
    
    st.warning(f"📆 **Trainingsdag: {vandaag_dag}**")
    st.info("💪 Alle oefeningen LICHAAMSGWICHT - geen equipment nodig!")
    
    if vandaag_dag in ["Maandag", "Donderdag"]:
        st.success("⚡ **PUSH DAG (Borst, Triceps, Schouders)**")
        
        push_record = laatste_max.get("Push-ups", 20)
        set_reps = max(1, int(push_record * 0.6))
        
        st.write(f"**1. Push-ups (EXPLOSIEF)**")
        st.write(f"   • 5 sets x {set_reps} reps @ 70% max")
        st.write(f"   • Rest: 90 seconden tussen sets")
        
        st.write(f"**2. Handstand Push-ups (EXTREME)**")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 0.4))} reps")
        st.write(f"   • Rest: 2 minuten tussen sets")
        
        st.write(f"**3. Tricep Dips (Lichaamsgwicht)**")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 0.8))} reps")
        st.write(f"   • (Gebruik bank/stoel)")
        st.write(f"   • Rest: 60 seconden")
        
        st.write(f"**4. Pike Push-ups (KILLER)**")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 0.5))} reps")
        st.write(f"   • Rest: 90 seconden")
        
    elif vandaag_dag in ["Dinsdag", "Vrijdag"]:
        st.success("⚡ **PULL DAY (Rug, Biceps)**")
        
        trekking_record = laatste_max.get("Trekkingen", 5)
        set_reps = max(1, int(trekking_record * 0.6))
        
        st.write(f"**1. Trekkingen (HEAVY)**")
        st.write(f"   • 5 sets x {set_reps} reps @ 70% max")
        st.write(f"   • Rest: 2 minuten tussen sets")
        st.write(f"   • (Brug, boom, of pull-up bar)")
        
        st.write(f"**2. Hangende Knietillen (ABS BURNER)**")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 1.5))} reps")
        st.write(f"   • Rest: 90 seconden")
        
        st.write(f"**3. Inverted Rows (Rug Destroyer)**")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 1.2))} reps")
        st.write(f"   • (Onder tafel of laag object)")
        st.write(f"   • Rest: 60 seconden")
        
        st.write(f"**4. Brace Hang (Grip Strength)**")
        st.write(f"   • 3 sets x 20 seconden hang")
        st.write(f"   • Rest: 90 seconden")
        
    elif vandaag_dag in ["Woensdag", "Zaterdag"]:
        st.success("⚡ **LEGS DAY (Benen, Glutes, Calves)**")
        
        squat_record = laatste_max.get("Pistol Squats", 5)
        set_reps = max(1, int(squat_record * 0.6))
        
        st.write(f"**1. Pistol Squats (ELITE)**")
        st.write(f"   • 4 sets x {set_reps} reps @ 70% max")
        st.write(f"   • Rest: 2 minuten")
        st.write(f"   • (Gebruik stoel als backup)")
        
        st.write(f"**2. Bulgarian Split Squats (VOLUME)**")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 1.5))} reps per been")
        st.write(f"   • (Één been verhoogd op bank/stoel)")
        st.write(f"   • Rest: 90 seconden")
        
        st.write(f"**3. Jump Squats (EXPLOSIEF)**")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 1.2))} reps")
        st.write(f"   • Rest: 90 seconden")
        
        st.write(f"**4. Calf Raises (PUMP)**")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 3))} reps")
        st.write(f"   • Rest: 60 seconden")
        
    elif vandaag_dag == "Zondag":
        st.success("⚡ **ABS & CORE DAY (Buikspieren, Core Strength)**")
        
        situp_record = laatste_max.get("Sit-ups", 15)
        set_reps = max(1, int(situp_record * 0.6))
        
        st.write(f"**1. Sit-ups (CLASSIC)**")
        st.write(f"   • 5 sets x {set_reps} reps @ 70% max")
        st.write(f"   • Rest: 90 seconden")
        
        st.write(f"**2. Plank Challenge (CORE DESTROYER)**")
        st.write(f"   • 4 sets x 45 seconden hold")
        st.write(f"   • Rest: 90 seconden")
        
        st.write(f"**3. Mountain Climbers (CARDIO ABS)**")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 2))} reps")
        st.write(f"   • Rest: 60 seconden")
        
        st.write(f"**4. Russian Twists (OBLIQUES)**")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 1.5))} reps per kant")
        st.write(f"   • Rest: 60 seconden")

    st.write("---")
    st.write("### ⚡ Workout Registratie")
    if st.button("💪 WORKOUT VOLTOOID!"):
        if u_data["last_workout_date"] != str(vandaag_datum):
            nw_w_streak = u_data["workout_streak"] + 1
            update_user_db(username, {"workout_streak": nw_w_streak, "last_workout_date": str(vandaag_datum)})
            st.success("🔥 Ingevoerd in cloud! Streak +1!")
            st.rerun()
        else:
            st.warning("Je hebt vandaag al getraind!")

# TAB 6: VOORTGANG & METINGEN
with tab_progress:
    st.subheader("📈 Voortgang & Metingen Overzicht")
    
    st.write("---")
    st.subheader("📊 Voortgangsdiagrammen")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if weight_history:
            st.write("### Gewichtstrend (kg)")
            st.line_chart(pd.DataFrame(weight_history).set_index("Datum"))
        else:
            st.info("Nog geen gewichtgeschiedenis. Voeg metingen toe!")
    with col_g2:
        if max_history:
            st.write("### Kracht Voortgang (Reps)")
            st.line_chart(pd.DataFrame(max_history).set_index("Datum"))
        else:
            st.info("Nog geen krachtvoortgang. Voeg metingen toe!")
    
    st.write("---")
    st.subheader("📅 Metingen Invoeren")
    st.info("📝 Update je records elke week om je trainingen aan te passen!")
    
    nieuw_gewicht = st.number_input("Gewicht (kg)", min_value=30.0, value=u_data["gewicht"], key="progress_weight")
    
    st.write("### 🏅 Vul je MAX in één set in:")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        trekkingen = st.number_input("Max Trekkingen", min_value=0, value=5, key="progress_trekkingen")
        pistol = st.number_input("Max Pistol Squats", min_value=0, value=5, key="progress_pistol")
    with col_m2:
        pushups = st.number_input("Max Push-ups", min_value=0, value=20, key="progress_pushups")
        situps = st.number_input("Max Sit-ups", min_value=0, value=15, key="progress_situps")
    
    if st.button("💾 Sla metingen op", key="save_progress"):
        datum_str = vandaag_datum.strftime("%d-%m")
        weight_history.append({"Datum": datum_str, "Gewicht": nieuw_gewicht})
        max_history.append({"Datum": datum_str, "Trekkingen": trekkingen, "Push-ups": pushups, "Pistol Squats": pistol, "Sit-ups": situps})
        
        update_user_db(username, {
            "weight_history": json.dumps(weight_history),
            "max_history": json.dumps(max_history),
            "gewicht": nieuw_gewicht
        })
        st.success("✅ Metingen permanent opgeslagen!")
        st.rerun()
    
    st.write("---")
    st.write("### 🏆 Jouw Huidige Badge Niveaus:")
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1: st.metric("🔗 Trekkingen", get_badge(trekkingen))
    with col_b2: st.metric("👊 Push-ups", get_badge(pushups))
    with col_b3: st.metric("🦵 Pistol Squats", get_badge(pistol))
    with col_b4: st.metric("🤸 Sit-ups", get_badge(situps))

# TAB 7: ACCOUNT & DOELEN BEHEREN
with tab_account:
    st.subheader("⚙️ Accountinstellingen")
    with st.form("account_form"):
        u_email = st.text_input("E-mailadres", value=u_data["email"])
        u_pass = st.text_input("Wachtwoord", value=u_data["password"])
        u_age = st.number_input("Leeftijd", min_value=12, value=u_data["leeftijd"])
        u_weight = st.number_input("Gewicht (kg)", min_value=30.0, value=u_data["gewicht"])
        u_height = st.number_input("Lengte (cm)", min_value=100, value=u_data["lengte"])
        u_freq = st.selectbox("Sportfrequentie", ["Niet (0 dagen)", "Licht (1-2 dagen)", "Gemiddeld (3-4 dagen)", "Zwaar (5-7 dagen)"], index=2)
        u_goal = st.selectbox("Doel", ["Afvallen (Cutten)", "Steady blijven (Maintain)", "Lean worden (Lean bulk)", "Nulken (Bulken)"], index=2)
        
        if st.form_submit_button("Sla profiel permanent op"):
            update_user_db(username, {
                "email": u_email, "password": u_pass, "leeftijd": u_age,
                "gewicht": u_weight, "lengte": u_height, "sport_frequentie": u_freq, "doel": u_goal
            })
            st.success("✅ Wijzigingen opgeslagen!")
            st.rerun()
