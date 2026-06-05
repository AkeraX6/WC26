# ⚽ World Cup 2026 Prediction Pool 🏆

An internal prediction pool app for friends/colleagues to compete predicting the FIFA World Cup 2026 results.

Built with **Streamlit** + **Supabase** (PostgreSQL backend).

---

## 🎯 How It Works

Each participant enters their name and fills out 3 sections:

### Section 1 – Group Stage (max 36 pts)
Predict the 1st and 2nd place team for each of the 12 groups.
- **1 point** per team correctly predicted in the right position
- **1 point** if a team qualifies but in the wrong position (1st↔2nd)
- **3 points** if both 1st and 2nd are exactly correct

### Section 2 – Final Four (max 25 pts)
Predict the top 4: Winner, Runner-up, Third, and Fourth.
- 🥇 Winner: **10 points**
- 🥈 Runner-up: **7 points**
- 🥉 Third: **5 points**
- 4th: **3 points**

### Section 3 – Special Categories (max 16 pts)
- ⚽ Top Scorer (Golden Boot) — **4 points**
- 🟥 Team with Most Red Cards — **4 points**
- 🎯 Team with Most Penalties Scored — **4 points**
- 🌟 Revelation Team — **4 points**

**Maximum total: 77 points**

---

## 🚀 Setup Guide

### 1. Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a free account.
2. Create a **New Project** (any name, e.g. `worldcup-pool`).
3. Go to **SQL Editor** in the left sidebar.
4. Copy the entire contents of `supabase_schema.sql` and run it.
5. Go to **Settings → API** and copy:
   - **Project URL** (e.g. `https://abcdefg.supabase.co`)
   - **anon public key** (the long JWT string)

### 2. Local Development (VS Code)

```bash
# Clone or download this repository
git clone https://github.com/YOUR_USERNAME/worldcup-pool.git
cd worldcup-pool

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Create secrets file
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml
```

Now edit `.streamlit/secrets.toml` and paste your Supabase credentials:
```toml
SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_KEY = "YOUR_ANON_PUBLIC_KEY"
ADMIN_PASSWORD = "your_secret_admin_password"
```

Run the app:
```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### 3. Deploy to Streamlit Community Cloud (Free Hosting)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Click **New app** → select your repo → set main file to `app.py`.
4. In **Advanced settings → Secrets**, paste:
   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
   SUPABASE_KEY = "YOUR_ANON_PUBLIC_KEY"
   ADMIN_PASSWORD = "your_secret_admin_password"
   ```
5. Click **Deploy**. You'll get a public URL to share with everyone!

---

## 🔧 Admin Panel

The app includes an admin tab (password-protected) where the organizer enters actual results as the tournament progresses. Once results are entered, scores are automatically calculated and the leaderboard updates in real-time.

Default admin password: `worldcup2026` (change it in your secrets).

---

## 📁 Project Structure

```
worldcup-pool/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── supabase_schema.sql     # Database schema (run in Supabase SQL Editor)
├── secrets.toml.example    # Template for secrets (DO NOT commit real secrets)
├── .gitignore              # Ignores secrets and cache files
└── README.md               # This file
```

---

## 📝 GitHub Setup

```bash
cd worldcup-pool
git init
git add .
git commit -m "Initial commit: World Cup 2026 Prediction Pool"
git remote add origin https://github.com/YOUR_USERNAME/worldcup-pool.git
git push -u origin main
```

---

## 🏟️ Groups – FIFA World Cup 2026

| Group | Teams |
|-------|-------|
| A | 🇲🇽 Mexico · 🇿🇦 South Africa · 🇰🇷 Korea Republic · 🇨🇿 Czechia |
| B | 🇨🇦 Canada · 🇧🇦 Bosnia & Herzegovina · 🇶🇦 Qatar · 🇨🇭 Switzerland |
| C | 🇧🇷 Brazil · 🇲🇦 Morocco · 🇭🇹 Haiti · 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland |
| D | 🇺🇸 USA · 🇵🇾 Paraguay · 🇦🇺 Australia · 🇹🇷 Türkiye |
| E | 🇩🇪 Germany · 🇨🇼 Curaçao · 🇨🇮 Côte d'Ivoire · 🇪🇨 Ecuador |
| F | 🇳🇱 Netherlands · 🇯🇵 Japan · 🇸🇪 Sweden · 🇹🇳 Tunisia |
| G | 🇧🇪 Belgium · 🇪🇬 Egypt · 🇮🇷 Iran · 🇳🇿 New Zealand |
| H | 🇪🇸 Spain · 🇨🇻 Cabo Verde · 🇸🇦 Saudi Arabia · 🇺🇾 Uruguay |
| I | 🇫🇷 France · 🇸🇳 Senegal · 🇮🇶 Iraq · 🇳🇴 Norway |
| J | 🇦🇷 Argentina · 🇩🇿 Algeria · 🇦🇹 Austria · 🇯🇴 Jordan |
| K | 🇵🇹 Portugal · 🇨🇩 Congo DR · 🇺🇿 Uzbekistan · 🇨🇴 Colombia |
| L | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England · 🇭🇷 Croatia · 🇬🇭 Ghana · 🇵🇦 Panama |
