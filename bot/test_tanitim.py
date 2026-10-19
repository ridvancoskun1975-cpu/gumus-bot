"""Bilgi sayfasının bir kezlik tanıtım Reels'i (Rıdvan, 19 Ekim 2026: web sayfası tanıtımı, 2. madde "2 uygula").

Çalıştır: python bot/test_tanitim.py   (HIZLI=1: video çizilmez, yalnızca kapak ve açıklama)
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402
import bilgi  # noqa: E402
import sinir  # noqa: E402
import kayit  # noqa: E402
import rapor  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


KOK = Path(__file__).resolve().parent.parent

# Açıklama: fiyatsız, site adresiyle başlar, model ya da şirket adı yok, Instagram sınırında
a = main.tanitim_aciklamasi("Örnek müzik – Pixabay")
kontrol(a.startswith(f"Gram gümüş için tek adres: {bilgi.SITE} (bağlantı biyografide)"), "ilk satır site adresi")
kontrol(len(a) <= 2200, f"açıklama {len(a)} ≤ 2200")
kontrol("Bilgi amaçlıdır, yatırım tavsiyesi değildir." in a and "Müzik: Örnek müzik" in a, "uyarı ve müzik künyesi")
kontrol(not re.search(r"claude|anthropic|opus|sonnet|gemini", a, re.I), "model ya da şirket adı yok")
kontrol(not re.search(r"\d+,\d{2}\s*₺", a), "fiyat yok (video ve açıklama eskimesin)")
kontrol(a.rstrip().endswith(main.HASHTAG_TANITIM) and len(main.HASHTAG_TANITIM.split()) == 5, "5 etiket sonda")

# Sayım ve adlar: hikâyesiz tek Reels
kontrol(sinir.TAHMIN.get("tanitim") == 1 and "tanitim" not in sinir.HIKAYESIZ, "günlük sınırda 1 sayılır")
kontrol("tanitim" not in main.HIKAYE_TURLERI, "hikâyeye gitmez")
kontrol(kayit.ETIKET.get("tanitim") == "Site tanıtımı", "takipçi kaydında adı")
kontrol(rapor.aciklamadan_ad({"caption": a}) == "Site tanıtımı", "haftalık raporda adı")
akis = (KOK / ".github/workflows/paylas.yml").read_text(encoding="utf-8")
kontrol(re.search(r"options: \[[^\]]*\btanitim\b", akis) is not None, "elle çalıştırma seçeneklerinde")
kontrol("tanitim" not in re.findall(r"cron: '([^']+)'", akis), "takvimde yok (yalnızca elle / tek seferlik görev)")
# Sitenin tanıtım kartı şablonu (templates/tanitim.html) ayrı dosya; Reels şablonu onu ezmesin
kontrol("kart(" in (KOK / "templates/tanitim.html").read_text(encoding="utf-8"), "sitenin tanıtım kartı yerinde")
kontrol((KOK / "templates/site-reels.html").exists(), "Reels şablonu ayrı dosyada")

# Üretim: meta, kapak, video (HIZLI=1'de video yerine boş dosya)
if os.environ.get("HIZLI"):
    def sahte_video(tur, veri, mp4, sure=7, seslendirme=None):
        Path(mp4).write_bytes(b"0")
        return True
    main.hareketli_video_uret = sahte_video
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    main.hazirla("tanitim", d, ornek=False)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    kontrol(meta["tur"] == "tanitim" and meta["dosya"].endswith(".mp4") and (d / meta["dosya"]).exists(), "Reels dosyası")
    kontrol(meta["kapak"].endswith(".jpg") and (d / meta["kapak"]).stat().st_size > 20000, "kapak (son hâl)")
    kontrol(meta["kapak_ms"] == int((main.TANITIM_SURE - 0.5) * 1000), "yedek kapak anı")
    kontrol("dosyalar" not in meta and "hikayeler" not in meta and "hikaye_videolari" not in meta, "kaydırmalı ve hikâye yok")
    kontrol(meta["aciklama"].startswith("Gram gümüş için tek adres"), "açıklama metada")
    if not os.environ.get("HIZLI"):
        kontrol((d / meta["dosya"]).stat().st_size > 100000, "video üretildi")

print(f"test_tanitim: {gecen} sınama geçti")
