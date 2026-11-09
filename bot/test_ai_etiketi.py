# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Meta "AI info" etiketinin sınamaları (bot/main.py → AI_ETIKETI, _reels_konteyneri, _ai_etiketi_bildir). Ağ yok.
Çalıştır: python bot/test_ai_etiketi.py

- Sesli Reels (meta["seslendirme"] dolu: rehber, arşiv, pazar) kabı is_ai_generated=true ile kurulur.
- Yalnız müzikli Reels, fiyat videoları (seslendirme yok) etiketsiz.
- Instagram etiketli kabı reddederse etiketsiz yeniden denenir, paylaşım durmaz; geçici engelde (ErisimEngeli) denenmez.
- Kapak (cover_url) düşerse son kareyle deneme etiketi korur.
- Paylaşımdan sonra etiket okunur (var / YOK); okuma hatası paylaşımı bozmaz.
"""
import io
import os
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


cagrilar = []
KURAL = {}   # davranış: "etiket_red", "kapak_red", "engel", "oku_hata", "etiket_yok"


def sahte_istek(yontem, yol, **params):
    cagrilar.append((yontem, yol, dict(params)))
    if yontem == "GET":
        if KURAL.get("oku_hata"):
            raise RuntimeError("Instagram API hatası (500): okunamadı")
        return {"is_ai_generated": not KURAL.get("etiket_yok")}
    if "is_ai_generated" in params and KURAL.get("engel"):
        raise main.ErisimEngeli("Instagram API hatası (400): API access blocked")
    if "is_ai_generated" in params and KURAL.get("etiket_red"):
        raise RuntimeError("Instagram API hatası (400): {'message': '(#100) Invalid parameter', 'code': 100}")
    if "cover_url" in params and KURAL.get("kapak_red"):
        raise RuntimeError("Instagram API hatası (400): kapak alınamadı")
    return {"id": f"kap{len(cagrilar)}"}


main._istek = sahte_istek
main._hazir_olmasini_bekle = lambda *a, **k: None
main._url_hazir_mi = lambda *a, **k: None


def kur(meta, **kural):
    cagrilar.clear()
    KURAL.clear()
    KURAL.update(kural)
    cikti = io.StringIO()
    with redirect_stdout(cikti), redirect_stderr(cikti):
        k = main._reels_konteyneri("123", "https://gunlukgumus.com/v.mp4", meta, "https://gunlukgumus.com/")
    return k, [c[2] for c in cagrilar if c[0] == "POST"], cikti.getvalue()


SESLI = {"aciklama": "Gümüş rehberi #3", "kapak": "k.jpg", "seslendirme": "Sulafat"}
MUZIKLI = {"aciklama": "Gümüş rehberi #3", "kapak": "k.jpg", "seslendirme": None}
FIYAT = {"aciklama": "Güncel gümüş fiyatları", "kapak": "k.jpg"}

# 1) sesli: tek deneme, etiketli + kapaklı
k, postlar, _ = kur(SESLI)
kontrol(len(postlar) == 1 and postlar[0].get("is_ai_generated") == "true" and "cover_url" in postlar[0],
        f"sesli Reels etiketli ve kapaklı kurulur: {postlar}")
kontrol(postlar[0]["media_type"] == "REELS" and postlar[0]["share_to_feed"] == "true", "Reels alanları korunur")

# 2) müzikli ve fiyat: etiketsiz
for ad, meta in (("müzikli", MUZIKLI), ("fiyat", FIYAT)):
    _, postlar, _ = kur(meta)
    kontrol(len(postlar) == 1 and "is_ai_generated" not in postlar[0], f"{ad} Reels etiketsiz: {postlar}")

# 3) AI_ETIKETI kapalı: sesli de etiketsiz
main.AI_ETIKETI = False
_, postlar, _ = kur(SESLI)
kontrol(len(postlar) == 1 and "is_ai_generated" not in postlar[0], "AI_ETIKETI=False iken etiket gönderilmez")
main.AI_ETIKETI = True

# 4) etiket reddedilir: etiketsiz yeniden denenir, uyarı yazılır
k, postlar, cikti = kur(SESLI, etiket_red=True)
kontrol(k and k.get("id"), "etiket reddedilince yine kap kurulur (paylaşım durmaz)")
kontrol(postlar[-1].get("is_ai_generated") is None and any(p.get("is_ai_generated") for p in postlar),
        f"önce etiketli, sonra etiketsiz deneme: {postlar}")
kontrol("::warning::" in cikti and "etiketsiz" in cikti, "etiket reddinde günlüğe uyarı")

# 5) geçici engel: etiketsiz denemeye geçilmez, hata yayinla()'ya çıkar
try:
    kur(SESLI, engel=True)
    kontrol(False, "ErisimEngeli yukarı çıkmalı")
except main.ErisimEngeli:
    kontrol(all(p.get("is_ai_generated") for p in [c[2] for c in cagrilar if c[0] == "POST"]),
            "geçici engelde etiketsiz deneme yapılmaz")

# 6) kapak düşer: son kareyle deneme de etiketli
_, postlar, _ = kur(SESLI, kapak_red=True)
kontrol(len(postlar) == 2 and all(p.get("is_ai_generated") == "true" for p in postlar)
        and "thumb_offset" in postlar[1], f"kapaksız deneme etiketi korur: {postlar}")

# 7) paylaşım sonrası okuma
for kural, beklenen in (({}, "AI info): var"), ({"etiket_yok": True}, "YOK"), ({"oku_hata": True}, "okunamadı")):
    cagrilar.clear()
    KURAL.clear()
    KURAL.update(kural)
    cikti = io.StringIO()
    with redirect_stdout(cikti), redirect_stderr(cikti):
        main._ai_etiketi_bildir("medya1", SESLI)   # hata vermemeli
    kontrol(beklenen in cikti.getvalue(), f"etiket okuma {kural}: {cikti.getvalue()!r}")
cagrilar.clear()
main._ai_etiketi_bildir("medya1", MUZIKLI)
kontrol(not cagrilar, "müzikli Reels için etiket okunmaz")

# 8) kodda bağlantılar: rehber/arşiv Reels'i ve pazar Reels'i paylaşımdan sonra okur
kaynak = Path(main.__file__).read_text(encoding="utf-8")
kontrol(kaynak.split("def yorum_reelsi(")[1].split("\ndef ")[0].count("_ai_etiketi_bildir(") == 1, "pazar Reels'i etiketi okur")
kontrol(kaynak.split("def _yayinla(")[1].split("\ndef ")[0].count("_ai_etiketi_bildir(") == 1, "Reels paylaşımı etiketi okur")

print(f"test_ai_etiketi: {gecen} kontrol geçti")
