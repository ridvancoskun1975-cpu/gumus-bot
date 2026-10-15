"""Pazar Reels'i ve cumartesi hatırlatması sınamaları (ağ yok). Çalıştır: python bot/test_pazar.py

- Pazar Reels'inin paylaşımı patlarsa (geçici engel dahil) hata dışarı sızmaz: yayinla() baştan denerse
  kaydırmalı gönderi ikinci kez gitmesin.
- Cumartesi hatırlatması yalnızca cumartesi ve yarın pazar yorumu takvimdeyse çıkar; açıklamaya da yazılır.
"""
import sys
from datetime import date
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

# 2) Cumartesi hatırlatması
kontrol(main.pazar_yorumu_yarin(date(2026, 10, 16)) is False, "cuma: hatırlatma yok")
kontrol(main.pazar_yorumu_yarin(date(2026, 10, 18)) is False, "pazar: hatırlatma yok")
f = main.ornek_haftalik()
v = main.haftalik_veri_hazirla(f, "@gunlukgumus")
kontrol("Yarın ~11:00" not in main.aciklama_yaz(v, "hafta"), "hatırlatma yoksa açıklamada da yok")
v["pazar_hatirlatma"] = main.PAZAR_HATIRLATMA
metin = main.aciklama_yaz(v, "hafta")
kontrol("Yarın ~11:00 · Pazar derin analizi: kısa, orta ve uzun vade. Kaçırmayın." in metin, "açıklamada hatırlatma")
kontrol(len(metin) <= 2200, "açıklama 2200 sınırında")

print(f"test_pazar: {gecen} sınama geçti")
