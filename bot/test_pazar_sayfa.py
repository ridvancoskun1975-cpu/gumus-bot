# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Ayrıntılı pazar sayfası sınamaları (bot/pazar_sayfa.py, bot/yorum.py → uzun_denetle, bot/sayfa.py bağlantısı).

Ağa çıkmaz, Claude API çağırmaz. Çalıştır: python bot/test_pazar_sayfa.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pazar_sayfa as ps  # noqa: E402
import sayfa  # noqa: E402
import yorum  # noqa: E402

HATA = []
SAY = [0]


def esit(ad, bulunan, beklenen):
    SAY[0] += 1
    if bulunan != beklenen:
        HATA.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    SAY[0] += 1
    if not kosul:
        HATA.append(ad)


def ornek_meta(yeni=True):
    ist = {"kisa": {"etiket": "Son 4 hafta", "baslangic": "2026-10-16", "gram": -13.1, "ons": -14.5, "dolar": 1.7,
                    "parite": 9.0, "gram_en_dusuk": 79.07, "gram_en_yuksek": 92.22, "veri_yeterli": True},
           "orta": {"etiket": "Son 3 ay", "baslangic": "2026-08-14", "gram": -20.5, "ons": -24.5, "dolar": 5.2,
                    "parite": 17.2, "gram_en_dusuk": 79.07, "gram_en_yuksek": 107.18, "veri_yeterli": True}}
    yz = {a: {"yon": "düşüş", "guc": g, "ozet": "Ons kaynaklı düşüş", "durum": "Ons geriledi.", "seyir": "Sürebilir.",
              "izlenecek": "Fed faiz yolu, sanayi talebi, dolar", "degisim": ""} for a, g in (("kisa", "orta"), ("orta", "belirgin"))}
    meta = {"tur": "yorum", "dosyalar": ["yorum-20261115-1003-1.jpg"],
            "aciklama": "Gümüş · Pazar analizi\nGram gümüş: 79,11 ₺ (haftalık ▼ %5,54) · 13 Kasım Cuma kapanışı\n…",
            "yorum": yz, "istatistik": ist,
            "haberler": [{"konu": "Siyaset", "metin": "ABD yönetimi açıklama yaptı.", "kaynak": "kitco.com"}],
            "gelismeler": {"metin": "1. Gümüş … Fed …", "kaynaklar": [
                {"alan": "kitco.com", "baslik": "Silver news", "url": "https://www.kitco.com/x"},
                {"alan": "kotu", "baslik": "x", "url": "javascript:alert(1)"}]},
            "son_veri": {"tarih": "2026-11-13", "gram": 79.11, "gumus": 48.85, "altin": 4070.0, "dolar": 42.33}}
    if yeni:
        meta["sayfa"] = {"tarih": "2026-11-15", "veri_ani": "13 Kasım Cuma kapanışı", "gram": "79,11",
                         "gram_deg": {"yon": "dusus", "yuzde": -5.54, "metin": "%5,54", "isaret": "▼"},
                         "onceki": {"kisa": {"yon": "yükseliş", "guc": "zayıf", "tarih_metni": "8 Kasım"}}}
    return meta


def main():
    # kayıt: yeni ve eski meta aynı tarihi ve rakamları verir
    for yeni in (True, False):
        k = ps.kayit_kur(ornek_meta(yeni))
        esit(f"kayit tarih ({yeni})", k["tarih"], "2026-11-15")
        esit(f"kayit gram ({yeni})", k["gram"], "79,11")
        esit(f"kayit veri anı ({yeni})", k["veri_ani"], "13 Kasım Cuma kapanışı")
        esit(f"kayit haftalık yön ({yeni})", k["gram_deg"]["yon"], "dusus")
    esit("önceki yön", ps.kayit_kur(ornek_meta())["onceki"]["kisa"]["yon"], "yükseliş")
    try:
        ps.kayit_kur({**ornek_meta(False), "dosyalar": [], "aciklama": ""})
        HATA.append("tarihsiz kayıt hata vermedi")
    except ValueError:
        SAY[0] += 1

    # hareketin kaynağı (kuralla)
    h = ps.hareket_kaynagi({"gram": -13.1, "ons": -14.5, "dolar": 1.7})
    dogru("ons kaynaklı", "büyük kısmı onstan" in h["cumle"] and "dengeledi" in h["cumle"])
    esit("en büyük çubuk tam boy", max(c["oran"] for c in h["cubuk"]), 100.0)
    dogru("kur kaynaklı", "kurundan" in ps.hareket_kaynagi({"gram": 6.0, "ons": 1.0, "dolar": 5.0})["cumle"])
    dogru("birlikte", "birlikte" in ps.hareket_kaynagi({"gram": 6.0, "ons": 3.0, "dolar": 3.0})["cumle"])
    esit("eksik veri", ps.hareket_kaynagi({"gram": 1.0}), None)

    # hafta sonu notu: pazar analizi, cuma verisi
    k = ps.kayit_kur(ornek_meta())
    dogru("hafta sonu notu", "13 Kasım Cuma" in ps.hafta_sonu_notu(k) and "15 Kasım Pazar" in ps.hafta_sonu_notu(k))
    esit("aynı gün notu yok", ps.hafta_sonu_notu({**k, "son_veri": {"tarih": "2026-11-15"}}), None)

    # sayfa verisi: güvensiz bağlantı atılır, haber kaynağına bağlantı, GÜNDEM başlığı
    p = ps.veri(k)
    esit("güvenli kaynaklar", [x["url"] for x in p["kaynaklar"]], ["https://www.kitco.com/x"])
    esit("haber bağlantısı", p["haberler"][0]["url"], "https://www.kitco.com/x")
    esit("gündem başlığı", p["haberler"][0]["baslik"], "GÜNDEM")
    dogru("nasıl hazırlandı sitede", "bu sayfadaki" in p["nasil"] or "aşağıdaki" not in p["nasil"])
    esit("izlenecek listesi", p["vadeler"][0]["izlenecek"], ["Fed faiz yolu", "sanayi talebi", "dolar"])

    # ayrıntılı açıklama denetimi
    iyi = {a: {"gerekce": "Onstaki belirgin gerileme ve güçlenen dolar gram fiyatı baskılıyor olabilir.",
               "donus": "Sanayi talebi toparlanırsa görünüm değişebilir.",
               "izleme": "Fed faiz yolu ons fiyatını, dolar kuru gram fiyatı etkileyebilir."} for a in ("kisa", "orta")}
    esit("iyi açıklama", yorum.uzun_denetle(iyi, {"metin": "Fed faiz kararı"}), [])
    dogru("rakam yasak", any("rakam" in x for x in yorum.uzun_denetle(
        {**iyi, "kisa": {**iyi["kisa"], "gerekce": "Ons yüzde 5 düştü, 2026'da"}}, {"metin": "Fed"})))
    dogru("al/sat yasak", any("al/sat" in x for x in yorum.uzun_denetle(
        {**iyi, "kisa": {**iyi["kisa"], "donus": "Şimdi al ve tut."}}, {"metin": "Fed"})))
    dogru("kişi adı yasak", any("kişi ya da parti" in x for x in yorum.uzun_denetle(
        {**iyi, "orta": {**iyi["orta"], "izleme": "Powell açıklaması önemli olabilir."}}, {"metin": "Fed"})))
    dogru("özette olmayan kurum", any("haber özetinde geçmiyor" in x for x in yorum.uzun_denetle(iyi, {"metin": "sanayi"})))
    dogru("uzun vade yok", any("uzun vade" in x for x in yorum.uzun_denetle(
        {**iyi, "orta": {**iyi["orta"], "donus": "Uzun vadede görünüm değişebilir."}}, {"metin": "Fed"})))
    dogru("boş alan", any("boş" in x for x in yorum.uzun_denetle({"kisa": iyi["kisa"]}, {"metin": "Fed"})))
    sema = yorum.uzun_sema()
    esit("şema vadeleri", sorted(sema["required"]), ["kisa", "orta"])

    # site: pazar/ ve tarihli sayfa, düğme siteye, site haritası, ayrıntı ve arşiv
    kayitlar = {"2026-11-15": {**k, "uzun": iyi}, "2026-11-08": ps.kayit_kur(
        {**ornek_meta(), "sayfa": {**ornek_meta()["sayfa"], "tarih": "2026-11-08"}})}
    kayitlar = json.loads(json.dumps(kayitlar, default=str))
    with tempfile.TemporaryDirectory() as d:
        cikti = Path(d)
        v = sayfa.uret(cikti, sayfa.ornek_gecmis(), pazar={"url": "https://www.instagram.com/p/X/", "tarih": "15 Kasım"},
                       pazar_kayitlar=kayitlar)
        esit("düğme siteye", v["tanitim"]["pazar"]["url"], sayfa.site_adresi() + "pazar/")
        son = (cikti / "pazar" / "index.html").read_text(encoding="utf-8")
        eski = (cikti / "pazar" / "2026-11-08" / "index.html").read_text(encoding="utf-8")
        dogru("son sayfa var", "Pazar analizi · 15 Kasım 2026" in son)
        dogru("ayrıntı son sayfada", "Neden bu yön" in son and "Onstaki belirgin gerileme" in son)
        dogru("ayrıntı yoksa bölüm yok", "Neden bu yön" not in eski)
        dogru("instagram bağlantısı son sayfada", "https://www.instagram.com/p/X/" in son)
        dogru("eski sayfada instagram gönderisi yok", "https://www.instagram.com/p/X/" not in eski)
        dogru("eski sayfa uyarısı", "geçmiş bir haftanın analizidir" in eski and "geçmiş bir haftanın" not in son)
        dogru("arşiv listesi", "Geçmiş analizler" in son and "8 Kasım 2026" in son)
        dogru("hafta sonu notu sayfada", "hafta sonu işlem görmediği" in son)
        dogru("önceki yön yazılı değil (değişim yok)", "8 Kasım yorumunda" not in son)
        dogru("SPK uyarısı", "yatırım danışmanlığı kapsamında değildir" in son)
        dogru("kendine giden düğme yok", "Son pazar analizi" not in son)
        dogru("model adı yok", "claude" not in son.lower() and "anthropic" not in son.lower())
        dogru("canonical", f'href="{sayfa.site_adresi()}pazar/2026-11-08/"' in eski)
        harita = (cikti / "sitemap.xml").read_text(encoding="utf-8")
        dogru("site haritası", "pazar/</loc>" in harita and "pazar/2026-11-08/</loc>" in harita)
        ana = (cikti / "index.html").read_text(encoding="utf-8")
        dogru("ana sayfa düğmesi", f'href="{sayfa.site_adresi()}pazar/">Son pazar analizi' in ana)
        # kayıt yoksa eskisi gibi Instagram
        v2 = sayfa.uret(Path(d) / "b", sayfa.ornek_gecmis(), pazar={"url": "https://www.instagram.com/p/X/",
                                                                      "tarih": "15 Kasım"}) if (Path(d) / "b").mkdir() is None else None
        esit("kayıtsız düğme Instagram", v2["tanitim"]["pazar"]["url"], "https://www.instagram.com/p/X/")
        dogru("kayıtsız pazar sayfası yok", not (Path(d) / "b" / "pazar").exists())
        # bozuk kayıt: site yine üretilir, düğme Instagram'a döner
        v3 = sayfa.uret(Path(d) / "c", sayfa.ornek_gecmis(), pazar={"url": "https://www.instagram.com/p/X/", "tarih": "15 Kasım"},
                        pazar_kayitlar={"2026-11-15": {"tarih": "2026-11-15"}}) if (Path(d) / "c").mkdir() is None else None
        esit("bozuk kayıtta düğme Instagram", v3["tanitim"]["pazar"]["url"], "https://www.instagram.com/p/X/")

    if HATA:
        print("test_pazar_sayfa: HATA\n- " + "\n- ".join(HATA))
        sys.exit(1)
    print(f"test_pazar_sayfa: hepsi geçti ({SAY[0]})")


if __name__ == "__main__":
    main()
