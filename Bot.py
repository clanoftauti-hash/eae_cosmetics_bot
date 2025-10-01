# -*- coding: utf-8 -*-
# EAE Cosmetics Bot — жёсткая структура + умный поиск txt + остаёмся в разделе
# + кнопки 🔄 Restart и 🔙 Geri на всех уровнях

import telebot
from telebot import types
import os, re, unicodedata

# 🔐 Твой токен
TOKEN = "7797695130:AAEZ4ZW5PqjVnIMgS8ChDriMegb5xi1gFlw"

# 📂 Папка с описаниями (txt)
DESCRIPTIONS_PATH = "descriptions"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ───────────────────── УТИЛИТЫ ─────────────────────

def ensure_dir(path: str):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def norm(s: str) -> str:
    """Нормализация строки для надёжного сравнения (диакритика/регистр/пробелы)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")  # ə -> e и т.п.
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def gdrive_direct(url: str) -> str:
    """Переводит любую google-drive ссылку в прямую."""
    if not url:
        return url
    # Только ID
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", url):
        return f"https://drive.google.com/uc?export=download&id={url}"
    # Уже прямой
    if "drive.google.com/uc?" in url:
        return url
    # Формат /file/d/<id>/
    m = re.search(r"drive\.google\.com/file/d/([A-Za-z0-9_-]+)/", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    # Формат ...id=<id>
    m2 = re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if m2:
        return f"https://drive.google.com/uc?export=download&id={m2.group(1)}"
    return url

def slug(s: str) -> str:
    """Слугообразование для файлов: без диакритики, без пробелов/знаков, нижний регистр."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[\s_\-\.]+", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

def list_txt_files() -> list:
    ensure_dir(DESCRIPTIONS_PATH)
    try:
        return [f for f in os.listdir(DESCRIPTIONS_PATH) if f.lower().endswith(".txt")]
    except Exception:
        return []

def resolve_fname(fname: str, title_hint: str = "") -> str:
    """
    Умный поиск реального txt-файла в descriptions.
    Порядок:
      1) точное совпадение
      2) без учёта регистра
      3) по slug от fname
      4) по slug от title_hint (название товара/раздела)
      5) частичное вхождение slug(title) в slug(файла) и наоборот
    """
    files = list_txt_files()
    if not files:
        return ""

    # 1) точное совпадение
    if fname and fname in files:
        return fname

    # 2) без учёта регистра
    if fname:
        low = fname.lower()
        for f in files:
            if f.lower() == low:
                return f

    # 3) slug по имени файла
    if fname:
        target = slug(fname.replace(".txt", ""))
        for f in files:
            if slug(f.replace(".txt", "")) == target:
                return f

    # 4) slug по названию
    if title_hint:
        th = slug(title_hint)
        for f in files:
            if slug(f.replace(".txt", "")) == th:
                return f

    # 5) частичное вхождение
    if title_hint:
        th = slug(title_hint)
        for f in files:
            fs = slug(f.replace(".txt", ""))
            if th in fs or fs in th:
                return f

    return ""

def read_txt(fname: str, title_hint: str = "") -> str:
    """Читает descriptions/<fname>, но сначала «умно» резолвит имя файла."""
    ensure_dir(DESCRIPTIONS_PATH)
    real = resolve_fname(fname, title_hint)
    if not real:
        expect = fname if fname else title_hint
        return f"⚠️ Açıqlama tapılmadı: <code>{expect}</code>"
    try:
        with open(os.path.join(DESCRIPTIONS_PATH, real), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        return f"⚠️ Oxu xətası: <code>{real}</code>\n{e}"

def send_product(chat_id: int, title: str, txt_file: str, image_url: str, cat: str):
    """Показываем товар и остаёмся в его разделе."""
    kb = kb_submenu(cat)
    url = gdrive_direct(image_url) if image_url else None
    caption = f"<b>{title}</b>"
    if url:
        try:
            bot.send_photo(chat_id, url, caption=caption, reply_markup=kb)
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Şəklin yüklənməsi alınmadı: {e}\n{url}", reply_markup=kb)
            bot.send_message(chat_id, caption, reply_markup=kb)
    else:
        bot.send_message(chat_id, caption, reply_markup=kb)
    bot.send_message(chat_id, read_txt(txt_file, title), reply_markup=kb)

# ───────────────────── СТРУКТУРА ─────────────────────

MAIN_MENU = [
    "📦 Məhsullar / 📦 Продукция",
    "📞 Bizimlə Əlaqə",
    "🔄 Restart",
    "🔙 Geri",
]

CATEGORIES = [
    "Molekulyar Düzləşdirmələr",
    "Saç Spreyləri və Parfümləri",
    "Saç Yağları",
    "Botokslar",
    "Maskalar və Şampunlar",
    "Saç Açıcı Pudra və Oksidlər",
    "Super Pro Baxımlar !",
    "Professional Saç Ütüsü",
]

# title, txt_file, image_url
MENU_DATA = {
    "Molekulyar Düzləşdirmələr": [
        ("Liss Ever – Sağlam saçlar", "liss_ever_white.txt",
         "1LJB4-aQsgC8VXh_Ig9fqPw_e31EOM28E"),
        ("Bioliso – Blond zədəli saçlar üçün", "bioliso_blond.txt",
         "1C-xtlXX-o_TuBpWQnn9W23DWyAd7kczH"),
        ("Dərin Təmizləmə Şampunu (öncə)", "derin_temizleme.txt",
         "1VaZdUffBUuzZ1k5iP2GIFDEwiCe2NEkB"),
        ("İstifadə qaydası", "istifade_qaydasi.txt", None),
        ("🔙 Məhsullar", None, None),
    ],

    "Saç Spreyləri və Parfümləri": [
        ("Mirai Uso Essencial Spray (Sənə nə lazımdırsa burada)", "Mirai_Uso_Essencial_Spray.txt",
         "1RJuF30WHBYo195CRYvugk1wjdQ5_bsln"),
        ("Thyrré Uso Essencial Spray (İstilikdən qoruyur və s.)", "thyrré_uso_essencial.txt",
         "1UfqzpSzka15R4-PnG1x8GA4aeo0pFTbm"),
        ("Eaê Uso Essencial – Finalizator Rekonstrutor Sprey", "EAE_Uso_Essencial.txt",
         "1iIUSW9CCJb7ypJhG1vaBHN3pGDrlr36X"),
        ("Eaê Uso Essencial – Finalizator Rekonstrutor Krem", "uso_essencial_finalizador.txt",
         "1KqSt25YZ3mtxlz1Bxo8wil-Ejrd7ceuC"),
        ("Eaê Verão Hair Parfums (Saç Parfümləri)", "eae_sprays_descriptions.txt",
         "1rTo4c97BZMQSS6d2PfQOqf8GWWZEaCu4"),
        ("Eaê Brazil Body & Hair Mist (Bədən və Saç Parfümü)", "body_hair_mist.txt",
         "1EFsti0DQQIAuTYtPDgOnfkKHdKxUPWyN"),
        ("🔙 Məhsullar", None, None),
    ],

    "Saç Yağları": [
        ("Eaê Brazil – Capsules Therapy (Saç dərisi sağlamlığı)", "eae_capsules_therapy.txt",
         "1D9HxN4iZBwOkIJWwAiyuLjk06FvEtyjg"),
        ("Eaê Ozonex Therapy (6 yağ – hər dərdin əlacı)", "EAE_Ozonex_Therapy.txt",
         "1yQ44wmbNfxdnr2VTjGDw3obW79knFRk9"),
        ("Eaê Yağlar Seriyası (bərpa, parlaqlıq, yumşaqlıq, qırılma əleyhinə)", "eae_yaglar_seriyasi.txt",
         "1ClG4UcTe5vPpFdG4gPv0UMJlmGLRaaWM"),
        ("🔙 Məhsullar", None, None),
    ],

    "Botokslar": [
        ("Eaê AntiDepressivo Botox (White/Blue & Macadamia Oil)", "antidepressivo_botox.txt",
         "1Y42F8NZdRBp4CFpgTqjysUZErSWY6hX8"),
        ("Soyuq Botox 🌿 Eaê Quiabo Bambu Babosa 9 em 1", "eaee_quiabo_bambu_babosa.txt",
         "1wfETtFZLvpib-x7M-pQyvWAvKIovwhls"),
        ("🔙 Məhsullar", None, None),
    ],

    "Maskalar və Şampunlar": [
        ("Eaê Ozonated Oil & Pink Clay (Kəpək və seboreyaya qarşı)", "ozonated_pinkclay_set.txt",
         "16RKv9OqtmBhkvFaAAyv27smpC8EN44xw"),
        ("Eaê Jolie Blond – (Rəngin parlaq yumşaqlığını qoruyur)", "Jolie_Blond_Matizador_All.txt",
         "1IQZwSd_XU2uEo8IZo1GLwBbPd9yuBVVQ"),
        ("Eaê COLORS – (Rəngli qoruyan saç maskaları)", "EAE_Rengli_Sac_Maskalari_Emojili.txt",
         "1W6eARyof6HrNz_VkRo4epoqXtXLILDgT"),
        ("Eaê Cachos – Saç baxımı seriyası (qıvrım və dalğalı saçlar üçün)", "Eae_Cachos_4Products.txt",
         "1n7e2GQ4kQ7WhuaqpZSMxOlduV1382RJj"),
        ("Eaê Detox – Gelatina Nutritiva", "eae_detox_set.txt",
         "1ICDHgaq5pA3RTVcxjqAqfj1Z45Ey3DqS"),
        ("Eaê Teia de Queratina (Saç bərпа maskası)", "tela_de_k.txt", None),
        ("Eaê Macadamia (Quruluğa qarşı nəmləndirici)", "macadamia.txt", None),
        ("Eaê Argila Preta (Yağlı və zəif saçlar üçün)", "argila.txt", None),
        ("Thyrré Bio Liso Espelhado (Botox və düzləşдirmədən sonra)", "bio_liso_espelhado_pos_progressiva.txt",
         "1vTSUUhWCuCmUcse91wTMSJ_HUHbtf-dM"),
        ("Thyrré Água / Menta / Frutas (Nəmləndirmə, parlaqlıq, rəngin qorunması)", "thyrre_6in1_series.txt",
         "1GpLc1FqwS-Wnw3729jpDUnD7-nqbdUHx"),
        ("Thyrré Revita Lizante (Hidro-rekonstruktiv bərپا maskası)", "revita_lizante.txt",
         "1uBIsW7HxKq4R0tkcx3yI2ZHytOcF_ic-"),
        ("Thyrré Cacto e Alecrim (Qidalandırıcı saç maskası)", "cacto_alecrim.txt",
         "1MG1-F0B9X81KF8p8xwNf8tbT0ckz8uog"),
        ("Eaê Bio Monovin (Saç uzanması, bərпа, parıltı)", "EAE_Bio_Monovin.txt",
         "1i_SC4lT-budxurUiD4Kmo66vyt34FbYd"),
        ("Eaê Matizador (rəng, parlaqlıq və qulluq bir yerdə)", "matizador_series.txt",
         "1EoIKFqEaSIbVfGnuGyeT2WBN3lCejDXh"),
        ("🔙 Məhsullar", None, None),
    ],

    "Saç Açıcı Pudra və Oksidlər": [
        ("Eaê Jolie Blond – Professional Açıcı Pudra", "jolie_blond_pudra.txt",
         "1kkJSgSt6IOuBMTeqrbfIzu382xUaBGKe"),
        ("Eaê Jolie Blond – Oksidlər (VOL:10,20,30,40)", "eae_jolie_blond_ox.txt",
         "1Dk0CV7uyiN3bTGM1GdrNJ6Nc0JKTKYYC"),
        ("🔙 Məhsullar", None, None),
    ],

    "Super Pro Baxımlar !": [
        ("Nano Crystallization", "nano_crystallization.txt",
         "1NQbDPgrXdw0SFQVciDp0uZpX8EAe-D7c"),
        ("Plex Reabilitação (Qırılmaya/Elastiklik bərпа seriyası)", "eae_reabilitacao_capilar.txt",
         "1xe_HWcjT8nnyvUUpXB264GPdg4By3vTI"),
        ("Thyrré – Reabilitação Capilar (Tam бərпа seriyası)", "thyrré_reabilitacao_capilar.txt",
         "11l0cRRiMkom2elJxrp80xW8nMCyKOGXk"),
        ("🔙 Məhsullar", None, None),
    ],

    "Professional Saç Ütüsü": [
        ("Lizze Professional Saç Ütüsü — ütü", "lizze.txt",
         "1ko__LCWi3gRVNYOpOM7_fywjbvziIg71"),
        ("🔙 Məhsullar", None, None),
    ],
}

# Быстрый индекс для «умного» поиска по названию товара
TITLE_INDEX = {}
for cat, items in MENU_DATA.items():
    for (t, f, u) in items:
        TITLE_INDEX[norm(t)] = (cat, t, f, u)

# ───────────────────── КЛАВИАТУРЫ ─────────────────────

def kb_main():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for b in MAIN_MENU:
        kb.add(types.KeyboardButton(b))
    return kb

def kb_categories():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for name in CATEGORIES:
        kb.add(types.KeyboardButton(name))
    kb.add(types.KeyboardButton("🔄 Restart"))
    kb.add(types.KeyboardButton("🔙 Geri"))
    return kb

def kb_submenu(cat: str):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for (title, _, __) in MENU_DATA.get(cat, []):
        kb.add(types.KeyboardButton(title))
    kb.add(types.KeyboardButton("🔄 Restart"))
    kb.add(types.KeyboardButton("🔙 Geri"))
    return kb

# ───────────────────── ХЕНДЛЕРЫ ─────────────────────

@bot.message_handler(commands=["start", "restart"])
def cmd_start(m):
    bot.send_message(
        m.chat.id,
        "👋 Salam! EAE Cosmetics Bot-a xoş gəlmisiniz.\nSeçim edin:",
        reply_markup=kb_main()
    )

@bot.message_handler(func=lambda m: m.text == "🔄 Restart")
def on_restart(m):
    cmd_start(m)

@bot.message_handler(func=lambda m: m.text == "📦 Məhsullar / 📦 Продукция")
def on_products(m):
    bot.send_message(m.chat.id, "📂 Kateqoriyanı seçin:", reply_markup=kb_categories())

# 🔧 ИСПРАВЛЕНО: читаем descriptions/Elage.txt
@bot.message_handler(func=lambda m: m.text == "📞 Bizimlə Əlaqə")
def on_contacts(m):
    # Бот сам найдёт файл даже если регистр/диакритика отличаются
    bot.send_message(m.chat.id, read_txt("Elage.txt", "Bizimlə Əlaqə"), reply_markup=kb_main())

@bot.message_handler(func=lambda m: m.text in ("🔙 Geri", "🔙 Məhsullar"))
def on_back(m):
    on_products(m)

# Открыть категорию
@bot.message_handler(func=lambda m: m.text in MENU_DATA.keys())
def open_category(m):
    cat = m.text
    bot.send_message(m.chat.id, f"📂 {cat}", reply_markup=kb_submenu(cat))

# Открыть товар (умный поиск по всем разделам)
@bot.message_handler(func=lambda m: True)
def open_product(m):
    query = norm(m.text)
    # прямое совпадение
    if query in TITLE_INDEX:
        cat, title, fname, url = TITLE_INDEX[query]
        send_product(m.chat.id, title, fname, url, cat)
        return
    # мягкий поиск по вхождению
    for key, (cat, title, fname, url) in TITLE_INDEX.items():
        if query and query in key:
            send_product(m.chat.id, title, fname, url, cat)
            return
    bot.send_message(m.chat.id, "Seçim edin:", reply_markup=kb_main())

# ───────────────────── START ─────────────────────
if __name__ == "__main__":
    print("EAE Bot start...")
    ensure_dir(DESCRIPTIONS_PATH)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
