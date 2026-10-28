"""Paylaşım programı: "ne zaman ne paylaşılıyor" bilgisini elle yazmak yerine botun gerçek ayarlarından üretir.

Bilgi sayfasının her yeri her zaman güncel kalsın diye (Rıdvan, 14 Ekim 2026: "Bilgi sayfasının her yeri
her zaman güncel kalmalı.") sayfadaki saatler, günler ve takvim buradan gelir:
- saatler ve günler: .github/workflows/paylas.yml içindeki cron satırları ve "Türü belirle" adımındaki
  cron → tür eşlemesi (eşlemede olmayan cron reels'tir, iş akışındaki "else" gibi)
- rehber, rehber arşivi Reels'i ve aylık özet günleri: bot/bilgi.py → takvim(), arsiv_takvim(); bot/aylik.py
- haftalık kart günleri (ayrı paylaşım; Reels ve özete ek): bot/kart.py → KART_GUNLERI, KART_BASLANGIC
- hikâyeye de giden türler: bot/main.py → HIKAYE_TURLERI (rehber bölümleri her zaman hikâyeye de gider)
- ilk haftalık özet ve ilk pazar yorumu: günlük kayıtların başladığı güne göre (botun kendi kurallarıyla)
- ECB kurunun yayın saati: iş günleri 16:00 Frankfurt saati, o günün Türkiye karşılığı (yaz/kış saati)

Cron saatleri UTC'dir; Türkiye yıl boyu UTC+3.

Hedef saat (Rıdvan, 28 Ekim 2026: "takipçilere 20 00 yazdık … işleme önce başlamalıyız", "söze uymamız
gerekiyor"): GitHub zamanlı işleri 20–50 dk gecikmeli başlatıyordu (akşam özeti 20:17–20:50 arası gidiyordu).
Bu yüzden cron'lar hedeften ~40 dk önce (HEDEF_SAATLERI); iş akışı kurulumdan sonra `python bot/program.py bekle
<tür>` ile hedef saate kadar bekler (geçmişse beklemez), fiyatı o anda alır. Gösterilen saat = hedef + GECIKME_DK,
5 dakikaya yuvarlanmış ("~10:00"); hedefi olmayan bir cron için cron + GECIKME_ESKI_DK.
Yalnızca standart kütüphane ve botun kendi modülleri kullanılır.

Yerelde: python bot/program.py → bugünkü tabloyu yazdırır; python bot/program.py bekle post → hedefe kadar bekler.
"""
import os
import re
import sys
import time
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
# Hedef saatler (TR): zamanlı çalışma bu saate kadar bekler, fiyatı o anda alır; üretim + paylaşım ~3–5 dk
# sürer, paylaşım ~hedef + 5 dk'da görünür. Cron bundan ~40 dk önce olmalı (GitHub gecikmesi için).
# Tür iş akışının "Türü belirle" adımındaki türdür; bilgi cron'u rehber (bilgi), aylık özet (ay) ya da rehber
# arşivi (kisa) olabilir, üçü aynı hedefte. Burada olmayan tür (yasal, hikaye, tanitim, kart) beklemez.
HEDEF_SAATLERI = {
    "reels": (9, 55),    # hafta içi sabah Reels'i → ~10:00
    "post": (19, 55),    # hafta içi akşam özeti → ~20:00
    "bilgi": (13, 55),   # rehber günü → ~14:00
    "ay": (13, 55),      # aylık özet (rehbersiz ayın ilk iş günü) → ~14:00
    "kisa": (13, 55),    # rehber arşivi Reels'i → ~14:00
    "hafta": (9, 55),    # cumartesi haftalık özet → ~10:00
    "yorum": (10, 55),   # pazar yorumu → ~11:00
}
GECIKME_DK = 5                            # hedef saatten paylaşıma kadar geçen yaklaşık süre (üretim + paylaşım)
GECIKME_ESKI_DK = 10                      # hedefi olmayan cron için: cron saatinden paylaşıma kadar (eski kural)
EN_COK_BEKLEME_SN = 60 * 60               # güvenlik: hedef bundan uzaksa beklemeden devam (yanlış ayar koruması)
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
    "yorum": "Kısa ve orta vade üst düzey yapay zekâ yorumu",   # Rıdvan, 19 Ekim 2026: sitede "üst düzey"
    "bilgi": "Gümüş rehberi",
    "kisa": "Rehber Reels'i (önceki bölüm)",
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


def _yuvarla(toplam_dk):
    toplam = int(round(toplam_dk / 5.0)) * 5
    return f"~{(toplam // 60) % 24:02d}:{toplam % 60:02d}"


def yayin_saati(cron, tur=None):
    """"~10:00" — türün hedef saati + GECIKME_DK; hedefi yoksa cron saati + GECIKME_ESKI_DK (TR), 5 dk'ya yuvarlı."""
    if tur in HEDEF_SAATLERI:
        s, d = HEDEF_SAATLERI[tur]
        return _yuvarla(s * 60 + d + GECIKME_DK)
    (s, d), _ = cron_coz(cron)
    return _yuvarla(s * 60 + d + GECIKME_ESKI_DK)


def hedef_denetle(yol=None):
    """Hedefi olan her türün cron'u hedeften 10–60 dk önce olmalı (yoksa bekleme işe yaramaz ya da çok uzun).
    Sorun listesi döndürür (boşsa tamam)."""
    sorunlar = []
    for cron, tur in cronlar(yol):
        if tur not in HEDEF_SAATLERI:
            continue
        (s, d), _ = cron_coz(cron)
        hs, hd = HEDEF_SAATLERI[tur]
        fark = (hs * 60 + hd) - (s * 60 + d)
        if not 10 <= fark <= 60:
            sorunlar.append(f"{tur}: cron {s:02d}:{d:02d} TR, hedef {hs:02d}:{hd:02d}, fark {fark} dk (10–60 olmalı)")
    return sorunlar


def bekleme_suresi(tur, simdi=None):
    """Hedef saate kaç saniye var (TR). Hedefi olmayan tür, geçmiş hedef ya da EN_COK_BEKLEME_SN'den uzak hedef → 0."""
    if tur not in HEDEF_SAATLERI:
        return 0
    simdi = simdi or datetime.now(TR_SAAT)
    s, d = HEDEF_SAATLERI[tur]
    hedef = simdi.astimezone(TR_SAAT).replace(hour=s, minute=d, second=0, microsecond=0)
    kalan = (hedef - simdi).total_seconds()
    if kalan <= 0 or kalan > EN_COK_BEKLEME_SN:
        return 0
    return int(kalan)


def _yaz(*a):
    print(*a, flush=True)   # iş akışı günlüğünde bekleme ilerlemesi anında görünsün


def bekle(tur, simdi=None, uyu=time.sleep, yaz=_yaz):
    """Hedef saate kadar bekler, beklenen saniyeyi döndürür. Hiçbir durumda hata fırlatmaz (paylaşımı durdurmasın)."""
    try:
        simdi = simdi or datetime.now(TR_SAAT)
        sn = bekleme_suresi(tur, simdi)
        if tur not in HEDEF_SAATLERI:
            yaz(f"Bekleme yok: '{tur}' türünün hedef saati yok.")
            return 0
        s, d = HEDEF_SAATLERI[tur]
        if sn == 0:
            yaz(f"Bekleme yok: şu an {simdi.astimezone(TR_SAAT):%H:%M} TR, hedef {s:02d}:{d:02d} "
                f"(geçmiş ya da {EN_COK_BEKLEME_SN // 60} dk'dan uzak); hemen devam.")
            return 0
        yaz(f"Hedef saate kadar bekleniyor: şu an {simdi.astimezone(TR_SAAT):%H:%M} TR, hedef {s:02d}:{d:02d} "
            f"({sn // 60} dk {sn % 60} sn).")
        kalan = sn
        while kalan > 0:
            adim = min(kalan, 300)
            uyu(adim)
            kalan -= adim
            if kalan > 0:
                yaz(f"  … {kalan // 60} dk kaldı")
        yaz(f"Hedef saat geldi ({s:02d}:{d:02d} TR); devam.")
        return sn
    except Exception as hata:  # noqa: BLE001 — bekleme paylaşımı asla durdurmaz
        yaz(f"::warning::Hedef saat beklemesi atlandı ({hata!r}); hemen devam.")
        return 0


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


def aralik_metni(gunler):
    """Ardışık iş günleri: "19–21 Ekim her gün", araya hafta sonu girerse "14–21 Ekim hafta içi her gün",
    tek gün "21 Ekim Çarşamba"."""
    ilk, son = gunler[0], gunler[-1]
    if ilk == son:
        return tek_tarih(ilk)
    bas = f"{ilk.day}" if (ilk.year, ilk.month) == (son.year, son.month) else f"{ilk.day} {AYLAR[ilk.month - 1]}"
    hafta_sonu_var = any((ilk + timedelta(days=i)).weekday() >= 5 for i in range((son - ilk).days + 1))
    return f"{bas}–{son.day} {AYLAR[son.month - 1]} {'hafta içi her gün' if hafta_sonu_var else 'her gün'}"


def haftasi(gun):
    """O haftanın pazartesisi, "26 Ekim" ("26 Ekim haftasından itibaren")."""
    pzt = gun - timedelta(days=gun.weekday())
    return f"{pzt.day} {AYLAR[pzt.month - 1]}"


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
            yorum_reels=None, rehber_reels=None, pazar_hikaye=None):
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
            # Pazar yorumu 15 Ekim 2026'dan beri kaydırmalının yanında Reels (17 Ekim'den beri 24 sn) ve hikâye olarak da gider
            yorum_reels = getattr(bot, "YORUM_REELS", False)
    if pazar_hikaye is None:
        import main as bot
        # Pazar hikâyesi 25 Ekim 2026'dan beri kapalı (main.PAZAR_HIKAYE)
        pazar_hikaye = getattr(bot, "PAZAR_HIKAYE", True)
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
            ek = "Reels ve hikâye" if pazar_hikaye else "Reels"
            bicim = (f"{bicim}, {ek}" if pazar_hikaye else f"{bicim} ve {ek}") if bicim else ek
        elif tur in hikaye_turleri:
            bicim = f"{bicim} ve hikâye" if bicim else "hikâye"
        return f"{TUR_ADI.get(tur, tur)} ({bicim})" if bicim else TUR_ADI.get(tur, tur)

    satirlar, saatler = [], {}
    for cron, tur in cronlar():
        (s, d), gunler = cron_coz(cron)
        saat = yayin_saati(cron, tur)
        saatler.setdefault(tur, []).append((saat, gunler))
        sira = (min(gunler), s * 60 + d)
        if tur == "bilgi":
            # Bu çalışma rehber gününde rehberi, rehbersiz ayın ilk iş gününde aylık özeti paylaşır.
            # Rehber arşivi Reels'i de (19 Ekim 2026'dan beri haftalık rehber sırasında) bir rehber Reels'idir:
            # ziyaretçiye ayrı satır olarak değil, rehber günü olarak görünür.
            gelecek = [date.fromisoformat(g) for g in sorted({**bilgi.takvim(), **bilgi.arsiv_takvim()})
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
                        # Rıdvan, 18 Ekim 2026 ("1 uygun"): "21 Ekim'e kadar her gün, sonra salı ve perşembe"
                        # 22 Ekim perşembeyi de rehber günü gibi gösteriyordu; düzenli günler bilgi.DUZENLI_BASLANGIC
                        # haftasından başlar, ara günleri açıkça yazılır.
                        ekler.append(f"{aralik_metni(ilk_hafta)}, {haftasi(bilgi.DUZENLI_BASLANGIC)} "
                                     f"haftasından itibaren {duzenli}")
                ekler.append(f"sıradaki: {tarih_listesi(ilkler)}")
            else:
                zaman, ekler = f"{gun_metni(gunler)} {saat}", ["şimdilik sıradaki bölüm yok"]
            # Rıdvan, 18 Ekim 2026 ("5 çıkar"): "Öne çıkanlar › Rehber" notu ve rehber arşivi Reels'i günleri
            # ziyaretçiyi ilgilendirmeyen iç ayrıntı; ayrı yazılmaz (arşiv Reels'i rehber günlerinin içinde görünür).
            satirlar.append({"sira": sira, "zaman": zaman, "ne": ad("bilgi"), "ek": ekler})
            g_ay = siradaki_aylik(bugun, kayitlar)
            if g_ay:
                satirlar.append({"sira": (min(gunler), s * 60 + d + 1), "zaman": f"Ayın ilk iş günü {saat}",
                                 "ne": ad("ay"), "ek": [f"sıradaki: {tek_tarih(g_ay)}"]})
            continue
        ek = []
        if tur == "hafta":
            ilk = ilk_haftalik(bugun, kayitlar)
            sonraki_cmt = bugun + timedelta(days=(5 - bugun.weekday()) % 7)
            if ilk and ilk > sonraki_cmt:
                ek = [f"ilki {tek_tarih(ilk)} (önceki haftayla kıyaslamak için kayıt gerekiyor)"]
        elif tur == "kart":
            import kart
            if bugun < kart.KART_BASLANGIC:
                ek = [f"ilki {tek_tarih(kart.KART_BASLANGIC)}"]
        elif tur == "post" and tur in hikaye_turleri:
            # Günlük sınır (bot/sinir.py; Rıdvan, 19 Ekim 2026): gün 4'ü aşacaksa akşam özetinin hikâye kopyası düşer.
            # Sayfa her gün hikâye gidiyormuş gibi yazmasın; Rıdvan, 21 Ekim 2026 ("1"): "bazı günler" yerine günleri
            # yaz. Günler ayarlardan gelir: rehber hikâyesi otomatik gidiyorsa rehber günü (Reels + hikâye video),
            # aylık özet hikâyeye de gidiyorsa ayın ilk iş günü (aylık + hikâyesi) günü 4'e getirir.
            hikayesiz = []
            if rehber_hikaye:
                rg = bilgi.DUZENLI_GUNLER
                hikayesiz.append(f"{'rehber günü' if len(rg) == 1 else 'rehber günleri'} ({gun_metni(rg).lower()})")
            if "ay" in hikaye_turleri:
                hikayesiz.append("ayın ilk iş günü")
            if hikayesiz:
                ek = [" ve ".join(hikayesiz) + " hikâyesiz"]
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
    if len(sys.argv) >= 2 and sys.argv[1] == "bekle":
        # İş akışı: zamanlı çalışmada hedef saate kadar bekle. Çıkış kodu her zaman 0 (paylaşımı durdurmaz).
        tur_adi = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("TUR", "")
        bekle(tur_adi)
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "hedef-denetle":
        sorunlar = hedef_denetle()
        print("\n".join(sorunlar) if sorunlar else "Hedef saatler ve cron'lar uyumlu.")
        sys.exit(1 if sorunlar else 0)
    p = program()
    print(json.dumps(p, ensure_ascii=False, indent=2))
