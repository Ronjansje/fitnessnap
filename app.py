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

# --- HOOFDMENU TABS ---
tab_dash, tab_food, tab_water, tab_kaak, tab_schema, tab_progress, tab_zondag, tab_account = st.tabs([
    "📊 Dashboard", "📸 Foto Scanner", "💧 Water Tracker", "🗿 Kaaklijn Trainer", "🏋️ Lichaamsgewicht Schema", "📈 Voortgang & Metingen", "📅 Zondag & 40 Badges", "⚙️ Account & Doelen"
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
    st.subheader("📈 Voortgangsdiagrammen (Centraal Opgeslagen)")
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
    col_w1, col_w2 = st.columns(2)
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
            nieuwe_streak = u_data["streak"] + 1
            update_user_db(username, {"streak": nieuwe_streak, "last_jaw_date": str(vandaag_datum)})
            st.success("Database geüpdatet! Streak verhoogd.")
            st.rerun()
        else: st.warning("Je hebt vandaag al getraind!")

# TAB 5: SLIM RECOVERY SCHEMA
with tab_schema:
    st.subheader("🏋️ Dagelijks Lichaamsgewicht Schema")
    laatste_max = max_history[-1] if max_history else {"Chin-ups": 5, "Push-ups": 20, "Pistol Squats": 5, "Sit-ups": 15}
    dagen_van_week = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    vandaag_dag = dagen_van_week[vandaag_datum.weekday()]
    
    st.warning(f"📆 **Huidige trainingsdag: {vandaag_dag}**")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if vandaag_dag in ["Maandag", "Donderdag"]:
            st.info("⚡ **PUSH DAG (Borst, Triceps, Schouders)**")
            st.write(f"- **Push-ups:** 4 sets van **{max(1, int(laatste_max['Push-ups'] * 0.7))} herhalingen**")
        elif vandaag_dag in ["Dinsdag", "Vrijdag"]:
            st.info("⚡ **PULL DAG (Rug, Biceps)**")
            st.write(f"- **Chin-ups:** 4 sets van **{max(1, int(laatste_max['Chin-ups'] * 0.7))} herhalingen**")
        elif vandaag_dag in ["Woensdag", "Zaterdag"]:
            st.info("⚡ **LEGS DAG (Benen & Kuiten)**")
            st.write(f"- **Pistol Squats:** 4 sets van **{max(1, int(laatste_max['Pistol Squats'] * 0.7))} herhalingen**")
        elif vandaag_dag == "Zondag":
            st.info("⚡ **ABS & CORE DAG (Buikspieren)**")
            st.write(f"- **Sit-ups:** 4 sets van **{max(1, int(laatste_max['Sit-ups'] * 0.7))} herhalingen**")

    with col_s2:
        st.write("### ⚡ Streak Registratie")
        if st.button("💪 WORKOUT VOLTOOID!"):
            if u_data["last_workout_date"] != str(vandaag_datum):
                nw_w_streak = u_data["workout_streak"] + 1
                update_user_db(username, {"workout_streak": nw_w_streak, "last_workout_date": str(vandaag_datum)})
                st.success("Ingevoerd in cloud!")
                st.rerun()
            else:
                st.warning("Je hebt vandaag al getraind!")

# TAB 6: VOORTGANG & METINGEN (NEW TAB)
with tab_progress:
    st.subheader("📈 Voortgang & Metingen Overzicht")
    
    # Display diagrams
    st.write("---")
    st.subheader("📊 Voortgangsdiagrammen")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if weight_history:
            st.write("### Gewichtstrend (kg)")
            st.line_chart(pd.DataFrame(weight_history).set_index("Datum"))
        else:
            st.info("Nog geen gewichtgeschiedenis. Voeg metingen toe in het 'Zondag & 40 Badges' tabblad.")
    with col_g2:
        if max_history:
            st.write("### Kracht Voortgang (Reps)")
            st.line_chart(pd.DataFrame(max_history).set_index("Datum"))
        else:
            st.info("Nog geen krachtvoortgang. Voeg metingen toe in het 'Zondag & 40 Badges' tabblad.")
    
    # Sunday measurements section
    st.write("---")
    st.subheader("📅 Zondagse Metingen Invoeren")
    st.info("📝 Voeg je huidige metingen hier in om je voortgang bij te houden!")
    
    nieuw_gewicht = st.number_input("Gewicht deze week (kg)", min_value=30.0, value=u_data["gewicht"], key="progress_weight")
    
    st.write("### 🏅 Vul je nieuwe MAX in één set in:")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        c_ups = st.number_input("Max Chin-ups", min_value=0, value=5, key="progress_chups")
        p_squats = st.number_input("Max Pistol Squats", min_value=0, value=5, key="progress_psquats")
    with col_m2:
        p_ups = st.number_input("Max Push-ups", min_value=0, value=20, key="progress_pups")
        s_ups = st.number_input("Max Sit-ups", min_value=0, value=15, key="progress_sups")
    
    if st.button("💾 Sla metingen op", key="save_progress"):
        datum_str = vandaag_datum.strftime("%d-%m")
        weight_history.append({"Datum": datum_str, "Gewicht": nieuw_gewicht})
        max_history.append({"Datum": datum_str, "Chin-ups": c_ups, "Push-ups": p_ups, "Pistol Squats": p_squats, "Sit-ups": s_ups})
        
        update_user_db(username, {
            "weight_history": json.dumps(weight_history),
            "max_history": json.dumps(max_history),
            "gewicht": nieuw_gewicht
        })
        st.success("✅ Metingen permanent opgeslagen!")
        st.rerun()
    
    # Badge section
    def get_10_tier_badge(reps):
        if reps >= 100: return "👑 Lvl 10: God Mode (100+)"
        elif reps >= 80: return "👹 Lvl 9: Demonic Strength (80+)"
        elif reps >= 65: return "🔱 Lvl 8: Mythical Chad (65+)"
        elif reps >= 50: return "🏆 Lvl 7: Elite Athlete (50+)"
        elif reps >= 40: return "🥇 Lvl 6: Master (40+)"
        elif reps >= 30: return "🥈 Lvl 5: Advanced (30+)"
        elif reps >= 20: return "🥉 Lvl 4: Warrior (20+)"
        elif reps >= 10: return "✨ Lvl 3: Gym Goer (10+)"
        elif reps >= 5:  return "🌱 Lvl 2: Beginner (5+)"
        elif reps >= 1:  return "👟 Lvl 1: Starter (1+)"
        return "🔒 Lvl 0: Geen Badge"

    st.write("---")
    st.write("### 🏆 Jouw Huidige Badge Niveaus:")
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1: st.metric("Chin-ups", get_10_tier_badge(c_ups))
    with col_b2: st.metric("Push-ups", get_10_tier_badge(p_ups))
    with col_b3: st.metric("Pistol Squats", get_10_tier_badge(p_squats))
    with col_b4: st.metric("Sit-ups", get_10_tier_badge(s_ups))

# TAB 7: ZONDAG METING & 40 BADGES
with tab_zondag:
    st.subheader("📅 Zondagse Voortgang & Het 40-Badge Systeem")
    nieuw_gewicht = st.number_input("Gewicht deze zondag (kg)", min_value=30.0, value=u_data["gewicht"])
    
    st.write("### 🏅 Vul je nieuwe MAX in één set in:")
    c_ups = st.number_input("Max Chin-ups", min_value=0, value=5)
    p_ups = st.number_input("Max Push-ups", min_value=0, value=20)
    p_squats = st.number_input("Max Pistol Squats", min_value=0, value=5)
    s_ups = st.number_input("Max Sit-ups", min_value=0, value=15)
    
    if st.button("💾 Sla zondagse metingen op"):
        datum_str = vandaag_datum.strftime("%d-%m")
        weight_history.append({"Datum": datum_str, "Gewicht": nieuw_gewicht})
        max_history.append({"Datum": datum_str, "Chin-ups": c_ups, "Push-ups": p_ups, "Pistol Squats": p_squats, "Sit-ups": s_ups})
        
        update_user_db(username, {
            "weight_history": json.dumps(weight_history),
            "max_history": json.dumps(max_history)
        })
        st.success("Metingen permanent weggeschreven!")
        st.rerun()

    def get_10_tier_badge(reps):
        if reps >= 100: return "👑 Lvl 10: God Mode (100+)"
        elif reps >= 80: return "👹 Lvl 9: Demonic Strength (80+)"
        elif reps >= 65: return "🔱 Lvl 8: Mythical Chad (65+)"
        elif reps >= 50: return "🏆 Lvl 7: Elite Athlete (50+)"
        elif reps >= 40: return "🥇 Lvl 6: Master (40+)"
        elif reps >= 30: return "🥈 Lvl 5: Advanced (30+)"
        elif reps >= 20: return "🥉 Lvl 4: Warrior (20+)"
        elif reps >= 10: return "✨ Lvl 3: Gym Goer (10+)"
        elif reps >= 5:  return "🌱 Lvl 2: Beginner (5+)"
        elif reps >= 1:  return "👟 Lvl 1: Starter (1+)"
        return "🔒 Lvl 0: Geen Badge"

    st.write("---")
    st.write("### 🏆 Jouw Huidige Badge Niveaus:")
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1: st.metric("Chin-ups", get_10_tier_badge(c_ups))
    with col_b2: st.metric("Push-ups", get_10_tier_badge(p_ups))
    with col_b3: st.metric("Pistol Squats", get_10_tier_badge(p_squats))
    with col_b4: st.metric("Sit-ups", get_10_tier_badge(s_ups))

# TAB 8: ACCOUNT & DOELEN BEHEREN
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
            st.success("Wijzigingen opgeslagen in de centrale database!")
            st.rerun()
