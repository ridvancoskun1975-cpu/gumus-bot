"""Sitede ayrıntılı pazar analizi sayfası (gunlukgumus.com/pazar/).

Rıdvan, 16 Kasım 2026 15:50: "Web sitesine girenler son pazarın yorumunu daha detaylı bir şekilde görmelerini
istiyorum". Instagram'daki kaydırmalı yorumun tamamı (iki vade, haftanın gelişmeleri) ile görselde yer almayan
ayrıntılar: dönem rakamları (gram, ons, dolar/TL, parite, en yüksek/en düşük), hareketin onstan mı kurdan mı
geldiği (kuralla hesaplanır, modele sorulmaz), haber kaynaklarının bağlantıları, nasıl hazırlandığı ve SPK uyarısı.

Girdi pazar yorumunun kaydıdır (main.py → yorum çalıştırmasının meta.json'u: yorum, haberler, istatistik,
gelismeler, son_veri, aciklama). Yeni bir model isteği yok.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as bot  # noqa: E402
import yorum  # noqa: E402

GUC_DOLU = {"zayıf": 1, "orta": 2, "belirgin": 3}


def _yuzde(x, basamak=1):
    """{"isaret", "metin", "yon"}: ▲ %1,7 gibi."""
    if x is None:
        return None
    yon = "dusus" if x < 0 else "artis"
    return {"yon": yon, "isaret": "▼" if x < 0 else "▲", "metin": "%" + bot.tr_sayi(abs(x), basamak)}


def _tarih(iso):
    g = date.fromisoformat(iso)
    return f"{g.day} {bot.AYLAR[g.month - 1]} {g.year}"


def _kisa(iso):
    g = date.fromisoformat(iso)
    return f"{g.day} {bot.AYLAR[g.month - 1]}" + (f" {g.year}" if g.year != date.today().year else "")


def hareket_kaynagi(ist):
    """Gram fiyattaki değişimin onstan mı kurdan mı geldiği; yalnız rakamlardan, kuralla (gram ≈ ons × kur)."""
    ons, kur, gram = ist.get("ons"), ist.get("dolar"), ist.get("gram")
    if ons is None or kur is None or gram is None:
        return None
    o, k = _yuzde(ons), _yuzde(kur)
    yon_gram = "düştü" if gram < 0 else "yükseldi"
    yon_ons = "düştü" if ons < 0 else "yükseldi"
    yon_kur = "geriledi" if kur < 0 else "arttı"
    if abs(ons) >= 2 * abs(kur):
        pay = "onstan"
    elif abs(kur) >= 2 * abs(ons):
        pay = "dolar/TL kurundan"
    else:
        pay = "ons ve kurdan birlikte"
    ayni = (ons < 0) == (kur < 0)
    ek = "" if ayni or pay != "onstan" else (" Kurdaki artış düşüşün bir kısmını dengeledi." if kur > 0
                                               else " Kurdaki düşüş yükselişin bir kısmını sınırladı.")
    if not ayni and pay == "dolar/TL kurundan":
        ek = " Onstaki hareket bir kısmını dengeledi."
    cumle = (f"Ons gümüş (dolar) {o['metin']} {yon_ons}, dolar/TL {k['metin']} {yon_kur}; gram fiyat "
             f"{_yuzde(gram)['metin']} {yon_gram}. Değişimin büyük kısmı {pay} geldi.{ek}")
    # Çubuklar: en büyük mutlak değişim tam boy
    olcek = max(abs(ons), abs(kur), abs(gram), 0.01)
    cubuk = [{"ad": ad, "deg": _yuzde(x), "oran": round(abs(x) / olcek * 100, 1)}
             for ad, x in (("Gram (₺)", gram), ("Ons ($)", ons), ("Dolar/TL", kur))]
    return {"cumle": cumle, "cubuk": cubuk}


def _haftalik(aciklama):
    """Açıklamanın ikinci satırından gram ve haftalık değişim: "Gram gümüş: 79,11 ₺ (haftalık ▼ %5,54) · 13 Kasım Cuma kapanışı"."""
    m = re.search(r"Gram gümüş: ([\d.,]+) ₺ \(haftalık ([▲▼]) (%[\d,]+)\) · (.+)", aciklama or "")
    if not m:
        return None
    return {"gram": m.group(1), "deg": {"isaret": m.group(2), "metin": m.group(3),
                                        "yon": "dusus" if m.group(2) == "▼" else "artis"},
            "veri_ani": m.group(4).strip()}


def veri(meta, instagram=None):
    """Şablon (templates/pazar.html) için sayfa verisi."""
    yz, ist = meta["yorum"], meta.get("istatistik") or {}
    gel = meta.get("gelismeler") or {}
    kaynaklar = gel.get("kaynaklar") or []
    alan_url = {}
    for k in kaynaklar:
        alan_url.setdefault(k.get("alan"), k.get("url"))
    bitis = (meta.get("son_veri") or {}).get("tarih")
    vadeler = []
    for v in yorum.VADELER:
        a = v["anahtar"]
        y, s = yz[a], ist.get(a) or {}
        vadeler.append({
            "ad": v["ad"], "ufuk": v["ufuk"], "anahtar": a,
            "yon": y["yon"], "yon_sinif": "dusus" if y["yon"] == "düşüş" else "artis",
            "ok": "▼" if y["yon"] == "düşüş" else "▲",
            "guc": yorum.GUC_ADI[y["guc"]], "guc_dolu": GUC_DOLU[y["guc"]],
            "ozet": y["ozet"], "durum": y["durum"], "seyir": y["seyir"],
            "izlenecek": [x.strip() for x in y["izlenecek"].split(",") if x.strip()],
            "degisim": (y.get("degisim") or "").strip(),
            "donem": s.get("etiket"),
            "aralik_tarih": (f"{_kisa(s['baslangic'])} – {_kisa(bitis)}" if s.get("baslangic") and bitis else None),
            "veri_yeterli": s.get("veri_yeterli", True),
            "rakamlar": [r for r in (
                {"ad": "Gram gümüş (₺)", "deg": _yuzde(s.get("gram"))},
                {"ad": "Ons gümüş ($)", "deg": _yuzde(s.get("ons"))},
                {"ad": "Dolar/TL", "deg": _yuzde(s.get("dolar"))},
                {"ad": "Altın/gümüş paritesi", "deg": _yuzde(s.get("parite"))},
            ) if r["deg"]],
            "parite": _yuzde(s.get("parite")),
            "aralik": (f"{bot.tr_sayi(s['gram_en_dusuk'])} – {bot.tr_sayi(s['gram_en_yuksek'])} ₺"
                       if s.get("gram_en_dusuk") and s.get("gram_en_yuksek") else None),
            "hareket": hareket_kaynagi(s),
        })
    haberler = [{**h, "baslik": h.get("baslik") or yorum.HABER_KONU_BASLIK.get(h["konu"], h["konu"].upper()),
                 "url": alan_url.get(h.get("kaynak"))} for h in (meta.get("haberler") or [])]
    son = meta.get("son_veri") or {}
    hafta = _haftalik(meta.get("aciklama"))
    tarih_iso = None
    m = re.search(r"yorum-(\d{4})(\d{2})(\d{2})-", " ".join(meta.get("dosyalar") or []))
    if m:
        tarih_iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return {
        "tarih": _tarih(tarih_iso) if tarih_iso else None,
        "veri_ani": hafta["veri_ani"] if hafta else None,
        "gram": hafta["gram"] if hafta else (bot.tr_sayi(son["gram"]) if son.get("gram") else None),
        "gram_hafta": hafta["deg"] if hafta else None,
        "ons": bot.tr_sayi(son["gumus"]) if son.get("gumus") else None,
        "dolar": bot.tr_sayi(son["dolar"], 4) if son.get("dolar") else None,
        "parite": bot.tr_sayi(son["altin"] / son["gumus"], 1) if son.get("altin") and son.get("gumus") else None,
        "vadeler": vadeler,
        "haberler": haberler,
        "kaynaklar": [{"alan": k.get("alan"), "baslik": k.get("baslik"), "url": k.get("url")} for k in kaynaklar
                      if k.get("url", "").startswith(("https://", "http://"))],
        # Instagram açıklamasındaki "aşağıdaki fiyat ve kur verileri" sitede yukarıda duruyor
        "nasil": yorum._nasil_hazirlandi(gel.get("metin")).replace("Nasıl hazırlandı: ", "")
                 .replace("aşağıdaki fiyat ve kur verileri", "bu sayfadaki fiyat ve kur verileri"),
        "uyari": yorum.UYARI,
        "yz_notu": yorum.YZ_NOTU,
        "secim_notu": yorum.SECIM_NOTU if gel.get("oy_gunu") else None,
        "instagram": instagram,
    }
