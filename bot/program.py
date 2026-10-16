"""Paylaşım programı: "ne zaman ne paylaşılıyor" bilgisini elle yazmak yerine botun gerçek ayarlarından üretir.

Bilgi sayfasının her yeri her zaman güncel kalsın diye (Rıdvan, 14 Ekim 2026: "Bilgi sayfasının her yeri
her zaman güncel kalmalı.") sayfadaki saatler, günler ve takvim buradan gelir:
- saatler ve günler: .github/workflows/paylas.yml içindeki cron satırları ve "Türü belirle" adımındaki
  cron → tür eşlemesi (eşlemede olmayan cron reels'tir, iş akışındaki "else" gibi)
- rehber, kısa Reels ve aylık özet günleri: bot/bilgi.py → takvim(), kisa_takvim(); bot/aylik.py
- haftalık kart günleri (ayrı paylaşım; Reels ve özete ek): bot/kart.py → KART_GUNLERI, KART_BASLANGIC
- hikâyeye de giden türler: bot/main.py → HIKAYE_TURLERI (rehber bölümleri her zaman hikâyeye de gider)
- ilk haftalık özet ve ilk pazar yorumu: günlük kayıtların başladığı güne göre (botun kendi kurallarıyla)
- ECB kurunun yayın saati: iş günleri 16:00 Frankfurt saati, o günün Türkiye karşılığı (yaz/kış saati)

Cron saatleri UTC'dir; Türkiye yıl boyu UTC+3. GitHub zamanlı işleri genelde 5-15 dk gecikmeli başlatır ve
üretim birkaç dakika sürer; bu yüzden gösterilen saat = cron + GECIKME_DK, 5 dakikaya yuvarlanmış ("~10:00").
Yalnızca standart kütüphane ve botun kendi modülleri kullanılır.

Yerelde: python bot/program.py → bugünkü tabloyu yazdırır.
"""
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aylik  # noqa: E402
import bilgi  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
IS_AKISI = KOK / ".github" / "workflows" / "paylas.yml"
TR_SAAT = ZoneInfo("Europe/Istanbul")
ECB_SAATI = (16, 0)                       # ECB referans kurları iş günleri ~16:00 CET/CEST'te yayımlanır
ECB_YER = ZoneInfo("Europe/Berlin")
GECIKME_DK = 10                           # cron saatinden paylaşıma kadar geçen yaklaşık süre
SIRADAKI_GUN_SAYISI = 4                   # rehber satırında gösterilecek sıradaki gün sayısı
KAYIT_TURLERI = ("reels", "post")         # günlük fiyat kaydı yazan (fiyatı güncelleyen) türler

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
         "Kasım", "Aralık"]
# Ay adlarının yönelme eki ("21 Ekim'e kadar", "5 Kasım'a kadar")
AY_YONELME = ["Ocak'a", "Şubat'a", "Mart'a", "Nisan'a", "Mayıs'a", "Haziran'a", "Temmuz'a", "Ağustos'a",
              "Eylül'e", "Ekim'e", "Kasım'a", "Aralık'a"]
GUN_ADLARI = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]

# Türlerin sayfadaki adı. Hikâye bilgisi ayrıca HIKAYE_TURLERI'nden eklenir.
TUR_ADI = {
    "reels": "Güncel fiyat",
    "post": "Günün özeti",
    "hafta": "Haftalık özet ve grafik",
    "ay": "Aylık özet ve grafik",
    "yorum": "Kısa, orta ve uzun vade yapay zekâ yorumu",
    "bilgi": "Gümüş rehberi",
    "kisa": "Rehberden kısa video",
    "kart": '"Kaç gram eder?" (çarşamba) ve altın–gümüş (cuma) kartı',
}
TUR_BICIM = {   # Instagram'daki biçim
    "reels": "Reels", "post": "Reels", "hafta": "Reels", "ay": "Reels", "kisa": "Reels", "kart": "Reels",
    "yorum": "kaydırmalı gönderi", "bilgi": "kaydırmalı gönderi",
}


class ProgramHatasi(Exception):
    pass


# ---------------------------------------------------------------- iş akışını okuma

def cronlar(yol=None):
    """[(cron, tür)] — iş akışındaki zamanlı çalışmalar, iş akışının seçtiği türle."""
    metin = Path(yol or IS_AKISI).read_text(encoding="utf-8")
    zamanlar = re.findall(r"^\s*-\s*cron:\s*'([^']+)'", metin, flags=re.M)
    if not zamanlar:
        raise ProgramHatasi(f"{yol} içinde cron satırı bulunamadı")
    esleme = dict(re.findall(r'github\.event\.schedule \}\}" = "([^"]+)" \]; then\s*\n\s*tur=(\w+)', metin))
    return [(c, esleme.get(c, "reels")) for c in zamanlar]


def _alan_coz(alan, en_az, en_cok):
    """Cron alanını sayı kümesine çevirir ("1-5", "1,3", "*", "0")."""
    if alan == "*":
        return set(range(en_az, en_cok + 1))
    sonuc = set()
    for parca in alan.split(","):
        if "-" in parca:
            a, b = parca.split("-")
            sonuc |= set(range(int(a), int(b) + 1))
        else:
            sonuc.add(int(parca))
    return sonuc


def cron_coz(cron):
    """(TR saat, dakika) ve Python hafta günleri kümesi (pazartesi 0) — gecikmesiz, cron'un kendisi."""
    dakika, saat, ayin_gunu, ay, hafta_gunu = cron.split()
    if ayin_gunu != "*" or ay != "*" or not dakika.isdigit() or not saat.isdigit():
        raise ProgramHatasi(f"Bu cron biçimi sayfaya çevrilemiyor: {cron}")
    utc = datetime(2026, 1, 5, int(saat), int(dakika), tzinfo=timezone.utc)   # günü önemsiz
    tr = utc.astimezone(TR_SAAT)
    gun_kaymasi = (tr.date() - utc.date()).days
    gunler = {((g - 1) % 7 + gun_kaymasi) % 7 for g in _alan_coz(hafta_gunu, 0, 7)}   # cron 0/7 = pazar
    return (tr.hour, tr.minute), gunler


def yayin_saati(cron):
    """"~10:00" — cron saati + GECIKME_DK, 5 dakikaya yuvarlanmış (TR)."""
    (s, d), _ = cron_coz(cron)
    toplam = s * 60 + d + GECIKME_DK
    toplam = int(round(toplam / 5.0)) * 5
    return f"~{(toplam // 60) % 24:02d}:{toplam % 60:02d}"


def gun_metni(gunler):
    gunler = set(gunler)
    if gunler == set(range(7)):
        return "Her gün"
    if gunler == set(range(5)):
        return "Hafta içi"
    if gunler == {5, 6}:
        return "Hafta sonu"
    adlar = [GUN_ADLARI[g] for g in sorted(gunler)]
    metin = adlar[0] if len(adlar) == 1 else ", ".join(adlar[:-1]) + " ve " + adlar[-1]
    return metin[0].upper() + metin[1:]


# ---------------------------------------------------------------- tarih yardımcıları

def tarih_listesi(gunler):
    """[date] → "15, 16, 19 ve 20 Ekim; 3 Kasım" (aynı ayın günleri birlikte)."""
    gruplar = []
    for g in gunler:
        if gruplar and gruplar[-1][0] == (g.year, g.month):
            gruplar[-1][1].append(g.day)
        else:
            gruplar.append(((g.year, g.month), [g.day]))
    parcalar = []
    for (_, ay), gl in gruplar:
        sayilar = [str(x) for x in gl]
        sayi = sayilar[0] if len(sayilar) == 1 else ", ".join(sayilar[:-1]) + " ve " + sayilar[-1]
        parcalar.append(f"{sayi} {AYLAR[ay - 1]}")
    return "; ".join(parcalar)


def _sonraki_is_gunu(gun):
    gun += timedelta(days=1)
    while gun.weekday() >= 5:
        gun += timedelta(days=1)
    return gun


def tek_tarih(gun):
    return f"{gun.day} {AYLAR[gun.month - 1]} {GUN_ADLARI[gun.weekday()].capitalize()}"


def ecb_saati(gun):
    """"~17:00" — ECB yayın saatinin o günkü Türkiye karşılığı."""
    an = datetime(gun.year, gun.month, gun.day, *ECB_SAATI, tzinfo=ECB_YER).astimezone(TR_SAAT)
    return an, f"~{an.hour:02d}:{an.minute:02d}"


def _kayitli_mi(gun, kayitlar, bugun):
    """Gün için fiyat kaydı var mı (geçmiş) ya da olacak mı (bugün ve sonrası hafta içi; bot her iş günü yazar)."""
    return gun in kayitlar or (gun >= bugun and gun.weekday() < 5)


def ilk_haftalik(bugun, kayitlar):
    """Bugünden itibaren haftalık özetin gerçekten çıkacağı ilk cumartesi (bot/main.py → _hafta_ayir kuralı:
    biten haftada en az 2 kayıt; önceki haftada kayıt yoksa ancak kayıtlar o hafta başladıysa çıkar, kısmi hafta)."""
    cumartesi = bugun + timedelta(days=(5 - bugun.weekday()) % 7)
    for _ in range(60):
        pazartesi = cumartesi - timedelta(days=5)
        bu = [pazartesi + timedelta(days=i) for i in range(5)]
        once = [pazartesi - timedelta(days=7 - i) for i in range(7)]
        onceki_var = any(_kayitli_mi(g, kayitlar, bugun) for g in once)
        kayitlar_bu_hafta_basladi = not any(g < pazartesi for g in kayitlar)
        if sum(_kayitli_mi(g, kayitlar, bugun) for g in bu) >= 2 and (onceki_var or kayitlar_bu_hafta_basladi):
            return cumartesi
        cumartesi += timedelta(days=7)
    return None


def ilk_yorum(bugun, kayitlar):
    """Pazar yorumunun çıkacağı ilk pazar (son 10 günde en az 2 kayıt kuralı)."""
    pazar = bugun + timedelta(days=(6 - bugun.weekday()) % 7)
    for _ in range(60):
        son10 = [pazar - timedelta(days=i) for i in range(11)]
        if sum(_kayitli_mi(g, kayitlar, bugun) for g in son10) >= 2:
            return pazar
        pazar += timedelta(days=7)
    return None


def siradaki_aylik(bugun, kayitlar):
    """Aylık özetin çıkacağı sıradaki gün (ILK_AY'dan önce değil; önceki ayda en az 5 kayıt olmalı)."""
    yil, ay = bugun.year, bugun.month
    for _ in range(24):
        g = aylik.ozet_gunu(yil, ay)
        if g >= bugun and g >= aylik.ILK_AY:
            ay_son = g.replace(day=1) - timedelta(days=1)
            ay_bas = ay_son.replace(day=1)
            kayitli = sum(_kayitli_mi(ay_bas + timedelta(days=i), kayitlar, bugun)
                          for i in range((ay_son - ay_bas).days + 1)
                          if (ay_bas + timedelta(days=i)).weekday() < 5)
            if kayitli >= 5:
                return g
        ay += 1
        if ay > 12:
            yil, ay = yil + 1, 1
    return None


# ---------------------------------------------------------------- program

def program(simdi=None, kayit_gunleri=(), hikaye_turleri=None, rehber_saati=(13, 45), rehber_hikaye=None,
            yorum_reels=None, rehber_reels=None):
    """Sayfa için hazır program.

    Döndürür: {"satirlar": [{"zaman", "ne", "ek": [satır, …]}], "guncelleme": "Hafta içi ~10:00 ve ~20:00",
    "son_deger_saati": "~20:00", "ecb": {...}, "rehber": {...}, "fiyat_gunleri": "Hafta içi", "yorum": bool}
    """
    simdi = simdi or datetime.now(TR_SAAT)
    bugun = simdi.date()
    kayitlar = set(kayit_gunleri)
    if hikaye_turleri is None or rehber_hikaye is None or yorum_reels is None:
        import main as bot
        if hikaye_turleri is None:
            hikaye_turleri = bot.HIKAYE_TURLERI
        if rehber_hikaye is None:
            # Rehber kareleri hikâyeye yalnızca bu açıksa otomatik gider (14 Ekim'den beri kapalı, elle paylaşılıyor)
            rehber_hikaye = getattr(bot, "REHBER_HIKAYE_OTOMATIK", True)
        if yorum_reels is None:
            # Pazar yorumu 15 Ekim 2026'dan beri kaydırmalının yanında 32 sn Reels ve hikâye olarak da gider
            yorum_reels = getattr(bot, "YORUM_REELS", False)
    if rehber_reels is None:
        import main as bot
        # Rehber günü 16 Ekim 2026'dan beri kaydırmalı yerine sesli Reels (main.REHBER_REELS)
        rehber_reels = getattr(bot, "REHBER_REELS", False)
    hikaye_turleri = set(hikaye_turleri) | ({"bilgi"} if rehber_hikaye else set())

    def ad(tur):
        bicim = TUR_BICIM.get(tur, "")
        if tur == "bilgi" and rehber_reels:
            bicim = "sesli Reels"
        if tur == "yorum" and yorum_reels:
            bicim = f"{bicim}, Reels ve hikâye" if bicim else "Reels ve hikâye"
        elif tur in hikaye_turleri:
            bicim = f"{bicim} ve hikâye" if bicim else "hikâye"
        return f"{TUR_ADI.get(tur, tur)} ({bicim})" if bicim else TUR_ADI.get(tur, tur)

    satirlar, saatler = [], {}
    for cron, tur in cronlar():
        (s, d), gunler = cron_coz(cron)
        saat = yayin_saati(cron)
        saatler.setdefault(tur, []).append((saat, gunler))
        sira = (min(gunler), s * 60 + d)
        if tur == "bilgi":
            # Bu çalışma rehber gününde rehberi, rehbersiz ayın ilk iş gününde aylık özeti paylaşır.
            gelecek = [date.fromisoformat(g) for g in sorted(bilgi.takvim())
                       if date.fromisoformat(g) > bugun
                       or (date.fromisoformat(g) == bugun and (simdi.hour, simdi.minute) < rehber_saati)]
            if gelecek:
                ilkler = gelecek[:SIRADAKI_GUN_SAYISI]
                ilk_hafta = sorted(date.fromisoformat(g) for g in bilgi.BASLANGIC)
                ilk_hafta = [g for g in ilk_hafta if g in gelecek]
                duzenli = gun_metni(bilgi.DUZENLI_GUNLER).lower()
                ekler = []
                if not ilk_hafta and all(g.weekday() in bilgi.DUZENLI_GUNLER for g in gelecek):
                    zaman = f"{gun_metni(bilgi.DUZENLI_GUNLER)} {saat}"
                else:
                    zaman = f"Rehber günleri {saat}"
                    if ilk_hafta and all(_sonraki_is_gunu(a) == b for a, b in zip(ilk_hafta, ilk_hafta[1:])):
                        son = ilk_hafta[-1]
                        ekler.append(f"{son.day} {AY_YONELME[son.month - 1]} kadar hafta içi her gün, sonra {duzenli}"
                                     if len(ilk_hafta) > 1 else f"{tek_tarih(son)}, sonra {duzenli}")
                ekler.append(f"sıradaki: {tarih_listesi(ilkler)}")
            else:
                zaman, ekler = f"{gun_metni(gunler)} {saat}", ["şimdilik sıradaki bölüm yok"]
            if rehber_hikaye:
                ekler.append("bölümler Instagram'da Öne çıkanlar › Rehber'de de toplanır")
            satirlar.append({"sira": sira, "zaman": zaman, "ne": ad("bilgi"), "ek": ekler})
            g_ay = siradaki_aylik(bugun, kayitlar)
            if g_ay:
                satirlar.append({"sira": (min(gunler), s * 60 + d + 1), "zaman": f"Ayın ilk iş günü {saat}",
                                 "ne": ad("ay"), "ek": ["o gün rehber varsa rehbersiz ilk iş günü",
                                                        f"sıradaki: {tek_tarih(g_ay)}"]})
            continue
        ek = []
        if tur == "kisa":
            gelecek = [date.fromisoformat(g) for g, _ in sorted(bilgi.kisa_takvim().items())
                       if date.fromisoformat(g) >= bugun]
            k = bilgi.kisa_takvim()
            ek = [f"sıradaki: {tek_tarih(gelecek[0])} (rehber #{k[gelecek[0].isoformat()]})" if gelecek
                  else "yeni rehber bölümleri eklenince devam eder"]
        elif tur == "hafta":
            ilk = ilk_haftalik(bugun, kayitlar)
            sonraki_cmt = bugun + timedelta(days=(5 - bugun.weekday()) % 7)
            if ilk and ilk > sonraki_cmt:
                ek = [f"ilki {tek_tarih(ilk)} (önceki haftayla kıyaslamak için kayıt gerekiyor)"]
        elif tur == "kart":
            import kart
            if bugun < kart.KART_BASLANGIC:
                ek = [f"ilki {tek_tarih(kart.KART_BASLANGIC)}"]
        elif tur == "yorum":
            ilk = ilk_yorum(bugun, kayitlar)
            sonraki_pz = bugun + timedelta(days=(6 - bugun.weekday()) % 7)
            if ilk and ilk > sonraki_pz:
                ek = [f"ilki {tek_tarih(ilk)}"]
        satirlar.append({"sira": sira, "zaman": f"{gun_metni(gunler)} {saat}", "ne": ad(tur), "ek": ek})

    satirlar.sort(key=lambda x: x["sira"])
    for x in satirlar:
        x.pop("sira")

    # Fiyatı güncelleyen paylaşımlar (kayıt yazanlar)
    kayit_saatleri = sorted({(saat, frozenset(g)) for t in KAYIT_TURLERI for saat, g in saatler.get(t, [])},
                            key=lambda x: x[0])
    if not kayit_saatleri:
        raise ProgramHatasi("Fiyat paylaşımı (reels/post) cron'u bulunamadı")
    fiyat_gunleri = set().union(*[g for _, g in kayit_saatleri])
    kayit_saat_listesi = [s for s, _ in kayit_saatleri]
    guncelleme = f"{gun_metni(fiyat_gunleri)} " + (kayit_saat_listesi[0] if len(kayit_saat_listesi) == 1
                                                   else ", ".join(kayit_saat_listesi[:-1]) + " ve " + kayit_saat_listesi[-1])

    # ECB: o gün (hafta sonuysa sıradaki iş günü) yayın saati; hangi paylaşım hangi günün kurunu kullanır
    ecb_gun = bugun
    while ecb_gun.weekday() >= 5:
        ecb_gun += timedelta(days=1)
    ecb_an, ecb_metin = ecb_saati(ecb_gun)
    ecb_dk = ecb_an.hour * 60 + ecb_an.minute
    once, sonra = [], []
    for saat in kayit_saat_listesi:
        hh, mm = int(saat[1:3]), int(saat[4:6])
        (sonra if hh * 60 + mm >= ecb_dk else once).append(saat)

    def birlestir(xs):
        return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " ve " + xs[-1]

    parcalar = []
    if once:
        parcalar.append(f"{birlestir(once)} değeri önceki iş gününün")
    if sonra:
        parcalar.append(f"{birlestir(sonra)} değeri o günün")
    ecb = {"saat": ecb_metin, "kullanim": ", ".join(parcalar) + " kurunu kullanır"}

    rehber_saat = next((s for s, _ in saatler.get("bilgi", [])), None)
    fiyat_ozet = {"Her gün": "her gün", "Hafta içi": "hafta içi her gün"}.get(
        gun_metni(fiyat_gunleri), gun_metni(fiyat_gunleri).lower())
    return {
        "fiyat_ozet": fiyat_ozet,
        "satirlar": satirlar,
        "guncelleme": guncelleme,
        "fiyat_gunleri": gun_metni(fiyat_gunleri),
        "son_deger_saati": kayit_saat_listesi[-1],
        "ecb": ecb,
        "rehber_saati": rehber_saat,
        "yorum": "yorum" in saatler,
        "rehber_hikaye": bool(rehber_hikaye),
    }


if __name__ == "__main__":
    import json
    p = program()
    print(json.dumps(p, ensure_ascii=False, indent=2))
