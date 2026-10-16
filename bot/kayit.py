"""Takipçi kaydı: her paylaşımda takipçi sayısını sana özel gumus-kayit deposuna yazar.

Kullanım (iş akışı çağırır):
  python bot/kayit.py --tur reels|post|hafta|ay|bilgi|kisa|yorum

Bot deposu herkese açık ve iş akışı günlüklerini herkes okuyabilir. Bu yüzden bu betik
takipçi sayısını hiçbir zaman günlüğe yazmaz; sayılar yalnızca özel depodaki takipci.md
dosyasında durur. Kayıt başarısız olursa yalnızca uyarı verir, paylaşımı hiçbir zaman durdurmaz.

Gerekenler (GitHub Secrets):
  IG_TOKEN   - Instagram erişim anahtarı (mevcut anahtar yeterli: instagram_business_basic)
  KAYIT_PAT  - yalnızca gumus-kayit deposuna "Contents: Read and write" izni olan GitHub anahtarı
İsteğe bağlı: KAYIT_DEPO (varsayılan <sahip>/gumus-kayit), HESAP_ADI, DENEME=true.
"""
import argparse
import base64
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TR_SAAT = ZoneInfo("Europe/Istanbul")
IG_API = (os.environ.get("IG_API_HOST", "https://graph.instagram.com").rstrip("/")
          + "/" + os.environ.get("IG_API_VERSION", "v23.0"))
DEPO = (os.environ.get("KAYIT_DEPO", "").strip()
        or os.environ.get("GITHUB_REPOSITORY_OWNER", "ridvancoskun1975-cpu") + "/gumus-kayit")
DOSYA = "takipci.md"
ETIKET = {"reels": "Reels", "post": "Günlük özet", "hafta": "Haftalık özet", "ay": "Aylık özet",
          "bilgi": "Rehber", "kisa": "Rehber Reels", "yorum": "Pazar yorumu",
          "hikaye": "Rehber hikâyesi", "kart": "Haftalık kart"}
SATIR = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\d{2}:\d{2})\s*\|\s*([^|]*?)\s*\|\s*(\d+)\s*\|")


class KayitHatasi(Exception):
    pass


# ---------------------------------------------------------------- veri

def hesap_bilgisi():
    """Takipçi sayısı ve kullanıcı adı. Hata iletisinde sayı yer almaz."""
    try:
        r = requests.get(f"{IG_API}/me", timeout=30,
                         params={"fields": "username,followers_count",
                                 "access_token": os.environ["IG_TOKEN"]})
        veri = r.json()
    except (requests.RequestException, ValueError) as e:
        raise KayitHatasi(f"Instagram'a ulaşılamadı ({type(e).__name__})")
    if r.status_code >= 400 or "followers_count" not in veri:
        ileti = (veri.get("error") or {}).get("message", "beklenmedik yanıt")
        raise KayitHatasi(f"Instagram takipçi sayısını vermedi ({r.status_code}: {ileti})")
    return int(veri["followers_count"]), veri.get("username", "")


def _github(yontem, yol, **kw):
    try:
        return requests.request(
            yontem, f"https://api.github.com/repos/{DEPO}{yol}", timeout=30,
            headers={"Authorization": f"Bearer {os.environ['KAYIT_PAT']}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"}, **kw)
    except requests.RequestException as e:
        raise KayitHatasi(f"GitHub'a ulaşılamadı ({type(e).__name__})")


def dosyayi_al():
    """(metin, sha). Dosya yoksa ("", None)."""
    r = _github("GET", f"/contents/{DOSYA}")
    if r.status_code == 404:
        if _github("GET", "").status_code == 404:
            raise KayitHatasi(f"{DEPO} deposuna ulaşılamadı: depo yok ya da KAYIT_PAT bu depoya izinli değil")
        return "", None
    if r.status_code in (401, 403):
        raise KayitHatasi(f"KAYIT_PAT {DEPO} deposunu okuyamadı ({r.status_code}); anahtarın izinlerini kontrol et")
    if r.status_code >= 400:
        raise KayitHatasi(f"GitHub dosyayı vermedi ({r.status_code})")
    j = r.json()
    return base64.b64decode(j["content"]).decode("utf-8"), j["sha"]


def dosyayi_yaz(metin, sha, mesaj):
    govde = {"message": mesaj, "content": base64.b64encode(metin.encode("utf-8")).decode()}
    if sha:
        govde["sha"] = sha
    r = _github("PUT", f"/contents/{DOSYA}", json=govde)
    if r.status_code in (401, 403):
        raise KayitHatasi(f"KAYIT_PAT {DEPO} deposuna yazamadı ({r.status_code}); "
                          "anahtarda Contents: Read and write izni olmalı")
    if r.status_code in (409, 422):
        return False   # bu arada başka bir yazım oldu; çağıran yeniden dener
    if r.status_code >= 400:
        raise KayitHatasi(f"GitHub dosyayı kaydetmedi ({r.status_code})")
    return True


# ---------------------------------------------------------------- dosya biçimi

def satirlari_oku(metin):
    """Tablodaki kayıtlar, eskiden yeniye: [(tarih, saat, paylasim, sayi), ...]"""
    satirlar = []
    for line in metin.splitlines():
        m = SATIR.match(line)
        if m:
            satirlar.append((m.group(1), m.group(2), m.group(3), int(m.group(4))))
    satirlar.sort(key=lambda s: (s[0], s[1]))
    return satirlar


def _isaretli(n):
    return f"+{n}" if n > 0 else str(n)


def _donem_farki(satirlar, gun):
    """Son kayıt ile 'gun' gün önceki (ya da daha eski) son kayıt arasındaki fark."""
    son = satirlar[-1]
    sinir = (date.fromisoformat(son[0]) - timedelta(days=gun)).isoformat()
    onceki = [s for s in satirlar if s[0] <= sinir]
    if onceki:
        return _isaretli(son[3] - onceki[-1][3])
    ilk = satirlar[0]
    gun_farki = (date.fromisoformat(son[0]) - date.fromisoformat(ilk[0])).days
    return f"{_isaretli(son[3] - ilk[3])} (kayıt başından beri, {gun_farki} gün)"


def dosyayi_olustur(satirlar, hesap):
    son = satirlar[-1]
    tarih_tr = datetime.strptime(son[0], "%Y-%m-%d").strftime("%d.%m.%Y")
    satir_metinleri = []
    for i in range(len(satirlar) - 1, -1, -1):          # yeniden eskiye
        s = satirlar[i]
        fark = _isaretli(s[3] - satirlar[i - 1][3]) if i > 0 else "—"
        satir_metinleri.append(f"| {s[0]} | {s[1]} | {s[2]} | {s[3]} | {fark} |")
    baslik = f"# Takipçi kaydı · {hesap}" if hesap else "# Takipçi kaydı"
    return "\n".join([
        baslik,
        "",
        f"**Son kayıt:** {tarih_tr} {son[1]} · **{son[3]} takipçi**",
        "",
        "| Dönem | Değişim |",
        "|---|---|",
        f"| Son 7 gün | {_donem_farki(satirlar, 7)} |",
        f"| Son 30 gün | {_donem_farki(satirlar, 30)} |",
        "",
        "Bu dosyayı gumus-bot her paylaşımda kendisi günceller (bot/kayit.py); elle değiştirme. "
        "Saatler Türkiye saatidir; deneme çalıştırmaları \"(deneme)\" diye işaretlenir.",
        "",
        "| Tarih | Saat | Paylaşım | Takipçi | Değişim |",
        "|---|---|---|---|---|",
        *satir_metinleri,
        "",
    ])


# ---------------------------------------------------------------- akış

def paylasim_adi(tur, deneme=False, meta_yolu="site/meta.json"):
    """Tablodaki paylaşım adı. Gorilli akşam/haftalık özette hâl eklenir (bot/goril.py → etiket_ekle):
    'Günlük özet · goril: istif'. meta.json yoksa, okunamazsa ya da goril yoksa ad bugünkü gibi kalır."""
    ad = ETIKET.get(tur, tur)
    if tur in ("post", "hafta"):
        try:
            meta = json.loads(Path(meta_yolu).read_text(encoding="utf-8"))
            if meta.get("tur") == tur and meta.get("goril"):
                import goril
                ad = goril.etiket_ekle(ad, meta["goril"])
        except Exception:
            pass
    return ad + (" (deneme)" if deneme else "")


def kaydet(tur, deneme=False, simdi=None):
    sayi, kullanici = hesap_bilgisi()
    hesap = os.environ.get("HESAP_ADI", "").strip() or kullanici
    hesap = ("@" + hesap.lstrip("@")) if hesap else ""
    simdi = simdi or datetime.now(TR_SAAT)
    paylasim = paylasim_adi(tur, deneme)
    yeni = (simdi.strftime("%Y-%m-%d"), simdi.strftime("%H:%M"), paylasim, sayi)
    for _ in range(3):
        metin, sha = dosyayi_al()
        satirlar = satirlari_oku(metin) + [yeni]
        satirlar.sort(key=lambda s: (s[0], s[1]))
        if dosyayi_yaz(dosyayi_olustur(satirlar, hesap), sha,
                       f"Takipçi kaydı: {yeni[0]} {yeni[1]} ({paylasim})"):
            return
    raise KayitHatasi("dosya üç denemede de kaydedilemedi (aynı anda başka yazım)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", required=True)
    a = ap.parse_args()
    if not os.environ.get("KAYIT_PAT"):
        print("::notice::KAYIT_PAT tanımlı değil; takipçi kaydı atlandı.")
        return
    if not os.environ.get("IG_TOKEN"):
        print("::warning::IG_TOKEN tanımlı değil; takipçi kaydı atlandı.")
        return
    deneme = os.environ.get("DENEME", "").lower() == "true"
    try:
        kaydet(a.tur, deneme)
    except KayitHatasi as e:
        print(f"::warning::Takipçi kaydı yazılamadı: {e}")
        return
    # Sayı bilerek yazdırılmıyor: bu depo ve günlükleri herkese açık.
    print(f"Takipçi kaydı güncellendi: {DEPO}/{DOSYA} (özel depo)")


if __name__ == "__main__":
    main()
