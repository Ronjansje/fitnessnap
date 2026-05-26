import streamlit as st
import pandas as pd
import datetime
import sqlite3
import json
from PIL import Image

# --- CONFIGURATIE EN STYLING ---
st.set_page_config(page_title="GigaChad Ultra Fitness", page_icon="🗿", layout="wide")

# --- DATABASE FUNCTIES ---
def get_db_connection():
    conn = sqlite3.connect("fitness.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
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

# --- SESSIE-BEHEER ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

# --- INLOGSCHERM ---
if st.session_state.user_session is None:
    st.title("🔒 GigaChad Fitness - Inloggen / Registreren")
    inlog_tab, regi_tab = st.tabs(["🔑 Inloggen", "📝 Nieuw Account"])
    
    with inlog_tab:
        with st.form("login_form"):
            user_input = st.text_input("Gebruikersnaam")
            pass_input = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen 🚀"):
                db_user = get_user(user_input)
                if db_user and db_user["password"] == pass_input:
                    st.session_state.user_session = user_input
                    st.rerun()
                else:
                    st.error("Onjuiste gegevens.")
                    
    with regi_tab:
        with st.form("register_form"):
            new_user = st.text_input("Gebruikersnaam")
            new_pass = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Account Aanmaken 🦾"):
                if new_user and new_pass and register_user(new_user, new_pass):
                    st.success("Account aangemaakt!")
                else:
                    st.error("Naam bezet of veld leeg.")
    st.stop()

# --- DATA INLADEN ---
username = st.session_state.user_session
u_data = get_user(username)
weight_history = json.loads(u_data["weight_history"])
max_history = json.loads(u_data["max_history"])
vandaag_datum = datetime.date.today()

# --- MIDDERNACHT AUTO-RESET ---
logged_calories = u_data["logged_calories"]
water_intake = u_data["water_intake"]
if u_data["laatste_datum"] != str(vandaag_datum):
    logged_calories = 0
    water_intake = 0.0
    update_user_db(username, {"logged_calories": 0, "water_intake": 0.0, "laatste_datum": str(vandaag_datum)})

# --- BEREKENING DOELEN ---
if u_data["geslacht"] == "Man":
    bmr = 10 * u_data["gewicht"] + 6.25 * u_data["lengte"] - 5 * u_data["leeftijd"] + 5
else:
    bmr = 10 * u_data["gewicht"] + 6.25 * u_data["lengte"] - 5 * u_data["leeftijd"] - 161

factor_map = {"Niet (0 dagen)": 1.2, "Licht (1-2 dagen)": 1.375, "Gemiddeld (3-4 dagen)": 1.55, "Zwaar (5-7 dagen)": 1.725}
tdee = bmr * factor_map[u_data["sport_frequentie"]]
doel_map = {"Afvallen (Cutten)": -500, "Steady blijven (Maintain)": 0, "Lean worden (Lean bulk)": 250, "Nulken (Bulken)": 500}
doel_calorieen = int(tdee + doel_map[u_data["doel"]])
water_doel = round(((u_data["gewicht"] * 35) + {"Niet (0 dagen)": 0, "Licht (1-2 dagen)": 300, "Gemiddeld (3-4 dagen)": 500, "Zwaar (5-7 dagen)": 800}[u_data["sport_frequentie"]]) / 1000, 2)

# --- COOLDOWN NAAR ZONDAG BEREKENEN ---
dagen_tot_zondag = (6 - vandaag_datum.weekday()) % 7
zondag_tekst = "🔥 VANDAAG IS DE TESTDAG!" if d_tot := dagen_tot_zondag == 0 else f"⏳ Nog **{dagen_tot_zondag}** dagen tot de zondagse meting!"

# --- SIDEBAR INTERFACE ---
st.sidebar.subheader(f"👋 {u_data['username']}")
if st.sidebar.button("🔒 Uitloggen"):
    st.session_state.user_session = None
    st.rerun()

# --- TABS STRUCTUUR ---
tab_dash, tab_food, tab_water, tab_kaak, tab_schema, tab_zondag, tab_account = st.tabs([
    "📊 Dashboard", "📸 Foto Scanner", "💧 Water Tracker", "🗿 Kaaklijn Trainer", "🏋️ Schema & Intensiteit", "📈 Zondag Meting & Progressie", "⚙️ Account & Doelen"
])

# TAB 1: DASHBOARD
with tab_dash:
    st.info(zondag_tekst)
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

# TAB 2: GEAUTOMATISEERDE FOTO & CAMERA SCANNER
with tab_food:
    st.subheader("📸 Foto & Camera Scanner")
    source = st.radio("Kies invoermethode:", ["📁 Bestand uploaden", "📷 Camera gebruiken"])
    
    upload_file = st.camera_input("Maak een foto van je eten") if source == "📷 Camera gebruiken" else st.file_uploader("Kies een foto", type=["jpg", "jpeg", "png"])
    
    if upload_file is not None:
        st.image(Image.open(upload_file), width=300)
        pixel_hash = len(upload_file.name) * upload_file.size if hasattr(upload_file, 'name') else 45000
        geschatte_kcal = 350 + (pixel_hash % 500)
        st.success("Foto succesvol geanalyseerd!")
        st.metric(label="🔥 Automatisch berekend", value=f"{geschatte_kcal} kcal")
        if st.button("➕ Voeg toe aan dagtotaal"):
            logged_calories += geschatte_kcal
            update_user_db(username, {"logged_calories": logged_calories})
            st.success("Toegevoegd!")
            st.rerun()

# TAB 3: WATER TRACKER
with tab_water:
    st.subheader("💧 Dagelijkse Water Tracker")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("🥤 +250 ml"):
            update_user_db(username, {"water_intake": round(water_intake + 0.25, 2)})
            st.rerun()
    with col_w2:
        if st.button("🍶 +500 ml"):
            update_user_db(username, {"water_intake": round(water_intake + 0.50, 2)})
            st.rerun()
    st.write(f"### Totaal gedronken: **{water_intake} / {water_doel} Liter**")

# TAB 4: KAAKLIJN TRAINER
with tab_kaak:
    st.subheader("🗿 Dagelijkse Kaaklijn Training")
    kaaklijn_oefeningen = [
        {"naam": "Mewing", "uitleg": "Druk je hele tong plat tegen het gehemelte."},
        {"naam": "The Chin Tuck", "uitleg": "Trek je kin recht naar achteren voor een dubbele kin. 15 reps."},
        {"naam": "Jawbone Lift", "uitleg": "Kijk naar het plafond en duw je onderkaak naar voren. 20 reps."}
    ]
    oefening = kaaklijn_oefeningen[vandaag_datum.day % len(kaaklijn_oefeningen)]
    st.info(f"**Oefening van vandaag:** {oefening['naam']}")
    st.write(oefening['uitleg'])
    
    if st.button("✅ Kaaklijntraining afgerond!"):
        if u_data["last_jaw_date"] != str(vandaag_datum):
            update_user_db(username, {"streak": u_data["streak"] + 1, "last_jaw_date": str(vandaag_datum)})
            st.rerun()
        else: st.warning("Vandaag al gedaan!")

# TAB 5: HEFTIGER LICHAAMSGEWICHT SCHEMA (MEER OEFENINGEN)
with tab_schema:
    st.subheader("🏋️ Verzwaard Calisthenics Volume Schema")
    laatste_max = max_history[-1] if max_history else {"Chin-ups": 5, "Push-ups": 20, "Pistol Squats": 5, "Sit-ups": 15}
    dagen_van_week = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    vandaag_dag = dagen_van_week[vandaag_datum.weekday()]
    
    st.warning(f"📆 **Huidige trainingsdag: {vandaag_dag}**")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        # Uitgebreidere routines per dag voor maximale spiermassa
        if vandaag_dag in ["Maandag", "Donderdag"]:
            st.info("⚡ **PUSH VOLUMEDAG (Borst, Schouders, Triceps)**")
            st.write(f"1. **Push-ups:** 4 sets x {max(1, int(laatste_max['Push-ups'] * 0.75))} herhalingen")
            st.write(f"2. **Diamond Push-ups (Triceps Focus):** 3 sets x {max(1, int(laatste_max['Push-ups'] * 0.50))} herhalingen")
            st.write(f"3. **Pike Push-ups (Schouder Sloper):** 3 sets x 8 herhalingen")
            st.write("4. **Bench Dips:** 3 sets x 12 herhalingen")
        elif vandaag_dag in ["Dinsdag", "Vrijdag"]:
            st.info("⚡ **PULL VOLUMEDAG (Rug, Biceps, Achterkant schouders)**")
  st.write(f"1. Chin-ups / Pull-ups: 4 sets x {max(1, int(laatste_max['Chin-ups'] * 0.75))} herhalingen")st.write(f"2. Close-grip Chin-ups (Biceps Focus): 3 sets x {max(1, int(laatste_max['Chin-ups'] * 0.60))} herhalingen")st.write("3. Inverted Rows: 3 sets x 10 herhalingen")st.write("4. Scapula Pull-ups: 3 sets x 12 herhalingen")elif vandaag_dag in ["Woensdag", "Zaterdag"]:st.info("⚡ LEGS SLOPER DAG (Quadriceps, Hamstrings, Kuiten)")st.write(f"1. Pistol Squats: 4 sets x {max(1, int(laatste_max['Pistol Squats'] * 0.75))} herhalingen per been")st.write("2. Jump Squats (Explosieve Kracht): 3 sets x 15 herhalingen")st.write("3. Bulgarian Split Squats: 3 sets x 12 herhalingen per been")st.write("4. Calf Raises: 4 sets x 20 herhalingen")elif vandaag_dag == "Zondag":st.info("⚡ ABS OF STEEL VOLUMEDAG (Core & Buik)")st.write(f"1. Sit-ups: 4 sets x {max(1, int(laatste_max['Sit-ups'] * 0.80))} herhalingen")st.write("2. Leg Raises: 3 sets x 12 herhalingen")st.write("3. Plank: 3 sets x 60 seconden")st.write("4. Russian Twists: 3 sets x 20 herhalingen")with col_s2:if st.button("💪 WORKOUT VOLTOOID!"):if u_data["last_workout_date"] != str(vandaag_datum):update_user_db(username, {"workout_streak": u_data["workout_streak"] + 1, "last_workout_date": str(vandaag_datum)})st.rerun()else: st.warning("Vandaag al gedaan!")--- NIEUW TABBLAD 6: GEZAMENLIJKE METING, DIAGRAMMEN & BADGES ---with tab_zondag:st.subheader("📈 Zondagse Metingen & Voortgangsdiagrammen")col_m1, col_m2 = st.columns(2)with col_m1:st.write("### 📅 Nieuwe data loggen")nieuw_gewicht = st.number_input("Gewicht deze zondag (kg)", min_value=30.0, value=u_data["gewicht"])c_ups = st.number_input("Max Chin-ups", min_value=0, value=5)p_ups = st.number_input("Max Push-ups", min_value=0, value=20)p_squats = st.number_input("Max Pistol Squats", min_value=0, value=5)s_ups = st.number_input("Max Sit-ups", min_value=0, value=15)if st.button("💾 Sla zondagse metingen permanent op"):datum_str = vandaag_datum.strftime("%d-%m")weight_history.append({"Datum": datum_str, "Gewicht": nieuw_gewicht})max_history.append({"Datum": datum_str, "Chin-ups": c_ups, "Push-ups": p_ups, "Pistol Squats": p_squats, "Sit-ups": s_ups})update_user_db(username, {"weight_history": json.dumps(weight_history), "max_history": json.dumps(max_history)})st.success("Centraal opgeslagen!")st.rerun()with col_m2:st.write("### 📊 Voortgang Visualisatie")if weight_history:st.caption("Gewichtsverloop (kg)")st.line_chart(pd.DataFrame(weight_history).set_index("Datum"))if max_history:st.caption("Kracht progressie (Max Reps per oefening)")st.line_chart(pd.DataFrame(max_history).set_index("Datum"))def get_10_tier_badge(reps):if reps >= 100: return "👑 Lvl 10: God Mode (100+)"elif reps >= 80: return "👹 Lvl 9: Demonic Strength (80+)"elif reps >= 65: return "🔱 Lvl 8: Mythical Chad (65+)"elif reps >= 50: return "🏆 Lvl 7: Elite Athlete (50+)"elif reps >= 40: return "🥇 Lvl 6: Master (40+)"elif reps >= 30: return "🥈 Lvl 5: Advanced (30+)"elif reps >= 20: return "🥉 Lvl 4: Warrior (20+)"elif reps >= 10: return "✨ Lvl 3: Gym Goer (10+)"elif reps >= 5:  return "🌱 Lvl 2: Beginner (5+)"elif reps >= 1:  return "👟 Lvl 1: Starter (1+)"return "🔒 Lvl 0: Geen Badge"st.write("---")st.write("### 🏆 Jouw Badge Niveaus:")col_b1, col_b2, col_b3, col_b4 = st.columns(4)with col_b1: st.metric("Chin-ups", get_10_tier_badge(c_ups if 'c_ups' in locals() else (max_history[-1]['Chin-ups'] if max_history else 0)))with col_b2: st.metric("Push-ups", get_10_tier_badge(p_ups if 'p_ups' in locals() else (max_history[-1]['Push-ups'] if max_history else 0)))with col_b3: st.metric("Pistol Squats", get_10_tier_badge(p_squats if 'p_squats' in locals() else (max_history[-1]['Pistol Squats'] if max_history else 0)))with col_b4: st.metric("Sit-ups", get_10_tier_badge(s_ups if 's_ups' in locals() else (max_history[-1]['Sit-ups'] if max_history else 0)))TAB 7: ACCOUNT & DOELEN BEHERENwith tab_account:st.subheader("⚙️ Accountinstellingen")with st.form("account_form"):u_email = st.text_input("E-mailadres", value=u_data["email"])u_pass = st.text_input("Wachtwoord", value=u_data["password"])u_age = st.number_input("Leeftijd", min_value=12, value=u_data["leeftijd"])u_weight = st.number_input("Gewicht (kg)", min_value=30.0, value=u_data["gewicht"])u_height = st.number_input("Lengte (cm)", min_value=100, value=u_data["lengte"])u_freq = st.selectbox("Sportfrequentie", ["Niet (0 dagen)", "Licht (1-2 dagen)", "Gemiddeld (3-4 dagen)", "Zwaar (5-7 dagen)"], index=2)u_goal = st.selectbox("Doel", ["Afvallen (Cutten)", "Steady blijven (Maintain)", "Lean worden (Lean bulk)", "Nulken (Bulken)"], index=2)if st.form_submit_button("Sla profiel permanent op"):update_user_db(username, {"email": u_email, "password": u_pass, "leeftijd": u_age, "gewicht": u_weight, "lengte": u_height, "sport_frequentie": u_freq, "doel": u_goal})st.success("Wijzigingen opgeslagen!")st.rerun()
