import streamlit as st
from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions
import os
import pandas as pd
import httpx

# ── CONFIG ──────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ World Cup 2026 Pool",
    page_icon="🏆",
    layout="wide",
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Use verify=False to bypass corporate proxy SSL interception
_httpx = httpx.Client(verify=False)
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=SyncClientOptions(httpx_client=_httpx),
)

# ── WORLD CUP DATA ─────────────────────────────────────────
GROUPS = {
    "A": ["Mexico", "South Africa", "Korea Republic", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Curaçao", "Côte d'Ivoire", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cabo Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Congo DR", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

ALL_TEAMS = sorted(set(team for teams in GROUPS.values() for team in teams))

GROUP_FLAGS = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "Korea Republic": "🇰🇷", "Czechia": "🇨🇿",
    "Canada": "🇨🇦", "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Switzerland": "🇨🇭",
    "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "USA": "🇺🇸", "Paraguay": "🇵🇾", "Australia": "🇦🇺", "Türkiye": "🇹🇷",
    "Germany": "🇩🇪", "Curaçao": "🇨🇼", "Côte d'Ivoire": "🇨🇮", "Ecuador": "🇪🇨",
    "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Sweden": "🇸🇪", "Tunisia": "🇹🇳",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cabo Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Norway": "🇳🇴",
    "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Jordan": "🇯🇴",
    "Portugal": "🇵🇹", "Congo DR": "🇨🇩", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croatia": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
}

def flag(team: str) -> str:
    return GROUP_FLAGS.get(team, "🏳️")


# ── HELPER FUNCTIONS ────────────────────────────────────────
def get_or_create_user(name: str):
    """Get existing user or create new one."""
    name = name.strip()
    result = supabase.table("users").select("*").eq("name", name).execute()
    if result.data:
        return result.data[0]
    new = supabase.table("users").insert({"name": name}).execute()
    return new.data[0]


def load_user_group_preds(user_id: str) -> dict:
    """Load existing group predictions for a user. Returns {group_name: {first, second}}."""
    result = supabase.table("group_predictions").select("*").eq("user_id", user_id).execute()
    return {r["group_name"]: r for r in result.data}


def load_user_final_preds(user_id: str):
    result = supabase.table("final_predictions").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def load_user_special_preds(user_id: str):
    result = supabase.table("special_predictions").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def save_group_prediction(user_id, group_name, first, second):
    supabase.table("group_predictions").upsert({
        "user_id": user_id,
        "group_name": group_name,
        "first_place": first,
        "second_place": second,
    }, on_conflict="user_id,group_name").execute()


def save_final_prediction(user_id, winner, second, third, fourth):
    supabase.table("final_predictions").upsert({
        "user_id": user_id,
        "winner": winner,
        "second": second,
        "third": third,
        "fourth": fourth,
    }, on_conflict="user_id").execute()


def save_special_prediction(user_id, top_scorer, red_cards, penalties, revelation):
    supabase.table("special_predictions").upsert({
        "user_id": user_id,
        "top_scorer": top_scorer,
        "most_red_cards_team": red_cards,
        "most_penalties_team": penalties,
        "revelation_team": revelation,
    }, on_conflict="user_id").execute()


# ── SCORING ENGINE ──────────────────────────────────────────
def calculate_scores() -> pd.DataFrame:
    """Calculate scores for all users based on actual results."""
    users = supabase.table("users").select("*").execute().data
    if not users:
        return pd.DataFrame()

    # Load actual results
    actual_groups_raw = supabase.table("actual_results").select("*").execute().data
    actual_groups = {r["group_name"]: r for r in actual_groups_raw}
    actual_finals_raw = supabase.table("actual_finals").select("*").execute().data
    actual_finals = actual_finals_raw[0] if actual_finals_raw else {}
    actual_specials_raw = supabase.table("actual_specials").select("*").execute().data
    actual_specials = actual_specials_raw[0] if actual_specials_raw else {}

    scores = []
    for user in users:
        uid = user["id"]
        name = user["name"]
        s1 = 0  # Section 1 points
        s2 = 0  # Section 2 points
        s3 = 0  # Section 3 points

        # ── Section 1: Group stage ──
        group_preds = load_user_group_preds(uid)
        for gname, actual in actual_groups.items():
            if not actual.get("first_place"):
                continue
            pred = group_preds.get(gname)
            if not pred:
                continue
            first_correct = pred["first_place"] == actual["first_place"]
            second_correct = pred["second_place"] == actual["second_place"]
            if first_correct and second_correct:
                s1 += 3  # Both correct = 3 points
            else:
                if first_correct:
                    s1 += 1
                if second_correct:
                    s1 += 1
                # Also 1 point if predicted team qualifies but in wrong position
                if pred["first_place"] == actual["second_place"]:
                    s1 += 1
                if pred["second_place"] == actual["first_place"]:
                    s1 += 1

        # ── Section 2: Final four ──
        final_pred = load_user_final_preds(uid)
        if final_pred and actual_finals.get("winner"):
            if final_pred["winner"] == actual_finals["winner"]:
                s2 += 10
            if final_pred["second"] == actual_finals["second"]:
                s2 += 7
            if final_pred["third"] == actual_finals["third"]:
                s2 += 5
            if final_pred["fourth"] == actual_finals["fourth"]:
                s2 += 3

        # ── Section 3: Special categories ──
        special_pred = load_user_special_preds(uid)
        if special_pred and actual_specials.get("top_scorer"):
            if special_pred["top_scorer"].strip().lower() == (actual_specials.get("top_scorer") or "").strip().lower():
                s3 += 4
            if special_pred["most_red_cards_team"] == actual_specials.get("most_red_cards_team"):
                s3 += 4
            if special_pred["most_penalties_team"] == actual_specials.get("most_penalties_team"):
                s3 += 4
            if special_pred["revelation_team"] == actual_specials.get("revelation_team"):
                s3 += 4

        scores.append({
            "Player": name,
            "Groups (max 36)": s1,
            "Finals (max 25)": s2,
            "Special (max 16)": s3,
            "TOTAL": s1 + s2 + s3,
        })

    df = pd.DataFrame(scores)
    if not df.empty:
        df = df.sort_values("TOTAL", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        df.index.name = "Rank"
    return df


# ── CUSTOM CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 1rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 1rem;
        border: 2px solid #e94560;
    }
    .main-header h1 { color: #FFD700 !important; font-size: 2rem; margin: 0; }
    .main-header p { color: #e0e0e0; font-size: 1rem; margin: 0.5rem 0 0 0; }
    .section-header {
        background: linear-gradient(90deg, #0f3460, #16213e);
        color: #FFD700;
        padding: 0.8rem 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #e94560;
        margin: 1.5rem 0 1rem 0;
    }
    .points-card {
        background: #16213e;
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 1rem;
        color: #e0e0e0;
        margin-bottom: 1rem;
    }
    .points-card strong { color: #FFD700; }
    .welcome-box {
        background: #16213e;
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 1.2rem;
        color: #e0e0e0;
        line-height: 1.6;
        margin: 1rem 0;
    }
    .welcome-box h3 { color: #FFD700; margin-top: 0; }
    .prize { color: #4CAF50; font-weight: bold; }
    .thank-you {
        text-align: center;
        padding: 3rem 1rem;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 15px;
        border: 2px solid #4CAF50;
        margin: 2rem 0;
    }
    .thank-you h2 { color: #FFD700 !important; }
    .thank-you p { color: #e0e0e0; font-size: 1.1rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 1rem;
    }
    @media (max-width: 768px) {
        .main-header h1 { font-size: 1.5rem; }
        .main-header p { font-size: 0.85rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── STEP NAVIGATION ────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state["step"] = 1

def go_to_step(n):
    st.session_state["step"] = n

current_step = st.session_state["step"]

# ── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/e/e3/2026_FIFA_World_Cup.svg/200px-2026_FIFA_World_Cup.svg.png", width=120)
    st.markdown("### ⚽ Porra Mundial 2026")
    st.markdown("---")

    # Admin panel in sidebar (password protected)
    st.markdown("### 🔧 Panel Admin")
    admin_pass = st.text_input("Contraseña Admin", type="password", key="admin_pw")

    if admin_pass == st.secrets.get("ADMIN_PASSWORD", "worldcup2026"):
        st.success("🔓 Acceso concedido")

        # Show detailed points breakdown
        st.markdown("#### 📊 Desglose de Puntos")
        df_scores = calculate_scores()
        if not df_scores.empty:
            st.dataframe(df_scores, use_container_width=True)
        else:
            st.caption("Sin datos aún.")

        st.markdown("---")
        st.markdown("#### ✏️ Actualizar Resultados Reales")

        admin_section = st.selectbox("Sección", ["Grupos", "Final Four", "Especiales"], key="adm_section")

        if admin_section == "Grupos":
            actual_groups_raw = supabase.table("actual_results").select("*").execute().data
            actual_map = {r["group_name"]: r for r in actual_groups_raw}

            for gname in GROUPS:
                teams = GROUPS[gname]
                existing_actual = actual_map.get(gname, {})
                st.markdown(f"**Grupo {gname}**")
                def_1 = teams.index(existing_actual["first_place"]) if existing_actual.get("first_place") in teams else 0
                a_first = st.selectbox(f"1º", teams, index=def_1, key=f"adm_g{gname}_1", format_func=lambda t: f"{flag(t)} {t}")
                opts = [t for t in teams if t != a_first]
                def_2 = opts.index(existing_actual["second_place"]) if existing_actual.get("second_place") in opts else 0
                a_second = st.selectbox(f"2º", opts, index=def_2, key=f"adm_g{gname}_2", format_func=lambda t: f"{flag(t)} {t}")

                if st.button(f"Guardar Grupo {gname}", key=f"adm_save_{gname}"):
                    supabase.table("actual_results").upsert({
                        "group_name": gname,
                        "first_place": a_first,
                        "second_place": a_second,
                    }, on_conflict="group_name").execute()
                    st.success(f"Grupo {gname} guardado!")

        elif admin_section == "Final Four":
            af = supabase.table("actual_finals").select("*").execute().data
            af = af[0] if af else {}
            aw = st.selectbox("Campeón", ALL_TEAMS, index=ALL_TEAMS.index(af["winner"]) if af.get("winner") in ALL_TEAMS else 0, key="adm_w", format_func=lambda t: f"{flag(t)} {t}")
            a2 = st.selectbox("Segundo", [t for t in ALL_TEAMS if t != aw], key="adm_2", format_func=lambda t: f"{flag(t)} {t}")
            a3 = st.selectbox("Tercero", [t for t in ALL_TEAMS if t not in [aw, a2]], key="adm_3", format_func=lambda t: f"{flag(t)} {t}")
            a4 = st.selectbox("Cuarto", [t for t in ALL_TEAMS if t not in [aw, a2, a3]], key="adm_4", format_func=lambda t: f"{flag(t)} {t}")

            if st.button("Guardar Final Four", key="adm_save_finals"):
                supabase.table("actual_finals").update({
                    "winner": aw, "second": a2, "third": a3, "fourth": a4,
                }).eq("id", af["id"]).execute()
                st.success("Final Four guardado!")

        elif admin_section == "Especiales":
            asp = supabase.table("actual_specials").select("*").execute().data
            asp = asp[0] if asp else {}
            a_scorer = st.text_input("Máximo Goleador", value=asp.get("top_scorer", "") or "", key="adm_scorer")
            a_red = st.selectbox("Más Tarjetas Rojas", ALL_TEAMS, key="adm_red", format_func=lambda t: f"{flag(t)} {t}")
            a_pen = st.selectbox("Más Penaltis", ALL_TEAMS, key="adm_pen", format_func=lambda t: f"{flag(t)} {t}")
            a_rev = st.selectbox("Equipo Revelación", ALL_TEAMS, key="adm_rev", format_func=lambda t: f"{flag(t)} {t}")

            if st.button("Guardar Especiales", key="adm_save_specials"):
                supabase.table("actual_specials").update({
                    "top_scorer": a_scorer,
                    "most_red_cards_team": a_red,
                    "most_penalties_team": a_pen,
                    "revelation_team": a_rev,
                }).eq("id", asp["id"]).execute()
                st.success("Especiales guardado!")

    elif admin_pass:
        st.error("❌ Contraseña incorrecta.")

# ══════════════════════════════════════════════════════════════
# STEP 1: WELCOME PAGE
# ══════════════════════════════════════════════════════════════
if current_step == 1:
    st.markdown("""
<div class="main-header">
    <h1>⚽ Porra Mundial 2026 🏆</h1>
    <p>USA 🇺🇸 • México 🇲🇽 • Canadá 🇨🇦 &nbsp;|&nbsp; 11 junio – 19 julio 2026</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="welcome-box">
    <h3>🎉 ¡Bienvenido a la Porra del Mundial 2026!</h3>
    <p>
        Esto es una <strong>porra</strong> para el Mundial de Fútbol 2026.
        ¡Demuestra cuánto sabes de fútbol y compite contra tus amigos!
    </p>
    <p>
        💰 <strong>Cuota de inscripción:</strong> 5€ por participante
    </p>
    <p>
        🏆 <strong>Reparto de premios</strong> (del bote total acumulado):<br>
        &nbsp;&nbsp;&nbsp;🥇 1º clasificado: <span class="prize">75%</span><br>
        &nbsp;&nbsp;&nbsp;🥈 2º clasificado: <span class="prize">20%</span><br>
        &nbsp;&nbsp;&nbsp;🥉 3º clasificado: <span class="prize">5%</span>
    </p>
    <p>
        📊 Al finalizar el Mundial se publicará la <strong>clasificación final</strong> 
        con la puntuación de cada participante.
    </p>
</div>
""", unsafe_allow_html=True)

    # Name input
    st.markdown("---")
    st.markdown("### 👤 Introduce tu nombre para participar")
    username = st.text_input("Nombre", placeholder="Ej: Carlos", label_visibility="collapsed", key="username_input")

    if st.button("Siguiente ➡️", type="primary", use_container_width=True):
        if username and username.strip():
            user = get_or_create_user(username)
            st.session_state["user"] = user
            st.session_state["step"] = 2
            st.rerun()
        else:
            st.error("⚠️ Por favor, introduce tu nombre para continuar.")

    # Leaderboard
    st.markdown("---")
    st.markdown('<div class="section-header"><h3>🏆 Clasificación Actual</h3></div>', unsafe_allow_html=True)
    all_users = supabase.table("users").select("*").execute().data
    if all_users:
        df = calculate_scores()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Aún no hay participantes. ¡Sé el primero!")

    # Participants list
    if all_users:
        st.markdown("#### 📋 Participantes registrados")
        participant_names = [u['name'] for u in all_users]
        st.write(" • ".join(participant_names))

    st.stop()

# ── Check user is logged in for steps 2-5 ──────────────────
if "user" not in st.session_state:
    st.session_state["step"] = 1
    st.rerun()

user = st.session_state["user"]
user_id = user["id"]

# Load existing predictions
existing_groups = load_user_group_preds(user_id)
existing_finals = load_user_final_preds(user_id)
existing_specials = load_user_special_preds(user_id)

# Header for steps 2-5
st.markdown("""
<div class="main-header">
    <h1>⚽ Porra Mundial 2026 🏆</h1>
    <p>Hola, {name}! &nbsp;|&nbsp; Paso {step} de 4</p>
</div>
""".format(name=user["name"], step=current_step - 1), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 2: GROUP STAGE
# ══════════════════════════════════════════════════════════════
if current_step == 2:
    st.markdown('<div class="section-header"><h3>🏟️ Sección 1: Predice el 1º y 2º de cada grupo</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="points-card">🎯 <strong>1 punto</strong> por equipo en posición correcta · <strong>1 punto</strong> si clasifica pero posición incorrecta · <strong>3 puntos</strong> si 1º y 2º son exactos</div>', unsafe_allow_html=True)

    group_selections = {}
    group_names = list(GROUPS.keys())

    for row in range(4):
        cols = st.columns(3)
        for col_idx in range(3):
            g_idx = row * 3 + col_idx
            if g_idx >= len(group_names):
                break
            gname = group_names[g_idx]
            teams = GROUPS[gname]
            existing = existing_groups.get(gname, {})

            with cols[col_idx]:
                team_labels = [f"{flag(t)} {t}" for t in teams]
                st.markdown(f"**Grupo {gname}**")
                st.caption(" · ".join(team_labels))

                default_1st = teams.index(existing["first_place"]) if existing.get("first_place") in teams else 0
                first = st.selectbox(
                    f"🥇 1º", teams, index=default_1st, key=f"g{gname}_1",
                    format_func=lambda t: f"{flag(t)} {t}",
                )
                second_options = [t for t in teams if t != first]
                default_2nd_filtered = second_options.index(existing["second_place"]) if existing.get("second_place") in second_options else 0
                second = st.selectbox(
                    f"🥈 2º", second_options, index=default_2nd_filtered, key=f"g{gname}_2",
                    format_func=lambda t: f"{flag(t)} {t}",
                )
                group_selections[gname] = (first, second)
                st.markdown("---")

    if st.button("Siguiente ➡️  (guarda automáticamente)", type="primary", use_container_width=True):
        for gname, (first, second) in group_selections.items():
            save_group_prediction(user_id, gname, first, second)
        st.session_state["step"] = 3
        st.rerun()

# ══════════════════════════════════════════════════════════════
# STEP 3: FINAL FOUR
# ══════════════════════════════════════════════════════════════
elif current_step == 3:
    st.markdown('<div class="section-header"><h3>🏆 Sección 2: Predice el Final Four</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="points-card">🥇 Campeón: <strong>10 pts</strong> · 🥈 Segundo: <strong>7 pts</strong> · 🥉 Tercero: <strong>5 pts</strong> · 4º: <strong>3 pts</strong></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        default_w = ALL_TEAMS.index(existing_finals["winner"]) if existing_finals and existing_finals.get("winner") in ALL_TEAMS else 0
        winner = st.selectbox("🥇 Campeón del Mundial", ALL_TEAMS, index=default_w, key="f_winner", format_func=lambda t: f"{flag(t)} {t}")

        remaining_2 = [t for t in ALL_TEAMS if t != winner]
        default_s = remaining_2.index(existing_finals["second"]) if existing_finals and existing_finals.get("second") in remaining_2 else 0
        second = st.selectbox("🥈 Subcampeón", remaining_2, index=default_s, key="f_second", format_func=lambda t: f"{flag(t)} {t}")

    with col2:
        remaining_3 = [t for t in ALL_TEAMS if t not in [winner, second]]
        default_t = remaining_3.index(existing_finals["third"]) if existing_finals and existing_finals.get("third") in remaining_3 else 0
        third = st.selectbox("🥉 Tercer puesto", remaining_3, index=default_t, key="f_third", format_func=lambda t: f"{flag(t)} {t}")

        remaining_4 = [t for t in ALL_TEAMS if t not in [winner, second, third]]
        default_f = remaining_4.index(existing_finals["fourth"]) if existing_finals and existing_finals.get("fourth") in remaining_4 else 0
        fourth = st.selectbox("4️⃣ Cuarto puesto", remaining_4, index=default_f, key="f_fourth", format_func=lambda t: f"{flag(t)} {t}")

    st.markdown(f"""
| Posición | Equipo |
|----------|--------|
| 🥇 Campeón | {flag(winner)} {winner} |
| 🥈 Segundo | {flag(second)} {second} |
| 🥉 Tercero | {flag(third)} {third} |
| 4️⃣ Cuarto | {flag(fourth)} {fourth} |
    """)

    if st.button("Siguiente ➡️  (guarda automáticamente)", type="primary", use_container_width=True):
        save_final_prediction(user_id, winner, second, third, fourth)
        st.session_state["step"] = 4
        st.rerun()

# ══════════════════════════════════════════════════════════════
# STEP 4: SPECIAL CATEGORIES
# ══════════════════════════════════════════════════════════════
elif current_step == 4:
    st.markdown('<div class="section-header"><h3>⭐ Sección 3: Categorías Especiales</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="points-card">🎯 <strong>4 puntos</strong> por cada predicción correcta · Máximo: <strong>16 puntos</strong></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        default_scorer = existing_specials.get("top_scorer", "") if existing_specials else ""
        top_scorer = st.text_input(
            "⚽ Máximo Goleador (Bota de Oro)",
            value=default_scorer,
            placeholder="Ej: Kylian Mbappé",
            help="Nombre del jugador que crees que marcará más goles."
        )

        default_red = ALL_TEAMS.index(existing_specials["most_red_cards_team"]) if existing_specials and existing_specials.get("most_red_cards_team") in ALL_TEAMS else 0
        most_red = st.selectbox(
            "🟥 Más Tarjetas Rojas (Equipo)",
            ALL_TEAMS, index=default_red, key="sp_red",
            format_func=lambda t: f"{flag(t)} {t}",
        )

    with col2:
        default_pen = ALL_TEAMS.index(existing_specials["most_penalties_team"]) if existing_specials and existing_specials.get("most_penalties_team") in ALL_TEAMS else 0
        most_penalties = st.selectbox(
            "🎯 Más Penaltis Marcados (Equipo)",
            ALL_TEAMS, index=default_pen, key="sp_pen",
            format_func=lambda t: f"{flag(t)} {t}",
        )

        default_rev = ALL_TEAMS.index(existing_specials["revelation_team"]) if existing_specials and existing_specials.get("revelation_team") in ALL_TEAMS else 0
        revelation = st.selectbox(
            "🌟 Equipo Revelación",
            ALL_TEAMS, index=default_rev, key="sp_rev",
            format_func=lambda t: f"{flag(t)} {t}",
            help="El equipo sorpresa que supera las expectativas."
        )

    if st.button("✅ Finalizar (guarda automáticamente)", type="primary", use_container_width=True):
        if not top_scorer.strip():
            st.error("⚠️ Introduce el nombre del máximo goleador.")
        else:
            save_special_prediction(user_id, top_scorer, most_red, most_penalties, revelation)
            st.session_state["step"] = 5
            st.rerun()

# ══════════════════════════════════════════════════════════════
# STEP 5: THANK YOU / CONFIRMATION
# ══════════════════════════════════════════════════════════════
elif current_step == 5:
    st.markdown("""
<div class="thank-you">
    <h2>🎉 ¡Gracias por participar!</h2>
    <p>Tus predicciones han sido guardadas correctamente.</p>
    <p>Podrás volver en cualquier momento para ver la clasificación actualizada.</p>
    <p>¡Buena suerte! 🍀⚽</p>
</div>
""", unsafe_allow_html=True)

    st.balloons()

    st.markdown("---")

    # Show leaderboard
    st.markdown('<div class="section-header"><h3>🏆 Clasificación Actual</h3></div>', unsafe_allow_html=True)
    df = calculate_scores()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        if len(df) > 0:
            leader = df.iloc[0]
            st.markdown(f"### 👑 Líder: **{leader['Player']}** con **{leader['TOTAL']}** puntos")

    st.markdown("---")
    if st.button("🔄 Volver al inicio", use_container_width=True):
        st.session_state["step"] = 1
        st.session_state.pop("user", None)
        st.rerun()
    if st.button("✏️ Modificar mis predicciones", use_container_width=True):
        st.session_state["step"] = 2
        st.rerun()
