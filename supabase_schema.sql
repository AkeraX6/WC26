-- ============================================================
-- FIFA WORLD CUP 2026 - PREDICTION POOL
-- Run this SQL in your Supabase SQL Editor (supabase.com > SQL)
-- ============================================================

-- 1) USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2) GROUP STAGE PREDICTIONS (Section 1)
--    Each row = one group prediction (1st and 2nd place)
CREATE TABLE IF NOT EXISTS group_predictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    group_name TEXT NOT NULL,          -- 'A', 'B', ... 'L'
    first_place TEXT NOT NULL,         -- team name
    second_place TEXT NOT NULL,        -- team name
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, group_name)
);

-- 3) FINAL FOUR PREDICTIONS (Section 2)
CREATE TABLE IF NOT EXISTS final_predictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    winner TEXT NOT NULL,
    second TEXT NOT NULL,
    third TEXT NOT NULL,
    fourth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 4) SPECIAL CATEGORY PREDICTIONS (Section 3)
CREATE TABLE IF NOT EXISTS special_predictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    top_scorer TEXT NOT NULL,          -- player name (free text)
    most_red_cards_team TEXT NOT NULL,  -- team name
    most_penalties_team TEXT NOT NULL,  -- team name
    revelation_team TEXT NOT NULL,      -- team name
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 5) ACTUAL RESULTS (admin fills this after the tournament)
CREATE TABLE IF NOT EXISTS actual_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    -- Group stage results
    group_name TEXT UNIQUE,            -- 'A' to 'L'
    first_place TEXT,
    second_place TEXT
);

CREATE TABLE IF NOT EXISTS actual_finals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    winner TEXT,
    second TEXT,
    third TEXT,
    fourth TEXT
);

CREATE TABLE IF NOT EXISTS actual_specials (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    top_scorer TEXT,
    most_red_cards_team TEXT,
    most_penalties_team TEXT,
    revelation_team TEXT
);

-- 6) Enable Row Level Security (RLS) but allow all operations
--    (since this is an internal friends pool, we keep it open)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE group_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE special_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE actual_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE actual_finals ENABLE ROW LEVEL SECURITY;
ALTER TABLE actual_specials ENABLE ROW LEVEL SECURITY;

-- Policies: allow everything for anonymous access
CREATE POLICY "Allow all on users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on group_predictions" ON group_predictions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on final_predictions" ON final_predictions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on special_predictions" ON special_predictions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on actual_results" ON actual_results FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on actual_finals" ON actual_finals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on actual_specials" ON actual_specials FOR ALL USING (true) WITH CHECK (true);

-- 7) Pre-populate actual_results rows for each group (empty, ready to fill)
INSERT INTO actual_results (group_name) VALUES
    ('A'), ('B'), ('C'), ('D'), ('E'), ('F'),
    ('G'), ('H'), ('I'), ('J'), ('K'), ('L')
ON CONFLICT (group_name) DO NOTHING;

INSERT INTO actual_finals (winner, second, third, fourth)
VALUES (NULL, NULL, NULL, NULL);

INSERT INTO actual_specials (top_scorer, most_red_cards_team, most_penalties_team, revelation_team)
VALUES (NULL, NULL, NULL, NULL);
