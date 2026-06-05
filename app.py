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
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 1.5rem;
        border: 2px solid #e94560;
    }
    .main-header h1 {
        color: #FFD700 !important;
        font-size: 2.5rem;
        margin: 0;
    }
    .main-header p {
        color: #e0e0e0;
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
    }
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #0f3460, #16213e);
        color: #FFD700;
        padding: 0.8rem 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #e94560;
        margin: 1.5rem 0 1rem 0;
    }
    /* Info cards */
    .points-card {
        background: #16213e;
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 1rem;
        color: #e0e0e0;
        margin-bottom: 1rem;
    }
    .points-card strong { color: #FFD700; }
    /* Streamlit overrides */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── HEADER ──────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚽ World Cup 2026 Prediction Pool 🏆</h1>
    <p>USA 🇺🇸 • Mexico 🇲🇽 • Canada 🇨🇦 &nbsp;|&nbsp; June 11 – July 19, 2026</p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR: USER LOGIN ────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/e/e3/2026_FIFA_World_Cup.svg/200px-2026_FIFA_World_Cup.svg.png", width=150)
    st.markdown("### 👤 Enter Your Name")
    username = st.text_input("Name", placeholder="e.g. Carlos", label_visibility="collapsed")

    if username:
        user = get_or_create_user(username)
        st.success(f"Welcome, **{user['name']}**!")
        st.session_state["user"] = user
    else:
        st.info("Type your name to start predicting.")
        st.session_state.pop("user", None)

    st.markdown("---")
    st.markdown("### 📊 Scoring System")
    st.markdown("""
**Section 1 – Groups:**
- 1 pt per correct team (right position)
- 1 pt if team qualifies but wrong position
- 3 pts if both 1st & 2nd are exact

**Section 2 – Final Four:**
- 🥇 Winner: 10 pts
- 🥈 Second: 7 pts
- 🥉 Third: 5 pts
- 4th: 3 pts

**Section 3 – Special:**
- 4 pts per correct prediction
    """)

# ── MAIN CONTENT ────────────────────────────────────────────
if "user" not in st.session_state:
    st.markdown("## 👈 Enter your name in the sidebar to begin!")
    st.markdown("---")

    # Still show leaderboard
    st.markdown('<div class="section-header"><h3>🏆 Leaderboard</h3></div>', unsafe_allow_html=True)
    all_users = supabase.table("users").select("*").execute().data
    if all_users:
        df = calculate_scores()
        if not df.empty:
            st.dataframe(df, use_container_width=True)

        st.markdown("#### 📋 Registered Participants")
        for u in all_users:
            st.write(f"• {u['name']}")
    else:
        st.info("No participants yet. Be the first to register!")
    st.stop()

user = st.session_state["user"]
user_id = user["id"]

# Load existing predictions
existing_groups = load_user_group_preds(user_id)
existing_finals = load_user_final_preds(user_id)
existing_specials = load_user_special_preds(user_id)

# ── TABS ────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏟️ Section 1: Group Stage",
    "🏆 Section 2: Final Four",
    "⭐ Section 3: Special Categories",
    "📊 Leaderboard",
    "🔧 Admin Panel",
])

# ── TAB 1: GROUP STAGE ─────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header"><h3>🏟️ Section 1: Predict 1st & 2nd Place for Each Group</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="points-card">🎯 <strong>1 point</strong> per correct team in correct position · <strong>1 point</strong> if team qualifies but in wrong position · <strong>3 points</strong> if both 1st and 2nd are exactly right</div>', unsafe_allow_html=True)

    # Display groups in a grid (3 columns x 4 rows)
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
                st.markdown(f"**Group {gname}**")
                st.caption(" · ".join(team_labels))

                default_1st = teams.index(existing["first_place"]) if existing.get("first_place") in teams else 0
                default_2nd = teams.index(existing["second_place"]) if existing.get("second_place") in teams else 1

                first = st.selectbox(
                    f"🥇 1st Place",
                    teams,
                    index=default_1st,
                    key=f"g{gname}_1",
                    format_func=lambda t: f"{flag(t)} {t}",
                )
                second_options = [t for t in teams if t != first]
                default_2nd_filtered = second_options.index(existing["second_place"]) if existing.get("second_place") in second_options else 0
                second = st.selectbox(
                    f"🥈 2nd Place",
                    second_options,
                    index=default_2nd_filtered,
                    key=f"g{gname}_2",
                    format_func=lambda t: f"{flag(t)} {t}",
                )
                group_selections[gname] = (first, second)
                st.markdown("---")

    if st.button("💾 Save Group Predictions", type="primary", use_container_width=True):
        for gname, (first, second) in group_selections.items():
            save_group_prediction(user_id, gname, first, second)
        st.success("✅ Group predictions saved!")
        st.balloons()

# ── TAB 2: FINAL FOUR ──────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header"><h3>🏆 Section 2: Predict the Final Four</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="points-card">🥇 Winner: <strong>10 pts</strong> · 🥈 Second: <strong>7 pts</strong> · 🥉 Third: <strong>5 pts</strong> · 4th: <strong>3 pts</strong> · Max possible: <strong>25 points</strong></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        default_w = ALL_TEAMS.index(existing_finals["winner"]) if existing_finals and existing_finals.get("winner") in ALL_TEAMS else 0
        winner = st.selectbox("🥇 World Cup Winner", ALL_TEAMS, index=default_w, key="f_winner", format_func=lambda t: f"{flag(t)} {t}")

        remaining_2 = [t for t in ALL_TEAMS if t != winner]
        default_s = remaining_2.index(existing_finals["second"]) if existing_finals and existing_finals.get("second") in remaining_2 else 0
        second = st.selectbox("🥈 Runner-up (2nd)", remaining_2, index=default_s, key="f_second", format_func=lambda t: f"{flag(t)} {t}")

    with col2:
        remaining_3 = [t for t in ALL_TEAMS if t not in [winner, second]]
        default_t = remaining_3.index(existing_finals["third"]) if existing_finals and existing_finals.get("third") in remaining_3 else 0
        third = st.selectbox("🥉 Third Place", remaining_3, index=default_t, key="f_third", format_func=lambda t: f"{flag(t)} {t}")

        remaining_4 = [t for t in ALL_TEAMS if t not in [winner, second, third]]
        default_f = remaining_4.index(existing_finals["fourth"]) if existing_finals and existing_finals.get("fourth") in remaining_4 else 0
        fourth = st.selectbox("4️⃣ Fourth Place", remaining_4, index=default_f, key="f_fourth", format_func=lambda t: f"{flag(t)} {t}")

    st.markdown(f"""
    ### Your Final Four:
    | Position | Team |
    |----------|------|
    | 🥇 Winner | {flag(winner)} {winner} |
    | 🥈 Second | {flag(second)} {second} |
    | 🥉 Third | {flag(third)} {third} |
    | 4️⃣ Fourth | {flag(fourth)} {fourth} |
    """)

    if st.button("💾 Save Final Four Predictions", type="primary", use_container_width=True):
        save_final_prediction(user_id, winner, second, third, fourth)
        st.success("✅ Final four predictions saved!")
        st.balloons()

# ── TAB 3: SPECIAL CATEGORIES ──────────────────────────────
with tab3:
    st.markdown('<div class="section-header"><h3>⭐ Section 3: Special Category Predictions</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="points-card">🎯 <strong>4 points</strong> for each correct prediction · Max possible: <strong>16 points</strong></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        default_scorer = existing_specials.get("top_scorer", "") if existing_specials else ""
        top_scorer = st.text_input(
            "⚽ Top Scorer (Golden Boot)",
            value=default_scorer,
            placeholder="e.g. Kylian Mbappé",
            help="Type the player's name who you think will score the most goals."
        )

        default_red = ALL_TEAMS.index(existing_specials["most_red_cards_team"]) if existing_specials and existing_specials.get("most_red_cards_team") in ALL_TEAMS else 0
        most_red = st.selectbox(
            "🟥 Most Red Cards (Team)",
            ALL_TEAMS,
            index=default_red,
            key="sp_red",
            format_func=lambda t: f"{flag(t)} {t}",
        )

    with col2:
        default_pen = ALL_TEAMS.index(existing_specials["most_penalties_team"]) if existing_specials and existing_specials.get("most_penalties_team") in ALL_TEAMS else 0
        most_penalties = st.selectbox(
            "🎯 Most Penalties Scored (Team)",
            ALL_TEAMS,
            index=default_pen,
            key="sp_pen",
            format_func=lambda t: f"{flag(t)} {t}",
        )

        default_rev = ALL_TEAMS.index(existing_specials["revelation_team"]) if existing_specials and existing_specials.get("revelation_team") in ALL_TEAMS else 0
        revelation = st.selectbox(
            "🌟 Revelation Team of the World Cup",
            ALL_TEAMS,
            index=default_rev,
            key="sp_rev",
            format_func=lambda t: f"{flag(t)} {t}",
            help="The underdog / surprise team that exceeds expectations."
        )

    if st.button("💾 Save Special Predictions", type="primary", use_container_width=True):
        if not top_scorer.strip():
            st.error("Please enter a player name for the Top Scorer.")
        else:
            save_special_prediction(user_id, top_scorer, most_red, most_penalties, revelation)
            st.success("✅ Special category predictions saved!")
            st.balloons()

# ── TAB 4: LEADERBOARD ─────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header"><h3>📊 Leaderboard & All Predictions</h3></div>', unsafe_allow_html=True)

    df = calculate_scores()
    if not df.empty:
        st.dataframe(df, use_container_width=True)

        if len(df) > 0:
            leader = df.iloc[0]
            st.markdown(f"### 👑 Current Leader: **{leader['Player']}** with **{leader['TOTAL']}** points")
    else:
        st.info("No predictions yet.")

    st.markdown("---")
    st.markdown("### 👀 View Everyone's Predictions")

    all_users = supabase.table("users").select("*").execute().data
    if all_users:
        selected_viewer = st.selectbox("Select a participant:", [u["name"] for u in all_users], key="viewer")
        viewed_user = next(u for u in all_users if u["name"] == selected_viewer)
        vid = viewed_user["id"]

        vcol1, vcol2 = st.columns(2)
        with vcol1:
            st.markdown("#### 🏟️ Group Predictions")
            vg = load_user_group_preds(vid)
            if vg:
                for gname in sorted(vg.keys()):
                    p = vg[gname]
                    st.write(f"**Group {gname}:** 🥇 {flag(p['first_place'])} {p['first_place']} · 🥈 {flag(p['second_place'])} {p['second_place']}")
            else:
                st.caption("No group predictions yet.")

        with vcol2:
            st.markdown("#### 🏆 Final Four")
            vf = load_user_final_preds(vid)
            if vf:
                st.write(f"🥇 {flag(vf['winner'])} {vf['winner']}")
                st.write(f"🥈 {flag(vf['second'])} {vf['second']}")
                st.write(f"🥉 {flag(vf['third'])} {vf['third']}")
                st.write(f"4️⃣ {flag(vf['fourth'])} {vf['fourth']}")
            else:
                st.caption("No final predictions yet.")

            st.markdown("#### ⭐ Special Categories")
            vs = load_user_special_preds(vid)
            if vs:
                st.write(f"⚽ Top Scorer: **{vs['top_scorer']}**")
                st.write(f"🟥 Most Red Cards: {flag(vs['most_red_cards_team'])} {vs['most_red_cards_team']}")
                st.write(f"🎯 Most Penalties: {flag(vs['most_penalties_team'])} {vs['most_penalties_team']}")
                st.write(f"🌟 Revelation: {flag(vs['revelation_team'])} {vs['revelation_team']}")
            else:
                st.caption("No special predictions yet.")

# ── TAB 5: ADMIN PANEL ─────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header"><h3>🔧 Admin Panel – Enter Actual Results</h3></div>', unsafe_allow_html=True)
    st.warning("⚠️ Only the pool organizer should use this section. Enter the real results as the tournament progresses to calculate scores.")

    admin_pass = st.text_input("Admin Password", type="password", key="admin_pw")

    if admin_pass == st.secrets.get("ADMIN_PASSWORD", "worldcup2026"):
        st.success("🔓 Admin access granted.")

        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["Groups", "Final Four", "Special"])

        with admin_tab1:
            st.markdown("#### Enter actual group results")
            actual_groups_raw = supabase.table("actual_results").select("*").execute().data
            actual_map = {r["group_name"]: r for r in actual_groups_raw}

            for gname in GROUPS:
                teams = GROUPS[gname]
                existing_actual = actual_map.get(gname, {})
                st.markdown(f"**Group {gname}**")
                ac1, ac2 = st.columns(2)
                with ac1:
                    def_1 = teams.index(existing_actual["first_place"]) if existing_actual.get("first_place") in teams else 0
                    a_first = st.selectbox(f"1st", teams, index=def_1, key=f"adm_g{gname}_1", format_func=lambda t: f"{flag(t)} {t}")
                with ac2:
                    opts = [t for t in teams if t != a_first]
                    def_2 = opts.index(existing_actual["second_place"]) if existing_actual.get("second_place") in opts else 0
                    a_second = st.selectbox(f"2nd", opts, index=def_2, key=f"adm_g{gname}_2", format_func=lambda t: f"{flag(t)} {t}")

                if st.button(f"Save Group {gname}", key=f"adm_save_{gname}"):
                    supabase.table("actual_results").update({
                        "first_place": a_first,
                        "second_place": a_second,
                    }).eq("group_name", gname).execute()
                    st.success(f"Group {gname} results saved!")

        with admin_tab2:
            st.markdown("#### Enter actual final four")
            af = supabase.table("actual_finals").select("*").execute().data
            af = af[0] if af else {}

            aw = st.selectbox("Winner", ALL_TEAMS, index=ALL_TEAMS.index(af["winner"]) if af.get("winner") in ALL_TEAMS else 0, key="adm_w", format_func=lambda t: f"{flag(t)} {t}")
            a2 = st.selectbox("Second", [t for t in ALL_TEAMS if t != aw], key="adm_2", format_func=lambda t: f"{flag(t)} {t}")
            a3 = st.selectbox("Third", [t for t in ALL_TEAMS if t not in [aw, a2]], key="adm_3", format_func=lambda t: f"{flag(t)} {t}")
            a4 = st.selectbox("Fourth", [t for t in ALL_TEAMS if t not in [aw, a2, a3]], key="adm_4", format_func=lambda t: f"{flag(t)} {t}")

            if st.button("Save Final Four Results", key="adm_save_finals"):
                supabase.table("actual_finals").update({
                    "winner": aw, "second": a2, "third": a3, "fourth": a4,
                }).eq("id", af["id"]).execute()
                st.success("Final four results saved!")

        with admin_tab3:
            st.markdown("#### Enter actual special results")
            asp = supabase.table("actual_specials").select("*").execute().data
            asp = asp[0] if asp else {}

            a_scorer = st.text_input("Top Scorer", value=asp.get("top_scorer", "") or "", key="adm_scorer")
            a_red = st.selectbox("Most Red Cards Team", ALL_TEAMS, key="adm_red", format_func=lambda t: f"{flag(t)} {t}")
            a_pen = st.selectbox("Most Penalties Team", ALL_TEAMS, key="adm_pen", format_func=lambda t: f"{flag(t)} {t}")
            a_rev = st.selectbox("Revelation Team", ALL_TEAMS, key="adm_rev", format_func=lambda t: f"{flag(t)} {t}")

            if st.button("Save Special Results", key="adm_save_specials"):
                supabase.table("actual_specials").update({
                    "top_scorer": a_scorer,
                    "most_red_cards_team": a_red,
                    "most_penalties_team": a_pen,
                    "revelation_team": a_rev,
                }).eq("id", asp["id"]).execute()
                st.success("Special results saved!")
    elif admin_pass:
        st.error("❌ Wrong password.")
