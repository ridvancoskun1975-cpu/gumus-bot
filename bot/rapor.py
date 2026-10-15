"""Haftalık Instagram raporu: son haftanın paylaşımlarının istatistiklerini özel gumus-kayit deposuna yazar.

Kullanım (iş akışı çağırır):
  python bot/rapor.py [--bitis YYYY-MM-DD] [--gun 7]

Varsayılan dönem: dünden geriye 7 gün (pazartesi sabahı çalışınca geçen pazartesi–pazar).
Rapor her paylaşımın ulaştığı kişi, görüntülenme, beğeni, yorum, kaydetme ve paylaşma sayılarını,
Reels ile gönderiyi karşılaştırmasını, hesaba ulaşanların ne kadarının takip etmeyenlerden geldiğini
ve günlere göre takipçi değişimini içerir.

Bot deposu ve iş akışı günlükleri herkese açık: bu betik hiçbir sayıyı günlüğe yazmaz. Rakamlar
yalnızca özel depodaki raporlar/<bitiş tarihi>.md dosyasında durur. DENEME=true ise dosya adı
"-deneme" ile biter. Instagram'a haftada ~30 istek yapar (sınır saatte 200); paylaşım saatlerinde
çalıştırılmaz.

Gerekenler (GitHub Secrets):
  IG_TOKEN   - instagram_business_basic + instagram_business_manage_insights izinli anahtar
  KAYIT_PAT  - gumus-kayit deposuna "Contents: Read and write" izni olan GitHub anahtarı
"""
import argparse
import base64
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kayit  # noqa: E402  (takipci.md biçimi ve özel depo adresi tek yerde)

TR_SAAT = ZoneInfo("Europe/Istanbul")
IG_API = kayit.IG_API
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
         "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# Tek tek gönderi istatistikleri. Instagram desteklemediği ölçüyü tüm isteği reddederek bildirir;
# o zaman ölçüler tek tek denenir ve desteklenmeyenler bu çalıştırma boyunca bir daha istenmez.
ORTAK = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions"]
OLCULER = {"REELS": ORTAK + ["ig_reels_avg_watch_time"],
           "FEED": ORTAK + ["follows", "profile_visits"]}
TUR_ADI = {"REELS": "Reels", "FEED": "Gönderi"}
# takipci.md'deki paylaşım adları rapordaki adlara (kayit.ETIKET ile aynı sözcükler)
RAPOR_ADI = {"Reels": "Fiyat Reels'i"}


class RaporHatasi(Exception):
    pass


# ---------------------------------------------------------------- Instagram

class Instagram:
    def __init__(self, token, bekle=0.6):
        self.token = token
        self.bekle = bekle
        self.istek_sayisi = 0
        self.desteklenmeyen = {}          # ürün türü -> {ölçü}
        self.uyarilar = []                # rapora yazılır (sayı içermez)

    def get(self, yol, **params):
        """(veri, hata). Hata metni sayı içermez: yalnızca HTTP ve Meta kodu."""
        if self.istek_sayisi:
            time.sleep(self.bekle)
        self.istek_sayisi += 1
        params["access_token"] = self.token
        url = yol if yol.startswith("http") else f"{IG_API}/{yol.lstrip('/')}"
        try:
            r = requests.get(url, params=None if yol.startswith("http") else params, timeout=30)
            veri = r.json()
        except (requests.RequestException, ValueError) as e:
            return None, f"Instagram'a ulaşılamadı ({type(e).__name__})"
        if r.status_code >= 400 or "error" in veri:
            h = veri.get("error") or {}
            if h.get("code") in (190,):
                raise RaporHatasi("IG_TOKEN geçersiz ya da süresi dolmuş (kod 190)")
            if h.get("code") in (4, 17, 32, 613) or "access blocked" in str(h.get("message", "")).lower():
                raise RaporHatasi(f"Instagram istek sınırı ya da engel (kod {h.get('code')}); rapor sonra denenir")
            return None, f"HTTP {r.status_code}, kod {h.get('code')}"
        return veri, None

    def medyalar(self, bas_utc):
        """bas_utc'den yeni bütün gönderiler (yeniden eskiye)."""
        alanlar = "id,caption,media_type,media_product_type,timestamp,permalink"
        veri, hata = self.get("me/media", fields=alanlar, limit=50)
        if hata:
            raise RaporHatasi(f"Gönderi listesi alınamadı ({hata})")
        sonuc = []
        while True:
            for m in veri.get("data", []):
                t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
                if t < bas_utc:
                    return sonuc
                m["_zaman"] = t.astimezone(TR_SAAT)
                sonuc.append(m)
            sonraki = (veri.get("paging") or {}).get("next")
            if not sonraki or len(sonuc) > 300:
                return sonuc
            veri, hata = self.get(sonraki)
            if hata:
                self.uyarilar.append(f"Gönderi listesinin devamı alınamadı ({hata}); rapor eksik olabilir.")
                return sonuc

    def medya_istatistik(self, medya):
        tur = medya.get("media_product_type") or "FEED"
        olculer = [o for o in OLCULER.get(tur, ORTAK) if o not in self.desteklenmeyen.get(tur, set())]
        veri, hata = self.get(f"{medya['id']}/insights", metric=",".join(olculer))
        if veri is not None:
            return _degerler(veri)
        # Biri desteklenmiyor olabilir: önce temel ölçüyü dene; o da yoksa sorun gönderide, ölçüde değil.
        v, h = self.get(f"{medya['id']}/insights", metric="reach")
        if v is None:
            self.uyarilar.append(f"{_kisa_zaman(medya['_zaman'])} paylaşımının istatistikleri alınamadı ({hata}).")
            return {}
        sonuc = _degerler(v)
        for o in olculer:
            if o == "reach":
                continue
            v, h = self.get(f"{medya['id']}/insights", metric=o)
            if v is None:
                self.desteklenmeyen.setdefault(tur, set()).add(o)   # bir daha istenmez
            else:
                sonuc.update(_degerler(v))
        return sonuc

    def hesap_istatistik(self, bas_tr, bit_tr):
        """Hafta boyunca hesap geneli: ulaşılan kişi (takipçi / takip etmeyen, Reels / gönderi / hikâye),
        görüntülenme, etkileşen hesap, profil bağlantısı tıklaması. Alınamayanlar boş kalır."""
        ortak = {"period": "day", "metric_type": "total_value",
                 "since": int(bas_tr.timestamp()), "until": int(bit_tr.timestamp())}
        sonuc = {}
        istekler = [
            ("reach", "follow_type"), ("reach", "media_product_type"),
            ("views", "follow_type"),
            ("accounts_engaged,total_interactions,profile_links_taps", None),
        ]
        for metrik, kirilim in istekler:
            p = dict(ortak, metric=metrik)
            if kirilim:
                p["breakdown"] = kirilim
            veri, hata = self.get("me/insights", **p)
            if veri is None:
                self.uyarilar.append(f"Hesap geneli {metrik}"
                                     f"{' (' + kirilim + ')' if kirilim else ''} alınamadı ({hata}).")
                continue
            for d in veri.get("data", []):
                tv = d.get("total_value") or {}
                anahtar = d.get("name")
                if "value" in tv:
                    sonuc[anahtar] = tv["value"]
                for k in tv.get("breakdowns", []):
                    for sat in k.get("results", []):
                        deger = (sat.get("dimension_values") or ["?"])[0]
                        sonuc[f"{anahtar}:{deger}"] = sat.get("value", 0)
        return sonuc


def _degerler(veri):
    sonuc = {}
    for d in veri.get("data", []):
        if "values" in d and d["values"]:
            sonuc[d["name"]] = d["values"][0].get("value", 0)
        elif "total_value" in d:
            sonuc[d["name"]] = (d["total_value"] or {}).get("value", 0)
    return sonuc


# ---------------------------------------------------------------- takipçi kaydı

def takipci_satirlari():
    metin, _ = kayit.dosyayi_al()
    return kayit.satirlari_oku(metin)


def paylasim_adlari(medyalar, satirlar):
    """Her gönderiye takipci.md'deki paylaşım adını eşler. Kayıt üretim işinde, Instagram'a
    gönderilmeden birkaç dakika önce düşer: gönderiden önceki en yakın kayıt (en çok 25 dk) seçilir.
    Eşleşmezse açıklamadan, o da olmazsa Reels/Gönderi."""
    gercek = [(datetime.strptime(f"{s[0]} {s[1]}", "%Y-%m-%d %H:%M").replace(tzinfo=TR_SAAT), s[2])
              for s in satirlar if "(deneme)" not in s[2]]
    kullanilan = set()
    for m in sorted(medyalar, key=lambda x: x["_zaman"]):
        adaylar = [(z, i) for i, (z, _) in enumerate(gercek) if i not in kullanilan
                   and -25 <= (z - m["_zaman"]).total_seconds() / 60 <= 2]
        ad = None
        if adaylar:
            _, i = max(adaylar)
            kullanilan.add(i)
            ad = gercek[i][1]
        m["_ad"] = RAPOR_ADI.get(ad, ad) if ad else aciklamadan_ad(m)


def aciklamadan_ad(m):
    a = (m.get("caption") or "").lower()
    for anahtar, ad in (("haftalık gümüş özeti", "Haftalık özet"), ("aylık gümüş özeti", "Aylık özet"),
                        ("günün gümüş özeti", "Günlük özet"), ("güncel gümüş fiyatları", "Fiyat Reels'i"),
                        ("yasal bilgilendirme", "Yasal bilgilendirme")):
        if anahtar in a:
            return ad
    return TUR_ADI.get(m.get("media_product_type"), "Gönderi")


# ---------------------------------------------------------------- biçim

def sayi(n):
    if n is None or n == "":
        return "—"
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(n)):,}".replace(",", ".")


def yuzde(pay, payda):
    if not payda:
        return "—"
    return f"%{round(100 * pay / payda)}"


def saniye(ms):
    if ms is None:
        return "—"
    return f"{ms / 1000:.1f}".replace(".", ",") + " sn"


def tarih_tr(g):
    return f"{g.day} {AYLAR[g.month - 1]}"


def _kisa_zaman(z):
    return f"{GUNLER[z.weekday()]} {z.day:02d}.{z.month:02d} {z:%H:%M}"


def _ort(liste, anahtar):
    """Ortalama; 10 ve üstü tam sayıya yuvarlanır (138,7 kişi değil 139 kişi)."""
    degerler = [m["_ist"].get(anahtar) for m in liste if m["_ist"].get(anahtar) is not None]
    if not degerler:
        return None
    o = sum(degerler) / len(degerler)
    return round(o) if o >= 10 else round(o, 1)


def _top(liste, anahtar):
    degerler = [m["_ist"].get(anahtar) for m in liste if m["_ist"].get(anahtar) is not None]
    return sum(degerler) if degerler else None


def gunluk_takipci(satirlar, bas, bit):
    """Her günün son kaydı ve bir önceki güne göre değişim: [(gün, takipçi, değişim)]."""
    gun_sonu = {}
    for s in satirlar:
        gun_sonu[s[0]] = s[3]          # satırlar eskiden yeniye; günün sonuncusu kalır
    sonuc, onceki = [], None
    for g_str in sorted(gun_sonu):
        g = date.fromisoformat(g_str)
        if g < bas:
            onceki = gun_sonu[g_str]
            continue
        if g > bit:
            break
        n = gun_sonu[g_str]
        sonuc.append((g, n, None if onceki is None else n - onceki))
        onceki = n
    return sonuc


def rapor_yaz(medyalar, hesap, satirlar, bas, bit, hesap_adi, uyarilar, deneme, simdi):
    sat = []
    baslik = f"# Haftalık Instagram raporu · {hesap_adi}" if hesap_adi else "# Haftalık Instagram raporu"
    sat += [baslik, "",
            f"**{tarih_tr(bas)} – {tarih_tr(bit)} {bit.year}**"
            + (" · örnek (deneme) rapor" if deneme else "")
            + f" · hazırlandı: {simdi.day:02d}.{simdi.month:02d}.{simdi.year} {simdi:%H:%M}", ""]

    # --- özet
    gunler = gunluk_takipci(satirlar, bas, bit)
    reels = [m for m in medyalar if m.get("media_product_type") == "REELS"]
    gonderi = [m for m in medyalar if m.get("media_product_type") != "REELS"]
    ozet = []
    if gunler:
        ilk = next((g for g in gunler if g[2] is not None), None)
        bas_sayi = (ilk[1] - ilk[2]) if ilk else None
        son = gunler[-1][1]
        if bas_sayi is not None:
            ozet.append(f"**Takipçi:** {sayi(bas_sayi)} → **{sayi(son)}** ({kayit._isaretli(son - bas_sayi)})")
        else:
            ozet.append(f"**Takipçi:** {sayi(son)} (kayıt bu hafta başladı; ilk gün {sayi(gunler[0][1])})")
    ozet.append(f"**Paylaşım:** {len(medyalar)} ({len(reels)} Reels, {len(gonderi)} gönderi)"
                " · hikâyeler 24 saatte kaybolduğu için bu sayıya ve tabloya girmez")
    ul = hesap.get("reach")
    if ul is not None:
        satir = f"**Hesaba ulaşan kişi:** {sayi(ul)}"
        tak, etm = hesap.get("reach:FOLLOWER"), hesap.get("reach:NON_FOLLOWER")
        if tak is not None or etm is not None:
            satir += (f" · takip etmeyen: **{sayi(etm or 0)}** ({yuzde(etm or 0, (tak or 0) + (etm or 0))}),"
                      f" takipçi: {sayi(tak or 0)}")
        ozet.append(satir)
    if hesap.get("views") is not None:
        satir = f"**Görüntülenme:** {sayi(hesap['views'])}"
        etm = hesap.get("views:NON_FOLLOWER")
        if etm is not None:
            satir += f" · takip etmeyenlerden: {yuzde(etm, hesap['views'])}"
        ozet.append(satir)
    for anahtar, ad in (("accounts_engaged", "Etkileşen hesap"), ("profile_links_taps", "Profildeki bağlantılara dokunma")):
        if hesap.get(anahtar) is not None:
            ozet.append(f"**{ad}:** {sayi(hesap[anahtar])}")
    toplam = {o: _top(medyalar, o) for o in ("likes", "comments", "saved", "shares")}
    ozet.append(f"**Gönderilerde:** {sayi(toplam['likes'])} beğeni · {sayi(toplam['comments'])} yorum · "
                f"{sayi(toplam['saved'])} kaydetme · {sayi(toplam['shares'])} paylaşma")
    sat += ["## Özet", ""] + [f"- {o}" for o in ozet] + [""]

    # --- öne çıkanlar
    one = []
    if medyalar:
        en = max(medyalar, key=lambda m: m["_ist"].get("reach") or 0)
        if en["_ist"].get("reach"):
            one.append(f"En çok kişiye ulaşan: [{en['_ad']} · {_kisa_zaman(en['_zaman'])}]({en.get('permalink', '')})"
                       f" — {sayi(en['_ist']['reach'])} kişi")
        for anahtar, ad in (("saved", "kaydedilen"), ("shares", "paylaşılan")):
            en = max(medyalar, key=lambda m: m["_ist"].get(anahtar) or 0)
            if en["_ist"].get(anahtar):
                one.append(f"En çok {ad}: [{en['_ad']} · {_kisa_zaman(en['_zaman'])}]({en.get('permalink', '')})"
                           f" — {sayi(en['_ist'][anahtar])}")
    r_ort, g_ort = _ort(reels, "reach"), _ort(gonderi, "reach")
    if r_ort and g_ort:
        if r_ort >= g_ort:
            one.append(f"Reels'ler ortalamada gönderilerin **{sayi(r_ort / g_ort)} katı** kişiye ulaştı "
                       f"({sayi(r_ort)} – {sayi(g_ort)}).")
        else:
            one.append(f"Gönderiler ortalamada Reels'lerin **{sayi(g_ort / r_ort)} katı** kişiye ulaştı "
                       f"({sayi(g_ort)} – {sayi(r_ort)}).")
    if one:
        sat += ["## Öne çıkanlar", ""] + [f"- {o}" for o in one] + [""]

    # --- Reels mi gönderi mi
    sat += ["## Reels mi gönderi mi?", "",
            "| | Adet | Ort. ulaşılan | Ort. görüntülenme | Ort. beğeni | Kaydetme | Paylaşma |",
            "|---|---|---|---|---|---|---|"]
    for ad, liste in (("Reels", reels), ("Gönderi", gonderi)):
        if liste:
            sat.append(f"| {ad} | {len(liste)} | {sayi(_ort(liste, 'reach'))} | {sayi(_ort(liste, 'views'))} | "
                       f"{sayi(_ort(liste, 'likes'))} | {sayi(_top(liste, 'saved'))} | {sayi(_top(liste, 'shares'))} |")
    kir = [(ad, hesap.get(f"reach:{k}")) for k, ad in (("REEL", "Reels"), ("POST", "Gönderi"),
                                                       ("CAROUSEL_CONTAINER", "Kaydırmalı"), ("STORY", "Hikâye"))]
    kir = [(ad, v) for ad, v in kir if v]
    if kir:
        sat += ["", "Hesap geneli, içerik türüne göre ulaşılan kişi: "
                + " · ".join(f"{ad} {sayi(v)}" for ad, v in kir)
                + " (bir kişi birden çok türde sayılabilir)."]
    sat.append("")

    # --- paylaşım türüne göre
    gruplar = {}
    for m in medyalar:
        gruplar.setdefault(m["_ad"], []).append(m)
    if gruplar:
        sat += ["## Paylaşım türüne göre", "",
                "| Paylaşım | Adet | Ort. ulaşılan | Ort. beğeni | Kaydetme | Paylaşma |",
                "|---|---|---|---|---|---|"]
        for ad, liste in sorted(gruplar.items(), key=lambda x: -(_ort(x[1], "reach") or 0)):
            sat.append(f"| {ad} | {len(liste)} | {sayi(_ort(liste, 'reach'))} | {sayi(_ort(liste, 'likes'))} | "
                       f"{sayi(_top(liste, 'saved'))} | {sayi(_top(liste, 'shares'))} |")
        sat.append("")

    # --- tek tek
    if medyalar:
        sat += ["## Tek tek paylaşımlar", "",
                "| Zaman | Paylaşım | Ulaşılan | Görüntülenme | Beğeni | Yorum | Kaydetme | Paylaşma | Ort. izlenme / takip |",
                "|---|---|---|---|---|---|---|---|---|"]
        for m in sorted(medyalar, key=lambda x: x["_zaman"]):
            i = m["_ist"]
            if m.get("media_product_type") == "REELS":
                son_hucre = saniye(i.get("ig_reels_avg_watch_time"))
            else:
                son_hucre = f"{sayi(i.get('follows'))} takip" if i.get("follows") is not None else "—"
            sat.append(f"| {_kisa_zaman(m['_zaman'])} | [{m['_ad']}]({m.get('permalink', '')}) | {sayi(i.get('reach'))} | "
                       f"{sayi(i.get('views'))} | {sayi(i.get('likes'))} | {sayi(i.get('comments'))} | "
                       f"{sayi(i.get('saved'))} | {sayi(i.get('shares'))} | {son_hucre} |")
        sat.append("")

    # --- takipçi günlük
    if gunler:
        sat += ["## Günlere göre takipçi", "", "| Gün | Takipçi (gün sonu) | Değişim |", "|---|---|---|"]
        for g, n, d in gunler:
            sat.append(f"| {GUNLER[g.weekday()]} {g.day} {AYLAR[g.month - 1]} | {sayi(n)} | "
                       f"{'—' if d is None else kayit._isaretli(d)} |")
        sat.append("")

    # --- notlar
    notlar = [
        "Rakamlar raporun hazırlandığı andaki toplamlardır; haftanın son günlerindeki paylaşımlar büyümeye devam eder.",
        "\"Ulaşılan\" o paylaşımı en az bir kez gören farklı hesap sayısıdır; \"görüntülenme\" tekrar izlemeleri de sayar.",
        "Takip etmeyen / takipçi ayrımını Instagram yalnızca hesap geneli için veriyor, tek tek paylaşım için vermiyor.",
        "Reels'te son sütun ortalama izlenme süresi, gönderide o gönderiden gelen takip sayısıdır.",
        "Takipçi tablosu gumus-kayit/takipci.md'den gelir (bot her paylaşımda yazar).",
    ]
    sat += ["## Notlar", ""] + [f"- {n}" for n in notlar + uyarilar] + [""]
    sat += ["Bu dosyayı gumus-bot yazar (bot/rapor.py); elle değiştirme.", ""]
    return "\n".join(sat)


# ---------------------------------------------------------------- akış

def ozel_depoya_yaz(yol, metin, mesaj):
    r = kayit._github("GET", f"/contents/{yol}")
    sha = r.json().get("sha") if r.status_code == 200 else None
    govde = {"message": mesaj, "content": base64.b64encode(metin.encode("utf-8")).decode()}
    if sha:
        govde["sha"] = sha
    r = kayit._github("PUT", f"/contents/{yol}", json=govde)
    if r.status_code >= 400:
        raise RaporHatasi(f"Rapor özel depoya yazılamadı (HTTP {r.status_code})")


def calistir(bit, gun, deneme):
    simdi = datetime.now(TR_SAAT)
    bas = bit - timedelta(days=gun - 1)
    bas_tr = datetime.combine(bas, datetime.min.time(), TR_SAAT)
    bit_tr = min(datetime.combine(bit + timedelta(days=1), datetime.min.time(), TR_SAAT), simdi)

    ig = Instagram(os.environ["IG_TOKEN"])
    medyalar = [m for m in ig.medyalar(bas_tr) if m["_zaman"] < bit_tr]
    for m in medyalar:
        m["_ist"] = ig.medya_istatistik(m)
    hesap = ig.hesap_istatistik(bas_tr, bit_tr)
    satirlar = takipci_satirlari()
    paylasim_adlari(medyalar, satirlar)

    from main import hesap_adi   # görsellerdeki kullanıcı adıyla aynı
    metin = rapor_yaz(medyalar, hesap, satirlar, bas, bit, hesap_adi(), ig.uyarilar, deneme, simdi)
    yol = f"raporlar/{bit.isoformat()}{'-deneme' if deneme else ''}.md"
    ozel_depoya_yaz(yol, metin, f"Haftalık rapor: {bas.isoformat()} – {bit.isoformat()}"
                                + (" (deneme)" if deneme else ""))
    # Yalnızca sayı içermeyen durum bilgisi: bu günlük herkese açık.
    print(f"Rapor yazıldı: {kayit.DEPO}/{yol} (özel depo) · {len(medyalar)} paylaşım · "
          f"{ig.istek_sayisi} Instagram isteği")
    for o in sorted(ig.desteklenmeyen.items()):
        print(f"Instagram'ın vermediği ölçüler ({o[0]}): {', '.join(sorted(o[1]))}")
    for u in ig.uyarilar:
        print(f"::warning::{u}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bitis", help="raporun son günü (YYYY-MM-DD); varsayılan dün")
    ap.add_argument("--gun", type=int, default=7)
    a = ap.parse_args()
    for degisken in ("IG_TOKEN", "KAYIT_PAT"):
        if not os.environ.get(degisken):
            print(f"::error::{degisken} tanımlı değil; rapor hazırlanamadı.")
            sys.exit(1)
    bit = date.fromisoformat(a.bitis) if a.bitis else datetime.now(TR_SAAT).date() - timedelta(days=1)
    deneme = os.environ.get("DENEME", "").lower() == "true"
    try:
        calistir(bit, a.gun, deneme)
    except (RaporHatasi, kayit.KayitHatasi) as e:
        print(f"::error::Rapor hazırlanamadı: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
