"""Günlük fiyat kayıtlarının (veri/gecmis.json) yedeği: sana özel gumus-kayit deposunda yedek/gecmis.json.

Rıdvan, 18 Ekim 2026 ("8 önerin uygun"): kayıtlar yalnızca GitHub Actions önbelleğinde duruyordu; önbellek
silinirse geçmiş fiyatlar, haftalık ve aylık özetler, pazar yorumunun kendi kayıtları sıfırlanırdı.

Kullanım (iş akışı çağırır):
  python bot/yedek.py birlestir   → yedeği indirir, yerel dosyada olmayan günleri ekler (yerel kayıt üstün).
                                    Önbellek boş geldiyse kayıtların tamamı yedekten gelir.
  python bot/yedek.py gonder      → yerel dosyayı yedekle birleştirip yedeğe yazar (değişiklik yoksa yazmaz).
                                    Yedekte olup yerelde olmayan gün silinmez: yedek hiçbir zaman küçülmez.

Günlüğe fiyat yazılmaz, yalnızca kayıt sayısı ve tarih aralığı. Her hata yalnızca uyarıdır; paylaşım ve bilgi
sayfası hiçbir zaman bu yüzden durmaz. Gerekenler: KAYIT_PAT (gumus-kayit için Contents: Read and write).
"""
import base64
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parent.parent
YEREL = KOK / "veri" / "gecmis.json"
DEPO = (os.environ.get("KAYIT_DEPO", "").strip()
        or os.environ.get("GITHUB_REPOSITORY_OWNER", "ridvancoskun1975-cpu") + "/gumus-kayit")
HEDEF = "yedek/gecmis.json"
SAKLAMA_GUN = 800   # bot/main.py → gecmis_yaz ile aynı (kayıtlar ~2 yıl tutulur)


class YedekHatasi(Exception):
    pass


def _github(yontem, yol, **kw):
    anahtar = os.environ.get("KAYIT_PAT", "").strip()
    if not anahtar:
        raise YedekHatasi("KAYIT_PAT tanımlı değil")
    try:
        return requests.request(yontem, f"https://api.github.com/repos/{DEPO}{yol}", timeout=30,
                                headers={"Authorization": f"Bearer {anahtar}",
                                         "Accept": "application/vnd.github+json",
                                         "X-GitHub-Api-Version": "2022-11-28"}, **kw)
    except requests.RequestException as e:
        raise YedekHatasi(f"GitHub'a ulaşılamadı ({type(e).__name__})")


def yedegi_al():
    """(kayıtlar, sha). Yedek yoksa ({}, None)."""
    r = _github("GET", f"/contents/{HEDEF}")
    if r.status_code == 404:
        return {}, None
    if r.status_code >= 400:
        raise YedekHatasi(f"yedek okunamadı ({r.status_code})")
    veri = r.json()
    try:
        if veri.get("encoding") == "base64" and veri.get("content"):
            metin = base64.b64decode(veri["content"]).decode("utf-8")
        else:   # 1 MB üstü dosyada içerik gelmez; ham içerik ayrıca istenir
            try:
                ham = requests.get(veri["download_url"], timeout=30,
                                   headers={"Authorization": f"Bearer {os.environ['KAYIT_PAT'].strip()}"})
            except requests.RequestException as e:
                raise YedekHatasi(f"yedek okunamadı ({type(e).__name__})")
            if ham.status_code >= 400:
                raise YedekHatasi(f"yedek okunamadı ({ham.status_code})")
            metin = ham.text
        kayitlar = json.loads(metin)
    except (ValueError, KeyError) as e:
        raise YedekHatasi(f"yedek okunamadı ({type(e).__name__})")
    if not isinstance(kayitlar, dict):
        raise YedekHatasi("yedek dosyası beklenen biçimde değil")
    return kayitlar, veri.get("sha")


def yereli_oku():
    try:
        kayitlar = json.loads(YEREL.read_text(encoding="utf-8"))
        return kayitlar if isinstance(kayitlar, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def birlesik(yerel, yedek):
    """Yedekteki günler + yerel günler (aynı günde yerel üstün), ~2 yıldan eskiler atılır, tarihe göre sıralı."""
    hepsi = {**yedek, **yerel}
    if not hepsi:
        return {}
    sinir = (date.fromisoformat(max(hepsi)) - timedelta(days=SAKLAMA_GUN)).isoformat()
    return {k: hepsi[k] for k in sorted(hepsi) if k >= sinir}


def _ozet(kayitlar):
    return f"{len(kayitlar)} gün, {min(kayitlar)} – {max(kayitlar)}" if kayitlar else "0 gün"


def birlestir():
    yerel = yereli_oku()
    yedek, _ = yedegi_al()
    sonuc = birlesik(yerel, yedek)
    eklenen = len(set(sonuc) - set(yerel))
    if eklenen:
        YEREL.parent.mkdir(parents=True, exist_ok=True)
        YEREL.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
        nerede = "önbellek boştu, kayıtlar yedekten geldi" if not yerel else "önbellekte eksik günler yedekten tamamlandı"
        print(f"::warning::Günlük kayıtlar: {nerede} ({eklenen} gün eklendi; şimdi {_ozet(sonuc)}).")
    else:
        print(f"Günlük kayıtlar yedekle uyumlu ({_ozet(yerel)}; yedek {_ozet(yedek)}).")


def gonder():
    yerel = yereli_oku()
    if not yerel:
        print("Yedeklenecek kayıt yok; yedeğe dokunulmadı.")
        return
    for _ in range(2):   # arada başka bir yazım olursa bir kez yeniden dener
        yedek, sha = yedegi_al()
        sonuc = birlesik(yerel, yedek)
        if sonuc == yedek:
            print(f"Yedek güncel ({_ozet(yedek)}).")
            return
        metin = json.dumps(sonuc, ensure_ascii=False, indent=1)
        govde = {"message": f"Yedek: günlük kayıtlar ({max(sonuc)})",
                 "content": base64.b64encode(metin.encode("utf-8")).decode()}
        if sha:
            govde["sha"] = sha
        r = _github("PUT", f"/contents/{HEDEF}", json=govde)
        if r.status_code in (409, 422):
            continue
        if r.status_code >= 400:
            raise YedekHatasi(f"yedek yazılamadı ({r.status_code})")
        print(f"Günlük kayıtlar yedeklendi: {DEPO}/{HEDEF} ({_ozet(sonuc)}).")
        return
    raise YedekHatasi("yedek yazılamadı (aynı anda başka bir yazım)")


def main():
    komut = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if komut == "birlestir":
            birlestir()
        elif komut == "gonder":
            gonder()
        else:
            print(__doc__)
            sys.exit(2)
    except YedekHatasi as e:   # yalnızca uyarı: paylaşım ve sayfa bu yüzden durmaz
        print(f"::warning::Günlük kayıt yedeği ({komut}): {e}")


if __name__ == "__main__":
    main()
