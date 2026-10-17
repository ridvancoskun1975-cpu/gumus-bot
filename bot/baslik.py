"""Günlük başlık ve özel gün kuralları.

Hafta içi fiyat paylaşımlarında (Reels ~10:00, günlük özet ~20:00) "GRAM GÜMÜŞ" başlığının yerine
o günün verisinden kurallı bir başlık çıkar: "Üst üste 3. gün yükseliş", "Son 1 ayın en yükseği",
"Haftaya düşüşle başladı"... Gram gümüş yuvarlak bir eşiği kayıtlarda ilk kez aştığında ya da en az
bir aylık en yükseğine çıktığında paylaşım özel görselle (templates/ozel.html) gider.

Hepsi botun kendi günlük kayıtlarından (veri/gecmis.json: iş günlerinin son paylaşımı, yaklaşık
20:00) hesaplanan olgulardır; tahmin ya da yorum içermez. Kayıtlar 13 Ekim 2026'da başladığı için
"en yüksek" ve "ilk kez" ifadeleri yalnızca kayıtların kapsadığı dönem için kullanılır: bir pencere
("son 1 ayın") ancak kayıtlar o pencerenin tamamını kapsıyorsa yazılır.

Yalnızca standart kütüphane kullanır. Kurallar bot/test_baslik.py ile sınanır.
"""
import math
from datetime import timedelta

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

ESIK_ADIM = 10        # ₺: yuvarlak eşikler 100, 110, 120 ...
# Pencereler (gün, "son … en yükseği" içindeki ad); küçükten büyüğe
PENCERELER = [(7, "1 haftanın"), (14, "2 haftanın"), (21, "3 haftanın"), (30, "1 ayın"),
              (60, "2 ayın"), (90, "3 ayın"), (180, "6 ayın"), (365, "1 yılın")]
PENCERE_KAYIT = 4     # pencerede en az bu kadar önceki kayıt olmalı
OZEL_PENCERE = 30     # en az bu genişlikte (gün) bir en yüksek özel görsel olur
OZEL_ARA = 5          # son bu kadar iş gününde aynı ya da daha geniş en yüksek varsa özel görsel yinelenmez
SERI_ALT = 3          # "üst üste N. gün" için en az gün
ESIK_SAKIN = 5        # eşiğin yeniden geçilmesi başlık olsun diye son bu kadar kayıt öbür tarafta olmalı
ILK_KEZ_GUN = 30      # "kayıtlarımızda ilk kez" demek için kayıtların en az bu kadar günü kapsaması gerekir
GRAFIK_NOKTA = 45     # özel görseldeki grafikte en fazla nokta


def _y(x):
    """Görselde yazılan değer (2 ondalık); karşılaştırmalar bununla yapılır."""
    return round(x + 1e-9, 2)


def tr_sayi(x, basamak=2):
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def tr_buyuk(metin):
    return metin.replace("i", "İ").replace("ı", "I").upper()


def onceki_is_gunu(gun):
    gun -= timedelta(days=1)
    while gun.weekday() >= 5:
        gun -= timedelta(days=1)
    return gun


def pencere(seri, gun, deger, yon):
    """deger, son W günün bütün kayıtlarından yüksekse (yon="artis") ya da düşükse (yon="dusus")
    bunu sağlayan en geniş pencere W (gün); yoksa None.

    Pencere ancak kayıtlar onu baştan sona kapsıyorsa sayılır: kayıtlar 3 haftalıksa "son 1 ayın
    en yükseği" denmez.
    """
    if not seri:
        return None
    ilk, sonuc = min(seri), None
    for w, _ in PENCERELER:
        bas = gun - timedelta(days=w)
        if ilk > bas:
            break
        ic = [v for d, v in seri.items() if bas <= d < gun]
        if not all((v < deger) if yon == "artis" else (v > deger) for v in ic):
            break
        if len(ic) >= PENCERE_KAYIT:
            sonuc = w
    return sonuc


def pencere_adi(w):
    return dict(PENCERELER)[w]


def seri_say(seri, gun, deger):
    """Bugün dahil, art arda aynı yönde değişen iş günü sayısı: (yon, n). Değişim yoksa (None, 0).

    Arada kaydı olmayan bir iş günü varsa seri orada kesilir.
    """
    yon, n = None, 0
    g, v = gun, deger
    while True:
        o = onceki_is_gunu(g)
        if o not in seri:
            break
        y = "artis" if v > seri[o] else "dusus" if v < seri[o] else None
        if y is None or (yon and y != yon):
            break
        yon, n = y, n + 1
        g, v = o, seri[o]
    return yon, n


def _oncesi(seri, gun):
    return {d: v for d, v in seri.items() if d < gun}


def _esik(seri, deger, once):
    """Yuvarlak eşik geçişi: ("yukari"|"asagi", eşik, kayıtlarda ilk kez mi) ya da None."""
    son = [seri[d] for d in sorted(seri)][-ESIK_SAKIN:]
    if deger > once:
        t = math.floor(deger / ESIK_ADIM) * ESIK_ADIM
        if t == deger:
            t -= ESIK_ADIM
        if t > 0 and once <= t:
            if all(v <= t for v in seri.values()):
                return "yukari", t, True
            if all(v <= t for v in son):
                return "yukari", t, False
    elif deger < once:
        t = math.ceil(deger / ESIK_ADIM) * ESIK_ADIM
        if t == deger:
            t += ESIK_ADIM
        if once >= t and all(v >= t for v in son):
            return "asagi", t, False
    return None


def _grafik_serisi(seri, gun, deger, gun_sayisi):
    """Özel görseldeki grafik için son günlerin kayıtları + bugün: [(tarih, değer)]."""
    bas = gun - timedelta(days=gun_sayisi)
    noktalar = sorted((d, v) for d, v in seri.items() if d >= bas)[-(GRAFIK_NOKTA - 1):]
    return noktalar + [(gun, deger)]


def degerlendir(kayitlar, gun, deger, sabah=False):
    """Bugünün başlığı ve (varsa) özel durumu.

    kayitlar: {tarih: gram} (bugünden önceki günler kullanılır), gun: bugün, deger: bugünkü gram.
    sabah: sabah Reels'i (Rıdvan, 16 Ekim 2026 23:00): gün daha bitmediği için bugünü tamamlanmış gün sayan
    "Üst üste N. gün …" ve "N günlük … sona erdi" başlıkları çıkmaz; yerine (varsa) anlık doğru olan başlık gelir
    (eşik, son X'in en yükseği/düşüğü, haftaya başlangıç). Akşam özetinde hepsi çıkar.
    Dönüş: {"ozel": None | {...}, "baslik": None | {"yon", "metin", "kural"}, "not": str | None}
    """
    seri = {d: _y(v) for d, v in kayitlar.items() if d < gun}
    deger = _y(deger)
    sonuc = {"ozel": None, "baslik": None, "not": None}
    son_gun = max(seri) if seri else None
    if son_gun is None or (gun - son_gun).days > 6:
        return sonuc
    once = seri[son_gun]
    ilk = min(seri)
    sonuc["not"] = ("Başlık botun günlük kayıtlarına göredir (iş günlerinin son paylaşımı, yaklaşık 20:00; "
                    f"kayıtların başlangıcı {ilk.day} {AYLAR[ilk.month - 1]} {ilk.year}).")

    esik = _esik(seri, deger, once)
    w_yuksek = pencere(seri, gun, deger, "artis")
    w_dusuk = pencere(seri, gun, deger, "dusus")
    yon, n = seri_say(seri, gun, deger)
    dun = onceki_is_gunu(gun)

    # ---- özel görsel: eşik ilk kez aşıldı ya da en az bir aylık en yüksek
    zirve = None
    if w_yuksek and w_yuksek >= OZEL_PENCERE:
        g, tekrar = gun, False
        for _ in range(OZEL_ARA):
            g = onceki_is_gunu(g)
            if g in seri:
                wo = pencere(_oncesi(seri, g), g, seri[g], "artis")
                if wo and wo >= w_yuksek:
                    tekrar = True
                    break
        if not tekrar:
            bas = gun - timedelta(days=w_yuksek)
            ic = [(v, d) for d, v in seri.items() if d >= bas]
            ust, ust_gun = max(ic)
            zirve = {"pencere": w_yuksek, "ad": pencere_adi(w_yuksek), "onceki": ust, "onceki_gun": ust_gun}

    if esik and esik[0] == "yukari" and esik[2]:
        t = esik[1]
        t_metin = tr_sayi(t, 0)
        alt = []
        if (gun - ilk).days >= ILK_KEZ_GUN:
            alt.append("Günlük kayıtlarımızda ilk kez")
        if zirve:
            alt.append(f"Son {zirve['ad']} en yükseği")
        sonuc["ozel"] = {
            "tur": "esik", "esik": t,
            "etiket": "EŞİK AŞILDI",
            "manset": f"Gram gümüş {t_metin} lirayı aştı",
            "satirlar": [f"{t_metin} lirayı aştı"],
            "kisa": f"{t_metin} lirayı aştı",
            "alt": " · ".join(alt) or None,
            "cizgi": float(t), "cizgi_etiket": f"{t_metin} ₺",
            "grafik": _grafik_serisi(seri, gun, deger, max(zirve["pencere"] if zirve else 0, 30)),
        }
    elif zirve:
        og = zirve["onceki_gun"]
        sonuc["ozel"] = {
            "tur": "zirve", "pencere": zirve["pencere"],
            "etiket": tr_buyuk(f"Son {zirve['ad']} en yükseği"),
            "manset": f"Gram gümüş son {zirve['ad']} en yükseğinde",
            "satirlar": [f"son {zirve['ad']}", "en yükseğinde"],
            "kisa": f"Son {zirve['ad']} en yükseği",
            "alt": f"Önceki en yüksek: {tr_sayi(zirve['onceki'])} ₺ ({og.day} {AYLAR[og.month - 1]})",
            "cizgi": zirve["onceki"], "cizgi_etiket": f"önceki en yüksek {tr_sayi(zirve['onceki'])} ₺",
            "grafik": _grafik_serisi(seri, gun, deger, zirve["pencere"]),
        }

    # ---- günlük başlık (sakin): ilk tutan kural
    def b(yon_, metin, kural):
        return {"yon": yon_, "metin": metin, "kural": kural}

    baslik = None
    if esik and not (esik[0] == "yukari" and esik[2]):
        t_metin = tr_sayi(esik[1], 0)
        baslik = (b("artis", f"Yeniden {t_metin} liranın üzerinde", "esik") if esik[0] == "yukari"
                  else b("dusus", f"{t_metin} liranın altına indi", "esik"))
    if not baslik and (w_yuksek or w_dusuk):
        w, y, ek = (w_yuksek, "artis", "en yükseği") if w_yuksek else (w_dusuk, "dusus", "en düşüğü")
        # Aynı pencere dün de geçerliyse ve seri sürüyorsa her gün aynı başlık çıkmasın: seri yazılır
        wo = pencere(_oncesi(seri, dun), dun, seri[dun], y) if dun in seri else None
        if sabah or not (wo == w and n >= SERI_ALT):     # sabah seri yazılmadığı için pencere susmaz
            baslik = b(y, f"Son {pencere_adi(w)} {ek}", "pencere")
    if not baslik and not sabah and yon and n == 1 and dun in seri:
        # Dün biten seri: bugün ters yöne döndüyse "3 günlük yükseliş sona erdi"
        yon_dun, n_dun = seri_say(_oncesi(seri, dun), dun, seri[dun])
        if yon_dun and yon_dun != yon and n_dun >= SERI_ALT:
            ad = "yükseliş" if yon_dun == "artis" else "düşüş"
            baslik = b(yon, f"{n_dun} günlük {ad} sona erdi", "donus")
    if not baslik and not sabah and yon and n >= SERI_ALT:
        baslik = b(yon, f"Üst üste {n}. gün {'yükseliş' if yon == 'artis' else 'düşüş'}", "seri")
    if not baslik and yon and gun.weekday() == 0:
        baslik = b(yon, f"Haftaya {'yükselişle' if yon == 'artis' else 'düşüşle'} başladı", "hafta")
    sonuc["baslik"] = baslik
    if not (baslik or sonuc["ozel"]):
        sonuc["not"] = None
    return sonuc


def donem_ozel(kayitlar, gunler):
    """Haftalık ve aylık özette gorilin kutlama (özel gün) hâli (Rıdvan, 18 Ekim 2026: "İki öneriyi de kabul
    ediyorum"; olumlu bir olay olduysa goril sevinsin). Günlük özel gün kurallarının dönem karşılığı:

      1) Dönemin bir gününde gram gümüş yuvarlak bir eşiği kayıtlarda ilk kez aştı (günlük "eşik aşıldı" ile
         aynı kural) ve dönem bu eşiğin üstünde kapandı → {"tur": "esik", "esik": 100, "kisa": "100 lirayı aştı"}
      2) Dönemin son değeri en az OZEL_PENCERE günlük en yüksek (kayıtlar pencerenin tamamını kapsıyorsa)
         → {"tur": "zirve", "pencere": 30, "kisa": "son 1 ayın en yükseğinde kapandı"}

    Eşik önce gelir; ikisi de yoksa None. İkisi de dönemin artıda kapandığı anlamına gelir (dönem başındaki
    değer eşiğin / pencerenin altında kalır), goril düşen bir dönemde kutlamaz.
    kayitlar: {tarih: gram} (dönemin son gününe kadar), gunler: dönemin kayıtlı günleri."""
    seri = {d: _y(v) for d, v in kayitlar.items() if d <= gunler[-1]}
    son_gun = gunler[-1]
    son = seri[son_gun]
    esikler = []
    for g in gunler:
        once = {d: v for d, v in seri.items() if d < g}
        if not once or g not in seri:
            continue
        e = _esik(once, seri[g], once[max(once)])
        if e and e[0] == "yukari" and e[2] and son > e[1]:
            esikler.append(e[1])
    if esikler:
        t = max(esikler)
        return {"tur": "esik", "esik": t, "kisa": f"{tr_sayi(t, 0)} lirayı aştı"}
    w = pencere(_oncesi(seri, son_gun), son_gun, son, "artis")
    if w and w >= OZEL_PENCERE:
        return {"tur": "zirve", "pencere": w, "kisa": f"son {pencere_adi(w)} en yükseğinde kapandı"}
    return None
