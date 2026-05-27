import streamlit as st
import pandas as pd
import datetime
import sqlite3
import json
import time
from PIL import Image
import base64
import io

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
            max_history TEXT DEFAULT '[]',
            calorie_history TEXT DEFAULT '[]'
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

def get_all_users():
    conn = get_db_connection()
    users = conn.execute("SELECT username, streak, workout_streak FROM users ORDER BY streak DESC").fetchall()
    conn.close()
    return users

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

def reset_account(username):
    conn = get_db_connection()
    conn.execute("""
        UPDATE users SET 
        streak = 0,
        workout_streak = 0,
        last_jaw_date = NULL,
        last_workout_date = NULL,
        logged_calories = 0,
        water_intake = 0.0,
        weight_history = '[]',
        max_history = '[]',
        calorie_history = '[]'
        WHERE username = ?
    """, (username,))
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
calorie_history = json.loads(u_data["calorie_history"]) if u_data.get("calorie_history") else []
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

# --- ADVANCED FOOD ANALYZER ---
def analyze_food_image(image):
    """
    Geavanceerde voedselanalyse gebaseerd op afbeelding eigenschappen.
    Dit is een simulatie - in productie zou je een echte AI/API gebruiken.
    """
    img_array = image.convert('RGB')
    pixels = list(img_array.getdata())
    
    avg_r = sum(p[0] for p in pixels) / len(pixels) if pixels else 128
    avg_g = sum(p[1] for p in pixels) / len(pixels) if pixels else 128
    avg_b = sum(p[2] for p in pixels) / len(pixels) if pixels else 128
    
    color_score = (avg_r + avg_g + avg_b) / 3
    pixel_brightness = (avg_r * 0.299 + avg_g * 0.587 + avg_b * 0.114) / 255
    
    # Bepaal voedselcategorie op basis van kleur
    if avg_r > avg_g and avg_r > avg_b:  # Rood/Bruin - vlees/ei
        base_calories = 250
        food_type = "🥩 Vlees/Eiwitrijke maaltijd"
        protein = 35
        carbs = 5
        fat = 12
    elif avg_g > avg_r and avg_g > avg_b:  # Groen - groenten
        base_calories = 150
        food_type = "🥗 Groenten/Salade"
        protein = 8
        carbs = 20
        fat = 2
    elif avg_b > avg_r and avg_b > avg_g:  # Blauw - niet realistisch, fallback
        base_calories = 200
        food_type = "🍱 Gemengde maaltijd"
        protein = 15
        carbs = 30
        fat = 5
    else:  # Geel/Oranje - koolhydraten
        base_calories = 300
        food_type = "🍚 Koolhydraatrijke maaltijd"
        protein = 10
        carbs = 45
        fat = 8
    
    # Aanpassing op basis van helderheid
    brightness_factor = 0.8 + (pixel_brightness * 0.4)
    final_calories = int(base_calories * brightness_factor)
    
    return {
        "calories": final_calories,
        "food_type": food_type,
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
        "confidence": min(95, 60 + int(pixel_brightness * 35))
    }

# --- HOOFDMENU TABS ---
tab_dash, tab_food, tab_water, tab_kaak, tab_schema, tab_progress, tab_account, tab_leaderboard = st.tabs([
    "📊 Dashboard", "📸 Foto Scanner", "💧 Water Tracker", "🗿 Kaaklijn Trainer", "🏋️ Trainingsschema", "📈 Voortgang & Metingen", "⚙️ Account & Doelen", "🏆 Leaderboard"
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
    laatste_max = max_history[-1] if max_history else {"Chin-ups": 5, "Push-ups": 20, "Pistol Squats": 5, "Sit-ups": 15}
    
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        badge_chinups = get_badge(laatste_max.get("Chin-ups", 0))
        st.metric("🔗 Chin-ups", badge_chinups)
        st.caption(badge_chinups)
    with col_b2:
        badge_pushups = get_badge(laatste_max.get("Push-ups", 0))
        st.metric("👊 Push-ups", badge_pushups)
        st.caption(badge_pushups)
    with col_b3:
        badge_pistol = get_badge(laatste_max.get("Pistol Squats", 0))
        st.metric("🦵 Pistol Squats", badge_pistol)
        st.caption(badge_pistol)
    with col_b4:
        badge_situps = get_badge(laatste_max.get("Sit-ups", 0))
        st.metric("🤸 Sit-ups", badge_situps)
        st.caption(badge_situps)

    st.write("---")
    st.subheader("📈 Voortgangsdiagrammen")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if calorie_history:
            df_cal = pd.DataFrame(calorie_history)
            st.write("### Calorieën Voortgang")
            st.line_chart(df_cal.set_index("Datum") if "Datum" in df_cal.columns else df_cal)
        else:
            st.info("Nog geen caloriegeschiedenis. Voeg maaltijden toe!")
    with col_g2:
        if max_history:
            df_max = pd.DataFrame(max_history)
            st.write("### Kracht Voortgang (Reps)")
            st.line_chart(df_max.set_index("Datum") if "Datum" in df_max.columns else df_max)
        else:
            st.info("Nog geen krachtvoortgang. Voeg metingen toe!")

# TAB 2: INSTANT FOTO SCANNER
with tab_food:
    st.subheader("📸 AI Voedsel Foto Scanner")
    
    col_scan1, col_scan2 = st.columns(2)
    
    with col_scan1:
        st.write("### 📤 Upload Foto")
        upload_file = st.file_uploader("Kies een foto van je maaltijd...", type=["jpg", "jpeg", "png"])
        
        if upload_file is not None:
            image = Image.open(upload_file)
            st.image(image, width=300)
            analysis = analyze_food_image(image)
            
            st.success(f"**{analysis['food_type']}** - Betrouwbaarheid: {analysis['confidence']}%")
            st.write(f"**Calorieën:** {analysis['calories']} kcal")
            st.write(f"**Eiwit:** {analysis['protein_g']}g | **Koolhydraten:** {analysis['carbs_g']}g | **Vet:** {analysis['fat_g']}g")
            
            if st.button("➕ Voeg deze maaltijd toe"):
                logged_calories += analysis['calories']
                datum_str = vandaag_datum.strftime("%d-%m")
                
                # Voeg toe aan calorie_history
                calorie_history.append({
                    "Datum": datum_str,
                    "Calorieën": analysis['calories'],
                    "Type": analysis['food_type']
                })
                
                update_user_db(username, {
                    "logged_calories": logged_calories,
                    "calorie_history": json.dumps(calorie_history)
                })
                st.success("✅ Maaltijd opgeslagen in cloud database!")
                st.rerun()
    
    with col_scan2:
        st.write("### 📱 Maak Foto Direct")
        st.info("💡 **Tip:** Zorg dat het voedsel goed zichtbaar is en in goed licht staat voor nauwkeurige analyse!")
        
        # Fallback: Manual input
        st.write("---")
        st.write("### 📝 Handmatig Invoeren")
        manual_calories = st.number_input("Calorieën", min_value=0, value=0)
        manual_type = st.selectbox("Voedseltype", ["🥩 Vlees/Eiwit", "🥗 Groenten", "🍚 Koolhydraten", "🥜 Noten/Olie", "🍕 Snacks", "Overig"])
        
        if st.button("➕ Voeg handmatig voedsel toe"):
            if manual_calories > 0:
                logged_calories += manual_calories
                datum_str = vandaag_datum.strftime("%d-%m")
                calorie_history.append({
                    "Datum": datum_str,
                    "Calorieën": manual_calories,
                    "Type": manual_type
                })
                update_user_db(username, {
                    "logged_calories": logged_calories,
                    "calorie_history": json.dumps(calorie_history)
                })
                st.success(f"✅ {manual_calories} kcal toegevoegd!")
                st.rerun()
            else:
                st.warning("Voer calorieën in!")

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
        {"naam": "Mewing Mastery", "uitleg": "Druk je hele tong plat tegen het gehemelte. Houd 60 seconden vast en focus op je volle gehemelte.", "duration": 60},
        {"naam": "Chin Annihilation", "uitleg": "Trek je kin recht naar achteren alsof je een dubbele kin maakt. 30 reps, EXPLOSIEF!", "duration": 30},
        {"naam": "Jawline Apocalypse", "uitleg": "Kijk naar het plafond en duw je onderkaak naar voren. 50 REPS - NO MERCY!", "duration": 45}
    ]
    oefening = kaaklijn_oefeningen[vandaag_datum.day % len(kaaklijn_oefeningen)]
    st.info(f"**Oefening van vandaag:** {oefening['naam']}")
    st.write(oefening['uitleg'])
    
    st.write("---")
    st.subheader("⏱️ Timer & Uitvoering")
    
    if st.button("▶️ Start Training Timer"):
        st.session_state.timer_active = True
    
    if st.session_state.get("timer_active", False):
        placeholder = st.empty()
        for remaining in range(oefening['duration'], 0, -1):
            with placeholder.container():
                progress_value = 1 - (remaining / oefening['duration'])
                st.progress(progress_value)
                st.metric("⏱️ Tijd Resterend", f"{remaining} seconden")
            time.sleep(1)
        
        with placeholder.container():
            st.progress(1.0)
            st.success("✅ Training voltooid!")
        st.session_state.timer_active = False
    
    st.write("---")
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
    laatste_max = max_history[-1] if max_history else {"Chin-ups": 5, "Push-ups": 20, "Pistol Squats": 5, "Sit-ups": 15}
    dagen_van_week = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    vandaag_dag = dagen_van_week[vandaag_datum.weekday()]
    
    st.warning(f"📆 **Trainingsdag: {vandaag_dag}**")
    st.info("💪 Alle oefeningen LICHAAMSGWICHT - geen equipment nodig!")
    
    if vandaag_dag in ["Maandag", "Donderdag"]:
        st.success("⚡ **PUSH DAY (Borst, Triceps, Schouders)**")
        
        push_record = laatste_max.get("Push-ups", 20)
        set_reps = max(1, int(push_record * 0.6))
        
        st.write(f"**1. Push-ups (EXPLOSIEF)**")
        st.write(f"   📝 **Uitvoering:** Plaats je handen schouderbreedte uit, lichaam recht, zakken tot je borst bijna de grond raakt, daarna explosief omhoog")
        st.write(f"   • 5 sets x {set_reps} reps @ 70% max")
        st.write(f"   • ⏱️ Rest: 90 seconden tussen sets")
        check1 = st.checkbox("✅ Push-ups afgerond", key="check_push")
        
        st.write(f"**2. Handstand Push-ups (EXTREME)**")
        st.write(f"   📝 **Uitvoering:** Omgekeerde positie tegen muur, armen schouderbreedte, buig elbogen en duw jezelf omhoog")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 0.4))} reps")
        st.write(f"   • ⏱️ Rest: 2 minuten tussen sets")
        check2 = st.checkbox("✅ Handstand Push-ups afgerond", key="check_handstand")
        
        st.write(f"**3. Tricep Dips (Lichaamsgwicht)**")
        st.write(f"   📝 **Uitvoering:** Gebruik bank/stoel, handen grepen rand, lichaam omlaag tot elbogen 90°, daarna terug omhoog")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 0.8))} reps")
        st.write(f"   • ⏱️ Rest: 60 seconden")
        check3 = st.checkbox("✅ Tricep Dips afgerond", key="check_dips")
        
        st.write(f"**4. Pike Push-ups (KILLER)**")
        st.write(f"   📝 **Uitvoering:** Push-up positie, bil omhoog (omgekeerde V-vorm), elbogen buigen en hoofd naar grond")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 0.5))} reps")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check4 = st.checkbox("✅ Pike Push-ups afgerond", key="check_pike")
        
        all_checked = check1 and check2 and check3 and check4
        
    elif vandaag_dag in ["Dinsdag", "Vrijdag"]:
        st.success("⚡ **PULL DAY (Rug, Biceps)**")
        
        chinup_record = laatste_max.get("Chin-ups", 5)
        set_reps = max(1, int(chinup_record * 0.6))
        
        st.write(f"**1. Chin-ups (HEAVY)**")
        st.write(f"   📝 **Uitvoering:** Handpalmen naar je toe, grip schouderbreedte of nauwer, trek jezelf omhoog tot je kin boven de bar, controleer omlaag")
        st.write(f"   • 5 sets x {set_reps} reps @ 70% max")
        st.write(f"   • ⏱️ Rest: 2 minuten tussen sets")
        st.write(f"   • (Brug, boom, of pull-up bar)")
        check1 = st.checkbox("✅ Chin-ups afgerond", key="check_chinup")
        
        st.write(f"**2. Hangende Knietillen (ABS BURNER)**")
        st.write(f"   📝 **Uitvoering:** Hang aan pull-up bar, trek kniën omhoog naar borst, controleer omlaag")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 1.5))} reps")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check2 = st.checkbox("✅ Hangende Knietillen afgerond", key="check_knee")
        
        st.write(f"**3. Inverted Rows (Rug Destroyer)**")
        st.write(f"   📝 **Uitvoering:** Lig onder laag object, greep schouderbreedte, trek jezelf omhoog tot borst object raakt")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 1.2))} reps")
        st.write(f"   • (Onder tafel of laag object)")
        st.write(f"   • ⏱️ Rest: 60 seconden")
        check3 = st.checkbox("✅ Inverted Rows afgerond", key="check_inverted")
        
        st.write(f"**4. Brace Hang (Grip Strength)**")
        st.write(f"   📝 **Uitvoering:** Hang aan pull-up bar met gestrekte armen, zo lang mogelijk vasthouden")
        st.write(f"   • 3 sets x 20 seconden hang")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check4 = st.checkbox("✅ Brace Hang afgerond", key="check_brace")
        
        all_checked = check1 and check2 and check3 and check4
        
    elif vandaag_dag in ["Woensdag", "Zaterdag"]:
        st.success("⚡ **LEGS DAY (Benen, Glutes, Calves)**")
        
        squat_record = laatste_max.get("Pistol Squats", 5)
        set_reps = max(1, int(squat_record * 0.6))
        
        st.write(f"**1. Pistol Squats (ELITE)**")
        st.write(f"   📝 **Uitvoering:** Sta op één been, ander been recht vooruit, buig steelbeen tot je bijna grond raakt, terug omhoog (gebruik stoel als backup)")
        st.write(f"   • 4 sets x {set_reps} reps @ 70% max")
        st.write(f"   • ⏱️ Rest: 2 minuten")
        check1 = st.checkbox("✅ Pistol Squats afgerond", key="check_pistol")
        
        st.write(f"**2. Bulgarian Split Squats (VOLUME)**")
        st.write(f"   📝 **Uitvoering:** Ën been verhoogd achter je op bank, buig voorbeen tot 90°, terug omhoog, wissel van been")
        st.write(f"   • 4 sets x {max(1, int(set_reps * 1.5))} reps per been")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check2 = st.checkbox("✅ Bulgarian Split Squats afgerond", key="check_bulgarian")
        
        st.write(f"**3. Jump Squats (EXPLOSIEF)**")
        st.write(f"   📝 **Uitvoering:** Normale squat positie, explosief omhoog springen, land zacht en ga direct omlaag voor volgende rep")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 1.2))} reps")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check3 = st.checkbox("✅ Jump Squats afgerond", key="check_jumpsquats")
        
        st.write(f"**4. Calf Raises (PUMP)**")
        st.write(f"   📝 **Uitvoering:** Sta op beide voeten, til jezelf op je tenen, controleer omlaag")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 3))} reps")
        st.write(f"   • ⏱️ Rest: 60 seconden")
        check4 = st.checkbox("✅ Calf Raises afgerond", key="check_calf")
        
        all_checked = check1 and check2 and check3 and check4
        
    elif vandaag_dag == "Zondag":
        st.success("⚡ **ABS & CORE DAY (Buikspieren, Core Strength)**")
        
        situp_record = laatste_max.get("Sit-ups", 15)
        set_reps = max(1, int(situp_record * 0.6))
        
        st.write(f"**1. Sit-ups (CLASSIC)**")
        st.write(f"   📝 **Uitvoering:** Lig op rug, voeten op grond/hooked, trek jezelf omhoog tot bovenlichaam 45° hoek, controleer omlaag")
        st.write(f"   • 5 sets x {set_reps} reps @ 70% max")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check1 = st.checkbox("✅ Sit-ups afgerond", key="check_situps")
        
        st.write(f"**2. Plank Challenge (CORE DESTROYER)**")
        st.write(f"   📝 **Uitvoering:** Onderarm plank positie, lichaam recht van hoofd tot enkels, span core aan")
        st.write(f"   • 4 sets x 45 seconden hold")
        st.write(f"   • ⏱️ Rest: 90 seconden")
        check2 = st.checkbox("✅ Plank Challenge afgerond", key="check_plank")
        
        st.write(f"**3. Mountain Climbers (CARDIO ABS)**")
        st.write(f"   📝 **Uitvoering:** Push-up positie, trek afwisselend kniën naar borst in snelle beweging")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 2))} reps")
        st.write(f"   • ⏱️ Rest: 60 seconden")
        check3 = st.checkbox("✅ Mountain Climbers afgerond", key="check_mountain")
        
        st.write(f"**4. Russian Twists (OBLIQUES)**")
        st.write(f"   📝 **Uitvoering:** Zit met benen gebogen, draai bovenlichaam links en rechts, raak grond beide kanten")
        st.write(f"   • 3 sets x {max(1, int(set_reps * 1.5))} reps per kant")
        st.write(f"   • ⏱️ Rest: 60 seconden")
        check4 = st.checkbox("✅ Russian Twists afgerond", key="check_twists")
        
        all_checked = check1 and check2 and check3 and check4

    st.write("---")
    st.write("### ⚡ Workout Registratie")
    
    if all_checked:
        if st.button("💪 WORKOUT VOLTOOID!"):
            if u_data["last_workout_date"] != str(vandaag_datum):
                nw_w_streak = u_data["workout_streak"] + 1
                update_user_db(username, {"workout_streak": nw_w_streak, "last_workout_date": str(vandaag_datum)})
                st.success("🔥 Ingevoerd in cloud! Streak +1!")
                st.rerun()
            else:
                st.warning("Je hebt vandaag al getraind!")
    else:
        st.info("✔️ Vink alle 4 oefeningen af om je workout op te slaan!")

# TAB 6: VOORTGANG & METINGEN
with tab_progress:
    st.subheader("📈 Voortgang & Metingen Overzicht")
    
    st.write("---")
    st.subheader("📅 Metingen Invoeren")
    st.info("📝 Update je records elke week om je trainingen aan te passen!")
    
    nieuw_gewicht = st.number_input("Gewicht (kg)", min_value=30.0, value=u_data["gewicht"], key="progress_weight")
    
    st.write("### 🏅 Vul je MAX in één set in:")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        chinups = st.number_input("Max Chin-ups", min_value=0, value=5, key="progress_chinups")
        pistol = st.number_input("Max Pistol Squats", min_value=0, value=5, key="progress_pistol")
    with col_m2:
        pushups = st.number_input("Max Push-ups", min_value=0, value=20, key="progress_pushups")
        situps = st.number_input("Max Sit-ups", min_value=0, value=15, key="progress_situps")
    
    if st.button("💾 Sla metingen op", key="save_progress"):
        datum_str = vandaag_datum.strftime("%d-%m")
        weight_history.append({"Datum": datum_str, "Gewicht": nieuw_gewicht})
        max_history.append({"Datum": datum_str, "Chin-ups": chinups, "Push-ups": pushups, "Pistol Squats": pistol, "Sit-ups": situps})
        
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
    with col_b1: 
        badge_c = get_badge(chinups)
        st.metric("🔗 Chin-ups", badge_c)
        st.caption(badge_c)
    with col_b2: 
        badge_p = get_badge(pushups)
        st.metric("👊 Push-ups", badge_p)
        st.caption(badge_p)
    with col_b3: 
        badge_ps = get_badge(pistol)
        st.metric("🦵 Pistol Squats", badge_ps)
        st.caption(badge_ps)
    with col_b4: 
        badge_s = get_badge(situps)
        st.metric("🤸 Sit-ups", badge_s)
        st.caption(badge_s)

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
    
    st.write("---")
    st.subheader("🚨 Account Reset")
    st.warning("⚠️ **LET OP:** Dit verwijdert ALLE je gegevens (streaks, metingen, calorieën). Dit kan niet ongedaan gemaakt worden!")
    
    if st.button("🔄 Reset Account Volledig", key="reset_account"):
        reset_account(username)
        st.success("✅ Account gereset! Alle gegevens verwijderd.")
        st.balloons()
        st.rerun()

# TAB 8: LEADERBOARD
with tab_leaderboard:
    st.subheader("🏆 GigaChad Fitness Leaderboard")
    st.write("---")
    
    all_users = get_all_users()
    
    if all_users:
        # Jaw Streak Leaderboard
        st.write("### 🗿 Kaaklijn Streak Kampioen")
        jaw_data = sorted(all_users, key=lambda x: x["streak"], reverse=True)
        
        col_rank, col_user, col_days = st.columns([1, 2, 2])
        with col_rank:
            st.write("**Rang**")
        with col_user:
            st.write("**Gebruiker**")
        with col_days:
            st.write("**Streak (Dagen)**")
        
        st.write("---")
        for idx, user in enumerate(jaw_data[:10], 1):
            col_rank, col_user, col_days = st.columns([1, 2, 2])
            with col_rank:
                if idx == 1:
                    st.write(f"🥇 #{idx}")
                elif idx == 2:
                    st.write(f"🥈 #{idx}")
                elif idx == 3:
                    st.write(f"🥉 #{idx}")
                else:
                    st.write(f"#{idx}")
            with col_user:
                st.write(f"**{user['username']}**")
            with col_days:
                st.metric("", f"{user['streak']} 🔥")
        
        st.write("---")
        st.write("### ⚡ Workout Streak Kampioen")
        workout_data = sorted(all_users, key=lambda x: x["workout_streak"], reverse=True)
        
        col_rank, col_user, col_days = st.columns([1, 2, 2])
        with col_rank:
            st.write("**Rang**")
        with col_user:
            st.write("**Gebruiker**")
        with col_days:
            st.write("**Streak (Dagen)**")
        
        st.write("---")
        for idx, user in enumerate(workout_data[:10], 1):
            col_rank, col_user, col_days = st.columns([1, 2, 2])
            with col_rank:
                if idx == 1:
                    st.write(f"🥇 #{idx}")
                elif idx == 2:
                    st.write(f"🥈 #{idx}")
                elif idx == 3:
                    st.write(f"🥉 #{idx}")
                else:
                    st.write(f"#{idx}")
            with col_user:
                st.write(f"**{user['username']}**")
            with col_days:
                st.metric("", f"{user['workout_streak']} ⚡")
    else:
        st.info("📊 Nog geen gebruikers op het leaderboard!")
