"""PDF Gümüş Rehberi: Instagram rehber bölümlerinin uzun, eksiksiz hâllerini tek PDF kitapta toplar.

Rıdvan, 19 Ekim 2026: "gümüş rehberi pdf kitap yapsak"; "kısa olan bilgiler pdf te eksiksiz doyurucu olmalı";
önizlemeye "uygundur başlayalım. bunu site tanıtımına da ekleyelim. beklenti olsun."; güncelleme aralığı için
(3 ay önerilmişti) 22:34 "1 yıl".

- Bölüm metinleri: rehber_pdf/bolum-NN.html (yazım kuralları rehber_pdf/YAZIM.md). Yeni bölümün uzun hâli aylık
  rehber paketiyle birlikte yazılır ve aynı iki kontrolden geçer.
- Ekler: rehber_pdf/ek-<harf>.html (ilk satırdaki yorumda <!-- BAŞLIK: ... --> başlığı verir).
- Takip: rehber_pdf/DURUM.md, kitabın tek takip yeri (Rıdvan, 20 Ekim 2026). Her bölüm ve ek için bir satır: Instagram
  tarihi, uzun metin durumu, kontrol, baskı yılı. `denetle` dosyayı gerçek durumla karşılaştırır, uyuşmazlık hatadır.
- Baskı yılda bir, 1 Ocak'ta ("2027 baskısı"). Baskıya o günden önce Instagram'da yayımlanmış bölümler girer;
  yayımlanmamış bölüm girmez (Reels'in önüne geçmesin). Önizleme 25 Aralık'ta aylık paketle birlikte Rıdvan'a gider;
  onaylanan PDF rehber_pdf/yayin/ altına konur ve BASKILAR'a eklenir. Site o baskıyı tarihi gelince kendiliğinden
  yayınlar (gunlukgumus.com/rehber.pdf); yayınlanmış bir baskı yokken sitede "Yakında" tanıtımı görünür.

Komut satırı:
  python bot/rehber_pdf.py denetle                       → bütün bölüm metinlerini denetler (çıkış kodu 1: hata)
  python bot/rehber_pdf.py uret --cikti kitap.pdf [--tarih 2027-01-01] [--onizleme] [--bolumler 1,2]
  python bot/rehber_pdf.py durum [--tarih YYYY-AA-GG]    → sitedeki durum (yakında / hazır)
"""
import argparse
import re
import sys
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilgi  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
METINLER = KOK / "rehber_pdf"
YAYIN = METINLER / "yayin"
SABLONLAR = KOK / "templates"
TR_SAAT = ZoneInfo("Europe/Istanbul")
SITE_ADRES = "rehber.pdf"          # sitenin kökünde: gunlukgumus.com/rehber.pdf (adres hiç değişmez)
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# Sitedeki "Yakında" tanıtımının tarihi (Rıdvan, 19 Ekim 2026: "beklenti olsun"). İlk baskı bu gün yayınlanır.
ILK_BASKI = date(2027, 1, 1)
BASKI_AYLARI = (1,)   # yılda bir, 1 Ocak (Rıdvan, 19 Ekim 2026 22:34: "1 yıl")
# Onaylanmış baskılar, eskiden yeniye. Rıdvan onaylayınca (ya da paketteki 7 gün sessiz kabulden sonra) eklenir:
#   {"tarih": date(2027, 1, 1), "dosya": "gumus-rehberi-2027.pdf"}
# Dosya rehber_pdf/yayin/ altında durur; site, tarihi gelmiş en yeni baskıyı rehber.pdf olarak yayınlar.
BASKILAR = []

# Bölüm metinlerinde izin verilen yapı taşları (rehber_pdf/YAZIM.md). Şablonda stili olmayan sınıf kullanılmasın.
IZINLI = {
    "p": {"", "giris", "aciklama", "kaynaklar"},
    "div": {"formul-kutu", "etiket", "formul", "not", "parca", "rozet", "rozet koyu", "not-kutu", "deneme", "cevap",
            "akilda", "birlikte"},
    "span": {"", "num", "mono", "sabit", "aciklama"},
    "h3": {""}, "b": {""}, "strong": {""}, "i": {""}, "em": {""}, "br": {""}, "small": {""}, "sup": {""}, "sub": {""},
    "table": {"tablo", "izgara"}, "tr": {"", "son"}, "th": {"", "r", "kose", "satir"},
    "td": {"", "r", "adim", "merkez", "capraz"}, "thead": {""}, "tbody": {""},
    "ul": {"", "duz"}, "ol": {"hatalar"}, "li": {""},
}
EN_AZ_KELIME, EN_COK_KELIME = 600, 1500
DURUM = METINLER / "DURUM.md"
# DURUM.md'deki "Uzun metin" sütunu: yok | yazılıyor · <dal> | önizlemede · <dal> | onaylandı
DURUM_DALLI = ("yazılıyor", "önizlemede")


def bolum_dosyasi(no):
    return METINLER / f"bolum-{no:02d}.html"


def _ay_yil(g):
    return f"{AYLAR[g.month - 1]} {g.year}"


def tarih_metni(g):
    return f"{g.day} {AYLAR[g.month - 1]} {g.year}"


def baski_adi(tarih):
    """2027 baskısı"""
    return f"{tarih.year} baskısı"


def sonraki_baski(bugun):
    """bugun'den sonraki ilk baskı günü (her yıl 1 Ocak)."""
    for yil in (bugun.year, bugun.year + 1):
        for ay in BASKI_AYLARI:
            g = date(yil, ay, 1)
            if g > bugun:
                return g
    raise AssertionError("ulaşılamaz")


def baski_bolumleri(tarih):
    """Baskıya girecek bölümler: tarih'ten önce Instagram'da yayımlanmış olanlar, numaraya göre sıralı."""
    return sorted({no for gun, no in bilgi.yayim_listesi() if gun < tarih})


def eksik_metinler(tarih):
    """tarih'teki baskıya girmesi gereken ama uzun metni olmayan bölümler."""
    return [no for no in baski_bolumleri(tarih) if not bolum_dosyasi(no).exists()]


def yayindaki_baski(bugun):
    """Tarihi gelmiş ve dosyası duran en yeni baskı (yoksa None)."""
    uygun = [b for b in BASKILAR if b["tarih"] <= bugun and (YAYIN / b["dosya"]).exists()]
    return max(uygun, key=lambda b: b["tarih"]) if uygun else None


def _boyut_metni(bayt):
    mb = bayt / (1024 * 1024)
    return f"{mb:.1f} MB".replace(".", ",") if mb >= 1 else f"{max(1, round(bayt / 1024))} KB"


# Türkçe bulunma eki: "1 Ocak 2027'de" (yılın okunuşunun son hecesine göre; 2030 gibi sıfırla bitenler onlar
# basamağıyla değişir, yalnız 2027–2029 için doğrulandı)
_RAKAM_EKI = {"0": "'da", "1": "'de", "2": "'de", "3": "'te", "4": "'te", "5": "'te", "6": "'da", "7": "'de",
              "8": "'de", "9": "'da"}


def tarih_bulunma(g):
    """1 Ocak 2027'de"""
    return f"{tarih_metni(g)}{_RAKAM_EKI[str(g.year)[-1]]}"


def site_durumu(bugun):
    """Sitedeki PDF kartının verisi.
    hazir: yayınlanmış baskı var → indirme düğmesi. yakinda: yok → tanıtım (ilk baskıdan önce tarih ve geri sayımla;
    tarih geçtiyse ve baskı hâlâ yoksa tarihsiz "çok yakında", eski bir tarih görünmesin)."""
    b = yayindaki_baski(bugun)
    if b:
        dosya = YAYIN / b["dosya"]
        sonraki = sonraki_baski(bugun)
        return {"durum": "hazir", "adres": SITE_ADRES, "kaynak": str(dosya),
                "baski": baski_adi(b["tarih"]), "bolum": b.get("bolum"),
                "boyut": _boyut_metni(dosya.stat().st_size), "sonraki": _ay_yil(sonraki)}
    if bugun < ILK_BASKI:
        return {"durum": "yakinda", "tarih": ILK_BASKI.isoformat(), "tarih_metni": tarih_metni(ILK_BASKI),
                "tarih_bulunma": tarih_bulunma(ILK_BASKI), "gun": (ILK_BASKI - bugun).days}
    print("::warning::PDF rehber: tanıtım tarihi geçti ama yayınlanmış baskı yok (bot/rehber_pdf.py → BASKILAR); "
          "sitede tarihsiz 'yakında' görünüyor.")
    return {"durum": "yakinda", "tarih": None, "tarih_metni": None, "tarih_bulunma": None, "gun": None}


# ---------------------------------------------------------------- denetim

class _Denetci(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hatalar, self.metin, self.h3, self.akilda, self.giris = [], [], [], False, False
        self._h3_ac = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "style" in a:
            self.hatalar.append(f"<{tag}> satır içi stil kullanıyor")
        sinif = (a.get("class") or "").strip()
        if tag not in IZINLI:
            self.hatalar.append(f"izinsiz etiket <{tag}>")
        elif sinif not in IZINLI[tag]:
            self.hatalar.append(f"<{tag} class=\"{sinif}\"> izinli değil")
        if tag == "div" and sinif == "akilda":
            self.akilda = True
        if tag == "p" and sinif == "giris":
            self.giris = True
        if tag == "h3":
            self._h3_ac = True
            self.h3.append("")

    def handle_endtag(self, tag):
        if tag == "h3":
            self._h3_ac = False

    def handle_data(self, data):
        self.metin.append(data)
        if self._h3_ac:
            self.h3[-1] += data


def parca_denetle(yol):
    """Bir bölüm metnini denetler. (hatalar, uyarilar, kelime sayısı)"""
    ham = yol.read_text(encoding="utf-8")
    d = _Denetci()
    d.feed(ham)
    hatalar, uyarilar = list(d.hatalar), []
    kelime = len(re.findall(r"\w+", " ".join(d.metin)))
    if not d.giris:
        hatalar.append("giriş paragrafı (<p class=\"giris\">) yok")
    if not d.akilda:
        hatalar.append("AKILDA KALSIN kutusu (<div class=\"akilda\">) yok")
    numaralar = [re.match(r"\s*(\d+)", h) for h in d.h3]
    if any(m is None for m in numaralar):
        hatalar.append("numarasız alt başlık var (<h3><span class=\"num\">N</span>…)")
    elif [int(m.group(1)) for m in numaralar] != list(range(1, len(numaralar) + 1)):
        hatalar.append(f"alt başlık numaraları sırasız: {[int(m.group(1)) for m in numaralar]}")
    if not EN_AZ_KELIME <= kelime <= EN_COK_KELIME:
        uyarilar.append(f"{kelime} kelime (beklenen {EN_AZ_KELIME}–{EN_COK_KELIME})")
    if "<!-- KAYNAK:" not in ham and 'class="kaynaklar"' in ham:
        uyarilar.append("kaynak adresleri (<!-- KAYNAK: … -->) yok")
    for yasak in ("Anthropic", "Claude", "Gemini", "OpenAI", "ChatGPT"):
        if yasak in ham:
            hatalar.append(f"model/şirket adı geçiyor: {yasak}")
    if re.search(r"\b(alın|satın alın|fırsat|kaçırmayın)\b", " ".join(d.metin), re.I):
        uyarilar.append("yönlendirme gibi okunabilecek bir kelime var (yatırım tavsiyesi olmasın)")
    return hatalar, uyarilar, kelime


def denetle(yazdir=True):
    """Bütün bölüm ve ek metinlerini denetler; hata yoksa True."""
    tamam = True
    for yol in sorted(METINLER.glob("bolum-*.html")) + sorted(METINLER.glob("ek-*.html")):
        hatalar, uyarilar, kelime = parca_denetle(yol) if yol.name.startswith("bolum-") else (*_ek_denetle(yol), 0)
        tamam &= not hatalar
        if yazdir:
            durum = "HATA" if hatalar else ("uyarı" if uyarilar else "tamam")
            print(f"{yol.name}: {durum}" + (f" · {kelime} kelime" if kelime else ""))
            for h in hatalar:
                print(f"  ✗ {h}")
            for u in uyarilar:
                print(f"  ! {u}")
    durum_hatalari = durum_denetle()
    tamam &= not durum_hatalari
    if yazdir:
        print(f"DURUM.md: {'HATA' if durum_hatalari else 'gerçek durumla uyuşuyor'}")
        for h in durum_hatalari:
            print(f"  ✗ {h}")
    return tamam


def _durum_tablolari(metin):
    """DURUM.md'den {"bolum": [hücreler], "ek": [hücreler]} — "## Bölümler" ve "## Ekler" altındaki tablo satırları."""
    tablolar, bolum = {"bolum": [], "ek": []}, None
    for satir in metin.splitlines():
        if satir.startswith("## "):
            bolum = {"## Bölümler": "bolum", "## Ekler": "ek"}.get(satir.strip())
            continue
        if bolum and satir.startswith("|") and not re.match(r"^\|\s*-", satir):
            hucreler = [h.strip() for h in satir.strip().strip("|").split("|")]
            if hucreler[0] not in ("No", "Ek"):
                tablolar[bolum].append(hucreler)
    return tablolar


def _metin_durumu_denetle(ad, yol, durum, kontrol):
    """Bir bölüm/ek satırının "Uzun metin" ve "Kontrol" sütunlarını dosyanın gerçek hâliyle karşılaştırır."""
    hatalar, var = [], yol.exists()
    tur = durum.split("·")[0].strip()
    if tur not in ("yok", "onaylandı", *DURUM_DALLI):
        return [f"{ad}: uzun metin durumu anlaşılmadı: '{durum}' (yok / yazılıyor · dal / önizlemede · dal / onaylandı)"]
    if tur in DURUM_DALLI and not durum.partition("·")[2].strip():
        hatalar.append(f"{ad}: '{tur}' durumunda dal adı yazılmalı ('{tur} · <dal>')")
    if tur == "yok" and var:
        hatalar.append(f"{ad}: DURUM.md 'yok' diyor ama {yol.name} var")
    if tur == "onaylandı" and not var:
        hatalar.append(f"{ad}: DURUM.md 'onaylandı' diyor ama {yol.name} yok")
    m = re.fullmatch(r"kaynak (✓|—) · denetle (✓|—)", kontrol)
    if not m:
        return hatalar + [f"{ad}: kontrol sütunu anlaşılmadı: '{kontrol}' (kaynak ✓/— · denetle ✓/—)"]
    kaynak, denet = m.group(1) == "✓", m.group(2) == "✓"
    if tur == "onaylandı" and not (kaynak and denet):
        hatalar.append(f"{ad}: onaylanmış metnin iki kontrolü de ✓ olmalı")
    if not var:
        if kaynak or denet:
            hatalar.append(f"{ad}: {yol.name} bu dalda yok, kontrol ✓ olamaz")
        return hatalar
    ham = yol.read_text(encoding="utf-8")
    gercek = not (parca_denetle(yol)[0] if yol.name.startswith("bolum-") else _ek_denetle(yol)[0])
    if denet != gercek:
        hatalar.append(f"{ad}: DURUM.md 'denetle {m.group(2)}' diyor ama denetim {'geçiyor' if gercek else 'geçmiyor'}")
    if kaynak and 'class="kaynaklar"' in ham and ham.count("<!-- KAYNAK:") < 2:
        hatalar.append(f"{ad}: 'kaynak ✓' için dosyada en az iki <!-- KAYNAK: … --> adresi olmalı")
    return hatalar


def durum_denetle():
    """rehber_pdf/DURUM.md'yi gerçek durumla karşılaştırır (bölüm listesi, başlık, Instagram tarihi, baskı yılı,
    uzun metin dosyası, kontroller, ekler). Hata listesi döndürür; boşsa uyuşuyor."""
    if not DURUM.exists():
        return ["rehber_pdf/DURUM.md yok"]
    t = _durum_tablolari(DURUM.read_text(encoding="utf-8"))
    hatalar, gorulen = [], set()
    ilk_yayim = {}
    for gun, no in bilgi.yayim_listesi():
        ilk_yayim.setdefault(no, gun)
    for h in t["bolum"]:
        if len(h) != 6 or not h[0].lstrip("#").isdigit():
            hatalar.append(f"bölüm satırı okunamadı: {' | '.join(h)}")
            continue
        no = int(h[0].lstrip("#"))
        _, baslik, insta, durum, kontrol, baski = h
        ad = f"#{no}"
        if not 1 <= no <= len(bilgi.BOLUMLER):
            hatalar.append(f"{ad}: BOLUMLER'de böyle bir bölüm yok")
            continue
        if no in gorulen:
            hatalar.append(f"{ad}: iki satır var")
        gorulen.add(no)
        if baslik != bilgi.BOLUMLER[no - 1]["baslik"]:
            hatalar.append(f"{ad}: başlık '{baslik}', BOLUMLER'de '{bilgi.BOLUMLER[no - 1]['baslik']}'")
        gun = ilk_yayim.get(no)
        if insta != (tarih_metni(gun) if gun else "—"):
            hatalar.append(f"{ad}: Instagram tarihi '{insta}', takvimde '{tarih_metni(gun) if gun else '—'}'")
        beklenen_baski = str(sonraki_baski(gun).year) if gun else "—"
        if baski != beklenen_baski:
            hatalar.append(f"{ad}: baskı '{baski}', takvime göre '{beklenen_baski}'")
        hatalar += _metin_durumu_denetle(ad, bolum_dosyasi(no), durum, kontrol)
    for no in range(1, len(bilgi.BOLUMLER) + 1):
        if no not in gorulen:
            hatalar.append(f"#{no}: DURUM.md'de satırı yok")
    ek_dosyalar = {y.stem.split("-", 1)[1].upper(): y for y in sorted(METINLER.glob("ek-*.html"))}
    ek_gorulen = set()
    for h in t["ek"]:
        if len(h) != 5:
            hatalar.append(f"ek satırı okunamadı: {' | '.join(h)}")
            continue
        harf, baslik, durum, kontrol, baski = h
        if harf == "—":                      # "henüz ek yok" satırı
            if ek_dosyalar:
                hatalar.append("DURUM.md 'henüz ek yok' diyor ama ek dosyası var")
            continue
        ad, yol = f"Ek {harf}", METINLER / f"ek-{harf.lower()}.html"
        ek_gorulen.add(harf)
        if yol.exists() and baslik != _ek_basligi(yol):
            hatalar.append(f"{ad}: başlık '{baslik}', dosyada '{_ek_basligi(yol)}'")
        if not re.fullmatch(r"\d{4}", baski):
            hatalar.append(f"{ad}: baskı yılı yazılmalı (ör. 2027)")
        hatalar += _metin_durumu_denetle(ad, yol, durum, kontrol)
    for harf in ek_dosyalar:
        if harf not in ek_gorulen:
            hatalar.append(f"Ek {harf}: DURUM.md'de satırı yok")
    if not t["ek"]:
        hatalar.append("DURUM.md'de Ekler tablosu boş (ek yoksa '— | henüz ek yok' satırı)")
    return hatalar


def _ek_denetle(yol):
    d = _Denetci()
    d.feed(yol.read_text(encoding="utf-8"))
    hatalar = list(d.hatalar)
    if not _ek_basligi(yol):
        hatalar.append("başlık yorumu (<!-- BAŞLIK: … -->) yok")
    return hatalar, []


def _ek_basligi(yol):
    m = re.search(r"<!--\s*BAŞLIK:\s*(.+?)\s*-->", yol.read_text(encoding="utf-8"))
    return m.group(1) if m else None


# ---------------------------------------------------------------- üretim

def kitap_verisi(tarih, onizleme=False, bolumler=None):
    from markupsafe import Markup

    nolar = bolumler or baski_bolumleri(tarih)
    eksik = [no for no in nolar if not bolum_dosyasi(no).exists()]
    if eksik:
        raise FileNotFoundError(f"uzun metni olmayan bölümler: {', '.join(f'#{n}' for n in eksik)}")
    liste = [{"no": no, "baslik": bilgi.BOLUMLER[no - 1]["baslik"],
              "metin": Markup(bolum_dosyasi(no).read_text(encoding="utf-8"))} for no in nolar]
    ekler = []
    for yol in sorted(METINLER.glob("ek-*.html")):
        ekler.append({"harf": yol.stem.split("-", 1)[1].upper(), "baslik": _ek_basligi(yol) or yol.stem,
                      "metin": Markup(yol.read_text(encoding="utf-8"))})
    goril_yol = SABLONLAR / "goril" / "istif.svg"
    return {"baski": {"ad": baski_adi(tarih), "yil": tarih.year},
            "bolumler": liste, "ekler": ekler, "onizleme": onizleme,
            "goril": Markup(goril_yol.read_text(encoding="utf-8")) if goril_yol.exists() else None,
            "site": bilgi.SITE, "hesap": "@gunlukgumus"}


def uret(cikti, tarih, onizleme=False, bolumler=None):
    """Kitabı PDF olarak üretir; sayfa sayısını döndürür."""
    import os
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    v = kitap_verisi(tarih, onizleme, bolumler)
    env = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True)
    gecici = SABLONLAR / "_cikti_rehber_pdf.html"     # yazı tipleri göreli yolla (../assets/fonts) yüklensin
    gecici.write_text(env.get_template("rehber-pdf.html").render(**v), encoding="utf-8")
    cikti = Path(cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            kw = {"executable_path": os.environ["CHROME_YOLU"]} if os.environ.get("CHROME_YOLU") else {}
            tarayici = p.chromium.launch(**kw)
            s = tarayici.new_page()
            s.goto(gecici.as_uri(), wait_until="load")
            s.evaluate("document.fonts.ready")
            s.wait_for_timeout(300)
            s.pdf(path=str(cikti), prefer_css_page_size=True, print_background=True,
                  tagged=True, outline=True)
            tarayici.close()
    finally:
        gecici.unlink(missing_ok=True)
    return len(re.findall(rb"/Type\s*/Page[^s]", cikti.read_bytes()))


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("denetle")
    u = alt.add_parser("uret")
    u.add_argument("--cikti", required=True)
    u.add_argument("--tarih", help="baskı tarihi (YYYY-AA-GG); verilmezse bir sonraki baskı günü")
    u.add_argument("--onizleme", action="store_true", help="kapakta ve sayfa başında ÖNİZLEME damgası")
    u.add_argument("--bolumler", help="yalnız bu bölümler (ör. 1,2,3); verilmezse tarihten önce yayımlananlar")
    d = alt.add_parser("durum")
    d.add_argument("--tarih")
    a = ap.parse_args()

    bugun = datetime.now(TR_SAAT).date()
    if a.komut == "denetle":
        sys.exit(0 if denetle() else 1)
    if a.komut == "durum":
        print(site_durumu(date.fromisoformat(a.tarih) if a.tarih else bugun))
        return
    tarih = date.fromisoformat(a.tarih) if a.tarih else sonraki_baski(bugun)
    nolar = [int(x) for x in a.bolumler.split(",")] if a.bolumler else None
    if not nolar:
        eksik = eksik_metinler(tarih)
        if eksik:
            print(f"::error::{tarih_metni(tarih)} baskısı için uzun metni olmayan bölümler: "
                  + ", ".join(f"#{n}" for n in eksik))
            sys.exit(1)
    if not denetle(yazdir=False):
        denetle()
        sys.exit(1)
    sayfa = uret(a.cikti, tarih, a.onizleme, nolar)
    print(f"PDF rehber üretildi: {a.cikti} ({sayfa} sayfa, {baski_adi(tarih)}, "
          f"{len(nolar or baski_bolumleri(tarih))} bölüm)")


if __name__ == "__main__":
    main()
