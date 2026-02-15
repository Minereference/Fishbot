import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import time
from config import TOKEN

DB_FILE = "fish.db"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------- DATABASE --------------------

DEFAULT_REGION = "River"
FISH_COOLDOWN = 10

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS rarities (
        name TEXT PRIMARY KEY,
        weight REAL NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        price INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS fish (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        rarity TEXT NOT NULL,
        min_size REAL,
        max_size REAL,
        value_per_kg INTEGER,
        FOREIGN KEY (rarity) REFERENCES rarities(name)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS fish_regions (
        fish_id INTEGER,
        region_id INTEGER,
        PRIMARY KEY (fish_id, region_id),
        FOREIGN KEY (fish_id) REFERENCES fish(id),
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS rods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        rarity TEXT NOT NULL,
        price INTEGER NOT NULL,
        bonus REAL NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        coins INTEGER DEFAULT 100 CHECK (coins >= 0),
        bait INTEGER DEFAULT 5 CHECK (bait >= 0),
        rod_id INTEGER,
        region_id INTEGER,
        last_fish INTEGER DEFAULT 0,
        favorite_fish_id INTEGER,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        FOREIGN KEY (rod_id) REFERENCES rods(id),
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_catch (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        fish_id INTEGER,
        size REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_regions (
        user_id INTEGER,
        region_id INTEGER,
        PRIMARY KEY (user_id, region_id),
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )
    """)

    # ---- SEEDS ----

    c.executemany("INSERT OR IGNORE INTO rarities VALUES (?, ?)", [
        ("Common", 0.5),
        ("Uncommon", 0.3),
        ("Rare", 0.12),
        ("Epic", 0.05),
        ("Legendary", 0.02),
        ("Mythic", 0.005),
    ])

    c.executemany("""
    INSERT OR IGNORE INTO regions (name, price)
    VALUES (?, ?)
    """, [
        ("River", 0),
        ("Ocean", 8000),
        ("Deep Sea", 75000),
        ("Mariana's Trench", 200000),
    ])


    c.executemany("""
    INSERT OR IGNORE INTO fish (name, rarity, min_size, max_size, value_per_kg)
    VALUES (?, ?, ?, ?, ?)
    """, [

        # 🐟 Common
        ("Goldfish", "Common", 5, 15, 1),
        ("Salmon", "Common", 30, 70, 2),
        ("Trout", "Common", 25, 60, 2),
        ("Carp", "Common", 20, 50, 2),
        ("Tilapia", "Common", 15, 45, 2),
        ("Anglerfish", "Common", 25, 35, 4),
        ("Blobfish", "Common", 20, 45, 5),

        # 🐠 Uncommon
        ("Catfish", "Uncommon", 40, 80, 5),
        ("Bass", "Uncommon", 35, 75, 5),
        ("Snapper", "Uncommon", 30, 60, 4),
        ("Mackerel", "Uncommon", 25, 55, 4),
        ("Sawfish", "Uncommon", 25, 55, 5),
        ("Deep Squid", "Uncommon", 30, 65, 6),

        # 🐡 Rare
        ("Tuna", "Rare", 100, 250, 6),
        ("Swordfish", "Rare", 150, 300, 8),
        ("Piranha", "Rare", 15, 40, 12),
        ("Electric Eel", "Rare", 80, 150, 8),
        ("Puffer Fish", "Rare", 2, 7, 87),

        # 🦈 Epic
        ("Shark", "Epic", 200, 400, 15),
        ("Blue Marlin", "Epic", 250, 450, 12),
        ("Dolphin", "Epic", 350, 450, 11),
        ("Oarfish", "Epic", 350, 550, 12),

        # 🦕 Legendary
        ("Megalodon", "Legendary", 2000, 2500, 3),
        ("Nessie", "Legendary", 1700, 2000, 4),
        ("Whale", "Legendary", 5000, 8000, 1),
        ("Collosal Squid", "Legendary", 2000, 3000, 5),

        # 🐉 Mythic
        ("Dragon", "Mythic", 4000, 7000, 4),
        ("Kraken", "Mythic", 2000, 5000, 5),
        ("Leviathan", "Mythic", 3000, 6000, 4),
        ("Abyssal Serpent", "Mythic", 4000, 8000, 4),
        ("Celestial Whale", "Mythic", 5000, 10000, 3),
    ])


    c.execute("SELECT id, name FROM fish")
    fish_map = {name: fid for fid, name in c.fetchall()}

    c.execute("SELECT id, name FROM regions")
    region_map = {name: rid for rid, name in c.fetchall()}

    fish_regions = [

        # River
        ("Goldfish", "River"),
        ("Salmon", "River"),
        ("Trout", "River"),
        ("Carp", "River"),
        ("Tilapia", "River"),
        ("Catfish", "River"),
        ("Bass", "River"),
        ("Piranha", "River"),
        ("Electric Eel", "River"),
        ("Nessie", "River"),

        # Ocean
        ("Snapper", "Ocean"),
        ("Mackerel", "Ocean"),
        ("Tuna", "Ocean"),
        ("Swordfish", "Ocean"),
        ("Puffer Fish", "Ocean"),
        ("Blue Marlin", "Ocean"),
        ("Dolphin", "Ocean"),
        ("Shark", "Ocean"),

        # Deep Sea
        ("Anglerfish", "Deep Sea"),
        ("Sawfish", "Deep Sea"),
        ("Oarfish", "Deep Sea"),
        ("Whale", "Deep Sea"),
        ("Megalodon", "Deep Sea"),
        ("Leviathan", "Deep Sea"),
        ("Abyssal Serpent", "Deep Sea"),

        # Mariana's Trench
        ("Blobfish", "Mariana's Trench"),
        ("Deep Squid", "Mariana's Trench"),
        ("Collosal Squid", "Mariana's Trench"),
        ("Dragon", "Mariana's Trench"),
        ("Kraken", "Mariana's Trench"),
        ("Celestial Whale", "Mariana's Trench"),
    ]   

    for fish, region in fish_regions:
        c.execute("""
        INSERT OR IGNORE INTO fish_regions (fish_id, region_id)
        VALUES (?, ?)
        """, (fish_map[fish], region_map[region]))


        c.executemany("""
        INSERT OR IGNORE INTO rods (name, rarity, price, bonus)
        VALUES (?, ?, ?, ?)
        """, [
            ("Wooden Rod", "Common", 0, 1.0),
            ("Quality Rod", "Uncommon", 3000, 1.3),
            ("Carbon Fiber Rod", "Rare", 20000, 1.7),
            ("Professional Rod", "Epic", 60000, 2.2),
            ("Poseidon's Rod", "Legendary", 240000, 4.5),
            ("Mariana's Rod", "Mythic", 1000000, 8.6),
        ])

    conn.commit()
    conn.close()


# -------------------- HELPERS --------------------

def xp_for_level(level: int) -> int:
    return 100 + (level - 1) * 50

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT id FROM rods WHERE name = 'Wooden Rod'")
    default_rod = c.fetchone()[0]

    c.execute("SELECT id FROM regions WHERE name = ?", (DEFAULT_REGION,))
    default_region = c.fetchone()[0]

    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()

    if not user:
        c.execute("""
        INSERT INTO users (user_id, rod_id, region_id)
        VALUES (?, ?, ?)
        """, (user_id, default_rod, default_region))

        c.execute("""
        INSERT OR IGNORE INTO user_regions (user_id, region_id)
        SELECT ?, id FROM regions WHERE name = 'River'
        """, (user_id,))

        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()

    conn.close()
    return user


# -------------------- COMMANDS --------------------

@bot.tree.command(name="fish")
async def fish(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    now = int(time.time())
    last_fish = user[5]  # index of last_fish column

    remaining = FISH_COOLDOWN - (now - last_fish)
    if remaining > 0:
        await interaction.response.send_message(
            f"⏳ Tunggu **{remaining} detik** sebelum memancing lagi.",
            ephemeral=True
        )
        return

    if user[2] <= 0:
        await interaction.response.send_message("❌ Kamu kehabisan bait.", ephemeral=True)
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    UPDATE users
    SET bait = bait - 1,
        last_fish = ?
    WHERE user_id = ?
    AND bait > 0
    """, (now, interaction.user.id))

    if c.rowcount == 0:
        conn.close()
        await interaction.response.send_message(
            "❌ Kamu kehabisan bait.",
            ephemeral=True
        )
        return



    c.execute("""
    SELECT f.id, f.name, f.rarity, f.min_size, f.max_size, f.value_per_kg, r.weight
    FROM fish f
    JOIN rarities r ON f.rarity = r.name
    JOIN fish_regions fr ON f.id = fr.fish_id
    WHERE fr.region_id = ?
    """, (user[4],))

    fish_list = c.fetchall()

    c.execute("""
    SELECT bonus, name FROM rods WHERE id = ?
    """, (user[3],))
    rod_bonus, rod_name = c.fetchone()

    weights = []
    for f in fish_list:
        base = f[6]
        if f[2] not in ("Common", "Uncommon"):
            base *= rod_bonus
        weights.append(base)

    chosen = random.choices(fish_list, weights=weights)[0]
    size = round(random.uniform(chosen[3], chosen[4]), 1)

    fish_rarity = chosen[2]

    rarity_xp = {
    "Common": 0,
    "Uncommon": 2,
    "Rare": 5,
    "Epic": 15,
    "Legendary": 90,
    "Mythic": 290
}

    gained_xp = 10 + rarity_xp.get(fish_rarity, 0)

    user_xp = user[7]     # adjust index if needed
    user_level = user[8]

    new_xp = user_xp + gained_xp

    while new_xp >= xp_for_level(user_level):
        new_xp -= xp_for_level(user_level)
        user_level += 1

    c.execute(
        "INSERT INTO user_catch (user_id, fish_id, size) VALUES (?, ?, ?)",
        (interaction.user.id, chosen[0], size)
    )

    c.execute("""
    UPDATE users
    SET xp = ?, level = ?
    WHERE user_id = ?
    """, (new_xp, user_level, interaction.user.id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"🎣 {interaction.user.mention} menggunakan **{rod_name}** dan mendapatkan "
        f"**{chosen[1]}** ({chosen[2]}) seberat **{size} kg**!"
    )

@bot.tree.command(name="level", description="Check your level and XP progress.")
async def level(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    xp = user[7]
    level = user[8]
    needed = xp_for_level(level)

    await interaction.response.send_message(
        f"📈 **Level {level}**\n"
        f"XP: {xp} / {needed}",
        ephemeral=True
    )

@bot.tree.command(
    name="fishipedia",
    description="Melihat daftar ikan. Bisa difilter berdasarkan rarity."
)
@app_commands.describe(rarity="Common, Uncommon, Rare, Epic, Legendary, Mythic")
async def fishipedia(
    interaction: discord.Interaction,
    rarity: str | None = None
):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    params = []
    query = """
        SELECT name, rarity, min_size, max_size, value_per_kg
        FROM fish
    """

    if rarity:
        query += " WHERE rarity = ?"
        params.append(rarity.capitalize())

    query += """
        ORDER BY 
            CASE rarity
                WHEN 'Common' THEN 1
                WHEN 'Uncommon' THEN 2
                WHEN 'Rare' THEN 3
                WHEN 'Epic' THEN 4
                WHEN 'Legendary' THEN 5
                WHEN 'Mythic' THEN 6
            END,
            name
    """

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    if not rows:
        await interaction.response.send_message(
            "Tidak ada ikan dengan rarity tersebut.",
            ephemeral=True
        )
        return

    title = "📖 Fishipedia"
    if rarity:
        title += f" — {rarity.capitalize()}"

    msg = f"**{title}**\n\n"

    for name, r, min_s, max_s, value in rows:
        msg += f"• **{name}** — {min_s}-{max_s} kg (💰 {value}/kg)\n"

    # Safety slice in case someone adds 200 fish later
    msg = msg[:1900]

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="travel", description="Pergi ke region yang sudah kamu unlock.")
@app_commands.describe(region="Nama region tujuan")
async def travel(interaction: discord.Interaction, region: str):
    user_id = interaction.user.id
    region = region.capitalize()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 1️⃣ Region must exist
    c.execute("SELECT id FROM regions WHERE name = ?", (region,))
    row = c.fetchone()

    if not row:
        conn.close()
        await interaction.response.send_message(
            "❌ Region tersebut tidak ada.",
            ephemeral=True
        )
        return

    region_id = row[0]

    # 2️⃣ User must have unlocked it
    c.execute("""
        SELECT 1 FROM user_regions
        WHERE user_id = ? AND region_id = ?
    """, (user_id, region_id))

    unlocked = c.fetchone()

    if not unlocked:
        conn.close()
        await interaction.response.send_message(
            f"🔒 Kamu belum unlock **{region}**.",
            ephemeral=True
        )
        return

    # 3️⃣ Travel allowed
    c.execute("""
        UPDATE users SET region_id = ?
        WHERE user_id = ?
    """, (region_id, user_id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✈️ Kamu berhasil pergi ke **{region}**!"
    )

@bot.tree.command(
    name="regions",
    description="Lihat daftar region yang tersedia dan statusnya."
)
async def regions(interaction: discord.Interaction):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # All regions
    c.execute("""
        SELECT r.id, r.name, r.price
        FROM regions r
        ORDER BY r.price
    """)
    all_regions = c.fetchall()

    # User unlocked regions
    c.execute("""
        SELECT region_id
        FROM user_regions
        WHERE user_id = ?
    """, (interaction.user.id,))
    unlocked = {row[0] for row in c.fetchall()}

    conn.close()

    msg = "🌍 **Regions**\n\n"

    for region_id, name, price in all_regions:
        if region_id in unlocked:
            msg += f"✅ **{name}** — Unlocked\n"
        else:
            msg += f"🔒 **{name}** — 💰 {price} coins\n"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(
    name="unlock",
    description="Unlock region baru untuk memancing."
)
@app_commands.describe(region="Nama region yang ingin dibuka")
async def unlock(interaction: discord.Interaction, region: str):
    user = get_user(interaction.user.id)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get region
    c.execute("""
        SELECT id, name, price
        FROM regions
        WHERE LOWER(name) = LOWER(?)
    """, (region,))
    region_data = c.fetchone()

    if not region_data:
        await interaction.response.send_message(
            "❌ Region tidak ditemukan.",
            ephemeral=True
        )
        conn.close()
        return

    region_id, name, price = region_data

    # Check if already unlocked
    c.execute("""
        SELECT 1 FROM user_regions
        WHERE user_id = ? AND region_id = ?
    """, (interaction.user.id, region_id))

    if c.fetchone():
        await interaction.response.send_message(
            f"✅ **{name}** sudah terbuka.",
            ephemeral=True
        )
        conn.close()
        return

    if user[1] < price:
        await interaction.response.send_message(
            f"❌ Coins tidak cukup. Butuh **{price} coins**.",
            ephemeral=True
        )
        conn.close()
        return

    # Unlock
    c.execute("""
        INSERT INTO user_regions (user_id, region_id)
        VALUES (?, ?)
    """, (interaction.user.id, region_id))

    c.execute("""
        UPDATE users SET coins = coins - ?
        WHERE user_id = ?
    """, (price, interaction.user.id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"🌍 Kamu membuka **{name}** seharga **{price} coins**!"
    )

@bot.tree.command(
    name="buybait",
    description="Membeli bait untuk memancing. Harga 10 coins per bait."
)
async def buybait(interaction: discord.Interaction, jumlah: int):
    if jumlah <= 0:
        await interaction.response.send_message(
            "Jumlah bait harus lebih dari 0.", ephemeral=True
        )
        return

    user = get_user(interaction.user.id)
    harga = jumlah * 10

    if user[1] < harga:
        await interaction.response.send_message(
            f"❌ Coins tidak cukup. Butuh **{harga} coins**.",
            ephemeral=True
        )
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET coins = coins - ?, bait = bait + ?
        WHERE user_id = ?
    """, (harga, jumlah, interaction.user.id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"🪣 Kamu membeli **{jumlah} bait** seharga **{harga} coins**!"
    )

@bot.tree.command(
    name="rodshop",
    description="Lihat daftar pancingan dan harganya."
)
async def rodshop(interaction: discord.Interaction):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT name, rarity, price, bonus
        FROM rods
        ORDER BY
            CASE rarity
                WHEN 'Common' THEN 1
                WHEN 'Uncommon' THEN 2
                WHEN 'Rare' THEN 3
                WHEN 'Epic' THEN 4
                WHEN 'Legendary' THEN 5
                WHEN 'Mythic' THEN 6
            END,
            price
    """)
    rods = c.fetchall()
    conn.close()

    msg = "**🎣 Rod Shop**\n\n"

    for name, rarity, price, bonus in rods:
        if price == 0:
            msg += f"• **{name}** ({rarity}) — Starter rod\n"
        else:
            msg += f"• **{name}** ({rarity}) — 💰 {price} coins\n"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="inventory", description="Lihat ikan yang kamu miliki.")
async def inventory(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    favorite_id = user[6]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT f.id, f.name, COUNT(*), ROUND(SUM(uc.size), 1)
        FROM user_catch uc
        JOIN fish f ON uc.fish_id = f.id
        WHERE uc.user_id = ?
        GROUP BY f.id, f.name
        ORDER BY f.name
    """, (interaction.user.id,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        await interaction.response.send_message(
            "🎒 Inventory kosong.",
            ephemeral=True
        )
        return

    msg = "🎒 **Inventory**\n\n"

    for fish_id, name, count, total_size in rows:
        star = " ⭐" if fish_id == favorite_id else ""
        msg += f"• **{name}**{star} — x{count} ({total_size} kg)\n"

    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(
    name="favorite",
    description="Menjadikan ikan sebagai favorit."
)
@app_commands.describe(fish_name="Nama ikan yang ingin difavoritkan")
async def favorite(interaction: discord.Interaction, fish_name: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Find fish
    c.execute("""
        SELECT id, name
        FROM fish
        WHERE LOWER(name) = LOWER(?)
    """, (fish_name,))
    fish = c.fetchone()

    if not fish:
        conn.close()
        await interaction.response.send_message(
            "❌ Ikan tidak ditemukan.",
            ephemeral=True
        )
        return

    fish_id, name = fish

    # Set favorite
    c.execute("""
        UPDATE users
        SET favorite_fish_id = ?
        WHERE user_id = ?
    """, (fish_id, interaction.user.id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"⭐ **{name}** sekarang menjadi ikan favoritmu!"
    )

@bot.tree.command(
    name="unfavorite",
    description="Menghapus ikan favoritmu."
)
async def unfavorite(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    # user[6] = favorite_fish_id
    if user[6] is None:
        await interaction.response.send_message(
            "❌ Kamu belum punya ikan favorit.",
            ephemeral=True
        )
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET favorite_fish_id = NULL
        WHERE user_id = ?
    """, (interaction.user.id,))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        "⭐ Ikan favoritmu telah dihapus."
    )


@bot.tree.command(
    name="buyrod",
    description="Beli pancingan baru untuk meningkatkan peluang ikan langka."
)
@app_commands.describe(rod_name="Nama rod yang ingin dibeli")
async def buyrod(interaction: discord.Interaction, rod_name: str):
    user = get_user(interaction.user.id)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get rod data
    c.execute("""
        SELECT id, name, price, rarity
        FROM rods
        WHERE LOWER(name) = LOWER(?)
    """, (rod_name,))
    rod = c.fetchone()

    if not rod:
        await interaction.response.send_message(
            "❌ Rod tidak ditemukan.",
            ephemeral=True
        )
        conn.close()
        return

    rod_id, name, price, rarity = rod

    if user[1] < price:
        await interaction.response.send_message(
            f"❌ Coins tidak cukup. Butuh **{price} coins**.",
            ephemeral=True
        )
        conn.close()
        return

    # Buy rod
    c.execute("""
        UPDATE users
        SET coins = coins - ?, rod_id = ?
        WHERE user_id = ?
    """, (price, rod_id, interaction.user.id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"🪝 Kamu membeli **{name}** ({rarity}) seharga **{price} coins**!"
    )

@bot.tree.command(name="sellall")
async def sellall(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    favorite_id = user[6]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT f.value_per_kg, uc.size
        FROM user_catch uc
        JOIN fish f ON uc.fish_id = f.id
        WHERE uc.user_id = ?
        AND ( ? IS NULL OR uc.fish_id != ? )
    """, (interaction.user.id, favorite_id, favorite_id))

    rows = c.fetchall()

    if not rows:
        await interaction.response.send_message(
            "Tidak ada ikan yang bisa dijual (favorit disimpan).",
            ephemeral=True
        )
        conn.close()
        return

    total = int(sum(v * s for v, s in rows))

    c.execute("""
        DELETE FROM user_catch
        WHERE user_id = ?
        AND ( ? IS NULL OR fish_id != ? )
    """, (interaction.user.id, favorite_id, favorite_id))

    c.execute("""
        UPDATE users SET coins = coins + ?
        WHERE user_id = ?
    """, (total, interaction.user.id))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"💰 Kamu mendapatkan **{total} coins**! (ikan favorit tidak dijual)"
    )


@bot.tree.command(name="backpack", description="Lihat saldo, bait, dan rod yang kamu miliki.")
async def backpack(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT name, rarity FROM rods WHERE id = ?", (user[3],))
    rod = c.fetchone()
    conn.close()

    rod_name, rod_rarity = rod

    msg = (
        f"🎒 **Backpack {interaction.user.display_name}**\n\n"
        f"💰 **Coins:** {user[1]}\n"
        f"🪣 **Bait:** {user[2]}\n"
        f"🎣 **Rod:** {rod_name} ({rod_rarity})"
    )

    await interaction.response.send_message(msg)

@bot.tree.command(name="leaderboard", description="Show leaderboard rankings.")
@app_commands.describe(category="xp, money, or catches")
async def leaderboard(interaction: discord.Interaction, category: str):
    category = category.lower()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if category == "xp":
        c.execute("""
            SELECT user_id, level, xp
            FROM users
            ORDER BY level DESC, xp DESC
            LIMIT 10
        """)
        rows = c.fetchall()

        title = "🏆 **XP Leaderboard**"
        lines = []
        for i, (user_id, level, xp) in enumerate(rows, start=1):
            user = await bot.fetch_user(user_id)
            lines.append(f"**{i}. {user.name}** — Level {level} ({xp} XP)")

    elif category == "money":
        c.execute("""
            SELECT user_id, coins
            FROM users
            ORDER BY coins DESC
            LIMIT 10
        """)
        rows = c.fetchall()

        title = "💰 **Money Leaderboard**"
        lines = []
        for i, (user_id, coins) in enumerate(rows, start=1):
            user = await bot.fetch_user(user_id)
            lines.append(f"**{i}. {user.name}** — {coins} coins")

    elif category == "catches":
        c.execute("""
            SELECT user_id, COUNT(*) as total
            FROM user_catch
            GROUP BY user_id
            ORDER BY total DESC
            LIMIT 10
        """)
        rows = c.fetchall()

        title = "🎣 **Catches Leaderboard**"
        lines = []
        for i, (user_id, total) in enumerate(rows, start=1):
            user = await bot.fetch_user(user_id)
            lines.append(f"**{i}. {user.name}** — {total} fish")

    else:
        conn.close()
        await interaction.response.send_message(
            "❌ Invalid category. Use `xp`, `money`, or `catches`.",
            ephemeral=True
        )
        return

    conn.close()

    if not rows:
        await interaction.response.send_message(
            "No data available yet.",
            ephemeral=True
        )
        return

    msg = title + "\n\n" + "\n".join(lines)
    await interaction.response.send_message(msg)

@bot.tree.command(name="info", description="Menampilkan semua command dan fungsinya.")
async def info(interaction: discord.Interaction):
    info_text = (
        "🎣 *Fishing Bot Command List*\n\n"

        "🐟 /fish — Memancing ikan secara acak (menggunakan bait & cooldown).\n"
        "📈 /level — Melihat level dan progress XP kamu.\n"
        "🏆 /leaderboard <xp/money/catches> — Melihat peringkat pemain.\n\n"

        "📖 /fishipedia — Melihat daftar ikan dalam database (bisa filter rarity).\n"
        "🎒 /inventory — Melihat hasil tangkapanmu.\n"
        "⭐ /favorite <nama ikan> — Menjadikan ikan sebagai favorit.\n"
        "❌ /unfavorite — Menghapus ikan favoritmu.\n"
        "💰 /sellall — Menjual semua ikanmu (ikan favorit tidak dijual).\n\n"

        "🪣 /buybait <jumlah> — Membeli bait (10 coins per bait).\n"
        "🎣 /rodshop — Melihat daftar pancingan.\n"
        "🪝 /buyrod <nama> — Membeli pancingan baru.\n"
        "💼 /backpack — Melihat saldo, bait, dan rod.\n\n"

        "🌍 /regions — Melihat daftar region dan status unlock.\n"
        "🔓 /unlock <region> — Membuka region baru.\n"
        "✈️ /travel <region> — Pergi ke region yang sudah dibuka.\n\n"

        "💵 /money <jumlah> — (Admin/Test) Menambah atau mengurangi coins."
    )

    await interaction.response.send_message(info_text, ephemeral=True)


@bot.tree.command(
    name="money",
    description="(TESTING) Menambahkan coins ke akunmu."
)
@app_commands.describe(amount="Jumlah coins yang ingin ditambahkan")
async def money(interaction: discord.Interaction, amount: int):

    if interaction.user.id != 773373891728244746:
        return


    # allow positive or negative, but not zero
    if amount == 0:
        await interaction.response.send_message(
            "Jumlah tidak boleh 0.",
            ephemeral=True
        )
        return


    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    UPDATE users
    SET coins = MAX(coins + ?, 0)
    WHERE user_id = ?
    """, (amount, interaction.user.id))


    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"💰 **{amount} coins** ditambahkan ke akunmu.",
        ephemeral=True
    )



@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"Bot online sebagai {bot.user}")

bot.run(TOKEN)