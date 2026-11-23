# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Sitede güncel haftalık ve aylık özet (gunlukgumus.com/ozet/; #50).

Rıdvan, 23 Kasım 2026 12:49: "web sitemizde en güncel haftalık ve aylık özetleri de görmek istiyorum. ama karışık
olmamalı. bir başlık altında olabilir."; seçim: menüde ayrı "Özetler" sekmesi, sayfada "Bu hafta" ve "Bu ay" iki kart,
her kartta Instagram'da paylaşılan görsel ve dört ana rakam (gram ve değişimi, dönemin en yükseği/en düşüğü,
altın/gümüş paritesi, dolar/TL).

Yalnız en son haftalık ve en son aylık özet tutulur (arşiv yok). Kayıtlar sana özel gumus-kayit deposunda:
ozet/hafta.json + ozet/hafta.png, ozet/ay.json + ozet/ay.png. Akış (paylas.yml, sayfa.yml, vitrin.yml):
  1. Cumartesi haftalık ya da aylık özet üretilince:  python bot/ozet_sayfa.py kaydet --cikti site
     Rakamlar meta.json'daki fiyatlardan aynı işlevlerle yeniden hesaplanır (görseldekiyle aynı), görsel paylaşılan
     PNG'dir. Kayıt yerel veri/ozet/'e ve (deneme değilse) özel depoya yazılır; aynı işteki site yeni özeti içerir.
  2. Siteyi kuran her iş önce:                        python bot/ozet_sayfa.py indir
Her hata yalnızca uyarıdır: paylaşım ve site bu yüzden durmaz (kayıt yoksa "Özetler" sekmesi görünmez).
"""
import argparse
import base64
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as bot  # noqa: E402

YEREL = bot.KOK / "veri" / "ozet"
UZAK = "ozet"
SAYFA_YOLU = "ozet/"
TURLER = ("hafta", "ay")
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


# ---------------------------------------------------------------- kayıt

def _paylasim_tarihi(dosya):
    """"hafta-20261121-0955.mp4" → "2026-11-21"."""
    m = re.search(r"-(\d{4})(\d{2})(\d{2})-\d{4}\.", dosya or "")
    if not m:
        raise ValueError(f"paylaşım tarihi dosya adından okunamadı: {dosya}")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def kayit_kur(meta):
    """meta.json (bot/main.py → hazirla, tür hafta/ay) → sayfa kaydı. Rakamlar görseldekiyle aynı işlevlerden."""
    tur = meta.get("tur")
    if tur not in TURLER:
        raise ValueError(f"özet türü değil: {tur}")
    hazirla = bot.haftalik_veri_hazirla if tur == "hafta" else bot.aylik_veri_hazirla
    v = hazirla(dict(meta["fiyatlar"]), bot.hesap_adi())
    return {
        "surum": 1,
        "tur": tur,
        "paylasim": _paylasim_tarihi(meta.get("dosya")),
        "donem": v["aralik"] if tur == "hafta" else v["ay_adi"],
        "baslik": (meta.get("baslik") or {}).get("metin"),
        "gram": v["gram"], "gram_deg": v["gram_deg"],
        "en_yuksek": v["en_yuksek"], "en_dusuk": v["en_dusuk"],
        "en_yuksek_gun": v.get("en_yuksek_gun"), "en_dusuk_gun": v.get("en_dusuk_gun"),
        "parite": v["parite"], "parite_deg": v["parite_deg"],
        "dolar": v["dolar"], "dolar_deg": v["dolar_deg"],
        "kur_tarihi": v.get("kur_tarihi"),
        "kismi": bool(v.get("kismi")),
        "baz_metin": v.get("baz_metin"),
        "aralik": v.get("aralik"),
        "yil_satiri": v.get("yil_satiri"),
    }


def oku():
    """Yerel kayıtlar {tur: kayıt}; görseli olmayan kayıt da döner ("gorsel" alanı None)."""
    sonuc = {}
    for tur in TURLER:
        try:
            k = json.loads((YEREL / f"{tur}.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            continue
        png = YEREL / f"{tur}.png"
        k["gorsel"] = str(png) if png.exists() and png.stat().st_size > 0 else None
        sonuc[tur] = k
    return sonuc


def _yerele_yaz(tur, kayit, png=None):
    YEREL.mkdir(parents=True, exist_ok=True)
    (YEREL / f"{tur}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if png:
        shutil.copy2(png, YEREL / f"{tur}.png")


def _sha(yol):
    import yedek
    r = yedek._github("GET", f"/contents/{yol}")
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        raise yedek.YedekHatasi(f"{yol} okunamadı ({r.status_code})")
    return r.json().get("sha")


def _uzaga_koy(yol, icerik, mesaj):
    """Özel depoya dosya yazar (varsa üstüne); aradaki yazımda bir kez yeniden dener."""
    import yedek
    for _ in range(2):
        govde = {"message": mesaj, "content": base64.b64encode(icerik).decode()}
        sha = _sha(yol)
        if sha:
            govde["sha"] = sha
        r = yedek._github("PUT", f"/contents/{yol}", json=govde)
        if r.status_code in (409, 422):
            continue
        if r.status_code >= 400:
            raise yedek.YedekHatasi(f"{yol} yazılamadı ({r.status_code})")
        return
    raise yedek.YedekHatasi(f"{yol} yazılamadı (aynı anda başka bir yazım)")


def _uzaktan_al(yol):
    """Ham içerik (bytes); yoksa None."""
    import requests
    import yedek
    anahtar = os.environ.get("KAYIT_PAT", "").strip()
    if not anahtar:
        raise yedek.YedekHatasi("KAYIT_PAT tanımlı değil")
    r = requests.get(f"https://api.github.com/repos/{yedek.DEPO}/contents/{yol}", timeout=30,
                     headers={"Authorization": f"Bearer {anahtar}", "Accept": "application/vnd.github.raw",
                              "X-GitHub-Api-Version": "2022-11-28"})
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        raise yedek.YedekHatasi(f"{yol} okunamadı ({r.status_code})")
    return r.content


def kaydet(cikti, deneme=False):
    cikti = Path(cikti)
    meta = json.loads((cikti / "meta.json").read_text(encoding="utf-8"))
    if meta.get("tur") not in TURLER:
        print("Haftalık ya da aylık özet değil; özet kaydı atlandı.")
        return
    k = kayit_kur(meta)
    png = cikti / re.sub(r"\.mp4$", ".png", meta["dosya"])
    if not png.exists():
        print(f"::warning::Özet sayfası: {png.name} bulunamadı; kayıt görselsiz.")
        png = None
    _yerele_yaz(k["tur"], k, png)
    if deneme:
        print(f"Özet kaydı yalnız yerelde (deneme): {k['tur']} · {k['donem']}.")
        return
    if png:   # önce görsel: json yeni olup görsel eski kalmasın
        _uzaga_koy(f"{UZAK}/{k['tur']}.png", png.read_bytes(), f"Özet görseli: {k['tur']} · {k['donem']}")
    _uzaga_koy(f"{UZAK}/{k['tur']}.json",
               json.dumps(k, ensure_ascii=False, indent=1, default=str).encode("utf-8"),
               f"Özet: {k['tur']} · {k['donem']}")
    print(f"Özet kaydedildi: gumus-kayit/{UZAK}/{k['tur']}.json ({k['donem']}).")


def indir():
    yerel = oku()
    sayi = 0
    for tur in TURLER:
        ham = _uzaktan_al(f"{UZAK}/{tur}.json")
        if ham is None:
            continue
        k = json.loads(ham.decode("utf-8"))
        # Aynı işte yeni üretilmiş (deneme ya da yazılamamış) kayıt daha yeniyse korunur
        if tur in yerel and yerel[tur].get("paylasim", "") > k.get("paylasim", ""):
            continue
        png = _uzaktan_al(f"{UZAK}/{tur}.png")
        YEREL.mkdir(parents=True, exist_ok=True)
        if png:
            (YEREL / f"{tur}.png").write_bytes(png)
        else:
            (YEREL / f"{tur}.png").unlink(missing_ok=True)
        _yerele_yaz(tur, k)
        sayi += 1
    if not sayi and not yerel:
        print("Özet kaydı henüz yok; sitede \"Özetler\" sekmesi görünmez.")
        return
    print(f"Özetler indirildi: {', '.join(sorted(oku()))}.")


# ---------------------------------------------------------------- sayfa

# Bulunma eki: "21 Kasım'da", "1 Aralık'ta" (figcaption: "Instagram'da … paylaşılan görsel")
EK = {"Ocak": "'ta", "Şubat": "'ta", "Mart": "'ta", "Nisan": "'da", "Mayıs": "'ta", "Haziran": "'da", "Temmuz": "'da",
      "Ağustos": "'ta", "Eylül": "'de", "Ekim": "'de", "Kasım": "'da", "Aralık": "'ta"}


def _uzun_tarih(iso):
    """"2026-11-21" → "21 Kasım'da"."""
    g = date.fromisoformat(iso)
    ay = AYLAR[g.month - 1]
    return f"{g.day} {ay}{EK[ay]}"


def kart(k):
    """Şablon için tek özet kartı."""
    hafta = k["tur"] == "hafta"
    if hafta:
        uc = {"ad": "Haftanın en yükseği / en düşüğü", "deger": f"{k['en_yuksek']} / {k['en_dusuk']} ₺", "alt": None}
        not_ = f"Değişimler {k['baz_metin']}dır." if k.get("baz_metin") else None
    else:
        alt = (f"{k['en_yuksek_gun']} · {k['en_dusuk_gun']}" if k.get("en_yuksek_gun") and k.get("en_dusuk_gun") else None)
        uc = {"ad": "Ayın en yükseği / en düşüğü", "deger": f"{k['en_yuksek']} / {k['en_dusuk']} ₺", "alt": alt}
        not_ = "Değişimler önceki ayın son değerine göredir." if not k.get("kismi") else None
    return {
        "tur": k["tur"],
        "etiket": "Bu hafta" if hafta else "Bu ay",
        "donem": k["donem"],
        "baslik": k.get("baslik"),
        "paylasim": _uzun_tarih(k["paylasim"]),
        "gram": k["gram"], "gram_deg": k["gram_deg"],
        "uc": uc,
        "parite": k["parite"], "parite_deg": k["parite_deg"],
        "dolar": k["dolar"], "dolar_deg": k["dolar_deg"],
        "kur_tarihi": k.get("kur_tarihi"),
        "yil_satiri": k.get("yil_satiri") if not hafta else None,
        "not": not_,
        "gorsel": None,
    }


def uret(cikti, env, v, kayitlar):
    """site/ozet/index.html ve görseller. Site haritası için [(adres, son tarih)] döndürür."""
    if not kayitlar:
        return []
    hedef = Path(cikti) / SAYFA_YOLU
    hedef.mkdir(parents=True, exist_ok=True)
    kartlar = {}
    for tur in TURLER:
        k = kayitlar.get(tur)
        if not k:
            continue
        c = kart(k)
        if k.get("gorsel"):
            ad = f"{tur}-{k['paylasim']}.png"   # tarihli ad: tarayıcı önbelleği eski görseli göstermesin
            shutil.copy2(k["gorsel"], hedef / ad)
            c["gorsel"] = ad
        kartlar[tur] = c
    (hedef / "index.html").write_text(
        env.get_template("ozet.html").render(**v, kok="../", adres=SAYFA_YOLU, hafta=kartlar.get("hafta"),
                                             ay=kartlar.get("ay")), encoding="utf-8")
    son = max(k["paylasim"] for k in kayitlar.values())
    return [(v["url"] + SAYFA_YOLU, son)]


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("kaydet")
    a.add_argument("--cikti", default="site")
    alt.add_parser("indir")
    a = ap.parse_args()
    deneme = os.environ.get("DENEME", "").strip().lower() == "true"
    try:
        if a.komut == "kaydet":
            kaydet(a.cikti if os.path.isabs(a.cikti) else bot.KOK / a.cikti, deneme=deneme)
        else:
            indir()
    except Exception as e:   # paylaşım ve site hiçbir zaman bu yüzden durmasın
        print(f"::warning::Özet sayfası ({a.komut}): {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
