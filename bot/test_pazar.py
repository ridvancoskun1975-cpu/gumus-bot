"""Pazar Reels'i ve cumartesi hatırlatması sınamaları (ağ yok). Çalıştır: python bot/test_pazar.py

- Pazar Reels'inin paylaşımı patlarsa (geçici engel dahil) hata dışarı sızmaz: yayinla() baştan denerse
  kaydırmalı gönderi ikinci kez gitmesin.
- Cumartesi hatırlatması KURAL: her cumartesi (ve yalnızca cumartesi) görselde ve açıklamada çıkar; kayıt okunamasa
  da düşmez; pazar yorumu ve haftalık özet takvimde durmalı.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


# 1) Reels paylaşımı hata verirse (engel, ağ, kapak) yorum_reelsi sessizce uyarır, hikâye denenmez
cagrilar = []
eski = (main._url_hazir_mi, main._istek, main.hikaye_paylas)
try:
    main._url_hazir_mi = lambda *a, **k: None
    for hata in (main.ErisimEngeli("API access blocked"), RuntimeError("konteyner işlenemedi")):
        def patla(*a, _h=hata, **k):
            raise _h
        main._istek = patla
        main.hikaye_paylas = lambda *a, **k: cagrilar.append("hikaye")
        main.yorum_reelsi("1", {"dosya": "r.mp4", "kapak": "k.jpg", "kapak_ms": 11500, "aciklama": "x"}, "https://ornek/")
    kontrol(cagrilar == [], "Reels gitmediyse hikâye de gitmez, hata sızmaz")

    # Başarılı akış: konteyner → publish → hikâye
    istekler = []
    def sahte(yontem, yol, **p):
        istekler.append((yontem, yol, p.get("media_type")))
        return {"id": "42", "status_code": "FINISHED"}
    main._istek = sahte
    main._hazir_olmasini_bekle = lambda *a, **k: None
    main.yorum_reelsi("1", {"dosya": "r.mp4", "kapak": "k.jpg", "kapak_ms": 11500, "aciklama": "x"}, "https://ornek/")
    kontrol(("POST", "1/media", "REELS") in istekler and ("POST", "1/media_publish", None) in istekler,
            "Reels konteyneri ve yayın")
    kontrol(cagrilar == ["hikaye"], "Reels'ten sonra aynı video hikâyeye")
finally:
    main._url_hazir_mi, main._istek, main.hikaye_paylas = eski

# 2) Cumartesi hatırlatması — KURAL (Rıdvan, 15 Ekim 2026 23:22): "her cumartesi bu yazı çıkmalı"
gun = date(2026, 10, 17)
for i in range(2 * 366):                      # iki yıl boyunca her gün: cumartesi evet, diğer günler hayır
    g = gun + timedelta(days=i)
    kontrol(main.pazar_yorumu_yarin(g) is (g.weekday() == 5), f"{g}: hatırlatma yalnızca ve her cumartesi")

# Kayıt dosyası okunamasa da (ör. önbellek boş) cumartesi hatırlatması düşmez: takvime/kayda bakılmaz
eski_oku = main.gecmis_oku
try:
    def patla():
        raise RuntimeError("kayıt yok")
    main.gecmis_oku = patla
    kontrol(main.pazar_yorumu_yarin(date(2026, 10, 24)) is True, "kayıt okunamasa da cumartesi hatırlatma var")
finally:
    main.gecmis_oku = eski_oku

# Söz boş kalmasın: haftalık özet cumartesi, pazar yorumu pazar zamanlı (biri takvimden çıkarsa kural konuşulur)
akis = (Path(__file__).parent.parent / ".github" / "workflows" / "paylas.yml").read_text(encoding="utf-8")
kontrol("cron: '50 6 * * 6'" in akis, "haftalık özet her cumartesi zamanlı")
kontrol("cron: '50 7 * * 0'" in akis, "pazar yorumu her pazar zamanlı (hatırlatmanın sözü)")

# Haftalık özet her zaman hafta şablonuyla çizilir (özel gün şablonunda şerit yok): gerçek veride özel gün yok
f = main.ornek_haftalik()
f.pop("gecmis_gram", None)                    # haftalik_fiyatlari_al() bu anahtarı hiç vermez
v = main.haftalik_veri_hazirla(f, "@gunlukgumus")
kontrol(not v.get("ozel"), "haftalık özet özel gün şablonuna geçmez")

kontrol("Yarın ~11:00" not in main.aciklama_yaz(v, "hafta"), "hatırlatma yoksa açıklamada da yok")
v["pazar_hatirlatma"] = main.PAZAR_HATIRLATMA
metin = main.aciklama_yaz(v, "hafta")
kontrol("Yarın ~11:00 · Pazar derin analizi: kısa ve orta vade. Kaçırmayın." in metin, "açıklamada hatırlatma")
kontrol(len(metin) <= 2200, "açıklama 2200 sınırında")

# Görselde (Reels ve hikâyesi aynı şablondan) şerit
from jinja2 import Environment, FileSystemLoader  # noqa: E402
html = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True).get_template("hafta.html").render(**v)
kontrol('id="hatirlatma"' in html and "Pazar derin analizi" in html and "Yarın ~11:00" in html, "görselde hatırlatma")

print(f"test_pazar: {gecen} sınama geçti")
