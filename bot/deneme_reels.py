# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Deneme Reels'i (Instagram "trial reels") uygunluk sınaması (büyüme incelemesi #40; Rıdvan, 12 Kasım 2026: önizlemesi
istendi). Instagram, 1.000+ takipçili hesabın Reels'ini önce yalnız takip etmeyenlere göstermesine izin veriyor; API'de
kap kurulurken trial_params ile (Meta değişiklik kaydı, Aralık 2025). Bu betik hesabın bu ayara izinli olup olmadığını
PAYLAŞIM YAPMADAN sınar: video yüklemeden (upload_type=resumable) bir Reels kabı kurar ve sonucu yazar. media_publish
hiçbir zaman çağrılmaz; yayınlanmayan kap Instagram'da hiçbir yerde görünmez ve 24 saatte kendiliğinden düşer.

Kullanım (iş akışı deneme-reels.yml, yalnız elle): python bot/deneme_reels.py uygunluk
Günlüğe anahtar ve sayı yazılmaz; yalnız kabul / ret ve Instagram'ın hata iletisi.
"""
import json
import os
import sys
import time

import requests

API_HOST = os.environ.get("IG_API_HOST", "https://graph.instagram.com").rstrip("/")
API_SURUM = os.environ.get("IG_API_VERSION", "v23.0")      # bot/main.py ile aynı sürüm
API = f"{API_HOST}/{API_SURUM}"

# MANUAL: Reels takipçilere hiç gösterilmez (ancak uygulamadan elle paylaşılırsa). Günlük 4 sınırına dokunmaması için
# (CLAUDE.md → "Günlük sınır") bot yalnız bunu kullanır; SS_PERFORMANCE iyi giderse takipçilere de açılır.
DENEME_AYARI = {"graduation_strategy": "MANUAL"}


def _istek(yontem, yol, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    r = requests.request(yontem, f"{API}/{yol}", data=params if yontem == "POST" else None,
                         params=params if yontem == "GET" else None, timeout=60)
    try:
        cevap = r.json()
    except ValueError:
        cevap = {"ham": r.text[:300]}
    return r.status_code, cevap


def _hata_metni(cevap):
    h = cevap.get("error", cevap) if isinstance(cevap, dict) else cevap
    if isinstance(h, dict):
        parcalar = [str(h.get(k)) for k in ("message", "error_user_title", "error_user_msg", "code", "error_subcode")
                    if h.get(k) not in (None, "")]
        return " · ".join(parcalar)
    return str(h)[:300]


def uygunluk():
    kod, ben = _istek("GET", "me", fields="user_id")
    if kod >= 400 or "user_id" not in ben:
        print(f"::error::Hesap okunamadı ({kod}): {_hata_metni(ben)}")
        return 2
    # Instagram Login API'si yüklemesiz kabı kabul etmiyor ("video_url is required"); kısa boş bir deneme videosunun
    # adresi iş akışı girdisiyle verilir. Video yalnız işlenir, paylaşılmaz.
    kod, kap = _istek("POST", f"{ben['user_id']}/media", media_type="REELS", video_url=os.environ["DENEME_VIDEO_URL"],
                      caption="deneme reels uygunluk sınaması (paylaşılmaz)", trial_params=json.dumps(DENEME_AYARI))
    if kod >= 400 or "id" not in kap:
        print(f"::warning::DENEME REELS'İ KABUL EDİLMEDİ ({kod}): {_hata_metni(kap)}")
        return 1
    print("DENEME REELS'İ KABUL EDİLDİ: trial_params ile Reels kabı kuruldu (video yalnız işlendi, paylaşılmadı; "
          "kap 24 saatte kendiliğinden düşer).")
    for _ in range(18):                     # en çok ~3 dk: Instagram videoyu işledi mi
        kod, durum = _istek("GET", kap["id"], fields="status_code,status")
        if kod >= 400 or durum.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
            break
        time.sleep(10)
    print(f"Kap durumu: {durum.get('status_code')} ({durum.get('status') or _hata_metni(durum)})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "uygunluk":
        print("Kullanım: python bot/deneme_reels.py uygunluk")
        sys.exit(2)
    if not os.environ.get("IG_TOKEN") or not os.environ.get("DENEME_VIDEO_URL"):
        print("::error::IG_TOKEN ya da DENEME_VIDEO_URL tanımlı değil.")
        sys.exit(2)
    sys.exit(uygunluk())
