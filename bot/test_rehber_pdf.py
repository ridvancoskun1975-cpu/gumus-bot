"""PDF Gümüş Rehberi sınamaları (bot/rehber_pdf.py; Rıdvan, 19 Ekim 2026): baskı takvimi, sitedeki yakında/indirme
kartı, bölüm metinlerinin denetimi. Ağa çıkmaz, tarayıcı açmaz. Çalıştır: python bot/test_rehber_pdf.py"""
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehber_pdf as rp  # noqa: E402
import sayfa  # noqa: E402

gecen = 0


def kontrol(ad, kosul, ek=""):
    global gecen
    if not kosul:
        print("HATA", ad, ek)
        sys.exit(1)
    gecen += 1
    print("TAMAM", ad)


# Baskı takvimi: yılda bir, 1 Ocak (Rıdvan, 19 Ekim 2026: "1 yıl")
kontrol("sonraki baskı 1 Ocak 2027", rp.sonraki_baski(date(2026, 10, 19)) == date(2027, 1, 1))
kontrol("baskı günü sayılmaz, sonrakine geçer", rp.sonraki_baski(date(2027, 1, 1)) == date(2028, 1, 1))
kontrol("yıl içinde ara baskı yok", rp.sonraki_baski(date(2027, 6, 30)) == date(2028, 1, 1))
kontrol("baskı adı", rp.baski_adi(date(2027, 1, 1)) == "2027 baskısı")
kontrol("tarih eki", rp.tarih_bulunma(date(2027, 1, 1)) == "1 Ocak 2027'de" and rp.tarih_bulunma(date(2028, 1, 1)) == "1 Ocak 2028'de")

# Baskıya yalnız o günden önce Instagram'da yayımlanmış bölümler girer (#13 30 Aralık 2026, #14 6 Ocak 2027)
ilk = rp.baski_bolumleri(date(2027, 1, 1))
kontrol("1. baskı #1–#13", ilk == list(range(1, 14)), str(ilk))
kontrol("yayımlanmamış bölüm girmez", 14 not in ilk)

# Site kartı: baskı yokken yakında + geri sayım; tarih geçince tarihsiz; baskı varsa indirme
y = rp.site_durumu(date(2026, 10, 19))
kontrol("yakında, 74 gün", y["durum"] == "yakinda" and y["gun"] == 74 and y["tarih_metni"] == "1 Ocak 2027", str(y))
g = rp.site_durumu(date(2027, 1, 5))
kontrol("tarih geçti, baskı yok: eski tarih görünmez", g["durum"] == "yakinda" and g["tarih_metni"] is None and g["gun"] is None)

with tempfile.TemporaryDirectory() as d:
    yayin_eski, baskilar_eski = rp.YAYIN, list(rp.BASKILAR)
    rp.YAYIN = Path(d)
    (rp.YAYIN / "gumus-rehberi-2027.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    rp.BASKILAR[:] = [{"tarih": date(2027, 1, 1), "dosya": "gumus-rehberi-2027.pdf"}]
    try:
        kontrol("baskı tarihinden önce yine yakında", rp.site_durumu(date(2026, 12, 31))["durum"] == "yakinda")
        h = rp.site_durumu(date(2027, 1, 1))
        kontrol("baskı günü indirme", h["durum"] == "hazir" and h["baski"] == "2027 baskısı"
                and h["sonraki"] == "Ocak 2028" and h["boyut"].endswith("KB"), str(h))

        # Site üretimi: indirme kartı ve rehber.pdf sitenin kökünde
        with tempfile.TemporaryDirectory() as s:
            cikti = Path(s)
            simdi = sayfa.datetime(2027, 1, 4, 20, 30, tzinfo=sayfa.bot.TR_SAAT)
            sayfa.bot.gorsel_uret = lambda *a, **k: None   # tarayıcı açma
            sayfa.dar_sayfalar.uret = lambda *a, **k: ([], [])
            sayfa.uret(cikti, sayfa.ornek_gecmis(), simdi=simdi)
            kontrol("rehber.pdf kökte", (cikti / "rehber.pdf").read_bytes().startswith(b"%PDF"))
            r = (cikti / "rehber" / "index.html").read_text(encoding="utf-8")
            a = (cikti / "index.html").read_text(encoding="utf-8")
            kontrol("rehber sayfasında indirme düğmesi", 'href="../rehber.pdf" download' in r and "Yakında" not in r)
            kontrol("ana sayfada indirme kartı", 'href="rehber.pdf" download' in a)
            kontrol("site haritasında rehber.pdf", "/rehber.pdf</loc>" in (cikti / "sitemap.xml").read_text(encoding="utf-8"))
    finally:
        rp.YAYIN, rp.BASKILAR[:] = yayin_eski, baskilar_eski

with tempfile.TemporaryDirectory() as s:
    cikti = Path(s)
    simdi = sayfa.datetime(2026, 10, 19, 20, 30, tzinfo=sayfa.bot.TR_SAAT)
    sayfa.uret(cikti, sayfa.ornek_gecmis(), simdi=simdi)
    r = (cikti / "rehber" / "index.html").read_text(encoding="utf-8")
    a = (cikti / "index.html").read_text(encoding="utf-8")
    kontrol("rehber sayfasında yakında kartı", "Gümüşte uzmanlaşmanın kısa yolu" in r and "Ücretsiz PDF kitap · 1 Ocak 2027" in r
            and 'data-hedef="2027-01-01"' in r and ">74<" in r)
    kontrol("ana sayfada yakında kartı", "Gümüşte uzmanlaşmanın kısa yolu" in a and "1 Ocak 2027&#39;de" in a
            and 'href="rehber/#pdf"' in a)
    kontrol("henüz PDF yok", not (cikti / "rehber.pdf").exists())
    kontrol("site haritasında henüz PDF yok", "rehber.pdf" not in (cikti / "sitemap.xml").read_text(encoding="utf-8"))

# Baskı günleri sitede kendiliğinden güncellensin (sayfa.yml zamanlaması, TR 00:07)
akis = (rp.KOK / ".github/workflows/sayfa.yml").read_text(encoding="utf-8")
kontrol("sayfa.yml baskı günü zamanı (1 Ocak 00:07 TR)", "cron: '7 21 31 12 *'" in akis
        and len(re.findall(r"cron: '", akis)) == 1)

# Bölüm metinleri: hepsi denetimden geçmeli; onaylanmış örnek #2 var
kontrol("#2 uzun metni var", rp.bolum_dosyasi(2).exists())
kontrol("bütün bölüm metinleri ve DURUM.md denetimden geçiyor", rp.denetle(yazdir=False))
h, u, k = rp.parca_denetle(rp.bolum_dosyasi(2))
kontrol("#2 denetimi temiz", not h and 600 <= k <= 1500, f"{h} {k}")

# Denetim kötü parçayı yakalar
with tempfile.TemporaryDirectory() as d:
    kotu = Path(d) / "bolum-99.html"
    kotu.write_text('<p>giriş yok</p><h3>Başlık</h3><div style="color:red" class="uydurma">x</div> Claude', encoding="utf-8")
    h, _, _ = rp.parca_denetle(kotu)
    kontrol("izinsiz sınıf, satır içi stil, numarasız başlık, akılda kalsın yok, model adı",
            len(h) >= 5 and any("Claude" in x for x in h), str(h))

# DURUM.md (Rıdvan, 20 Ekim 2026): kitabın tek takip yeri; denetim gerçek durumla karşılaştırır
kontrol("DURUM.md gerçek durumla uyuşuyor", rp.durum_denetle() == [], str(rp.durum_denetle()))
gercek_durum = rp.DURUM.read_text(encoding="utf-8")
with tempfile.TemporaryDirectory() as d:
    durum_eski = rp.DURUM
    rp.DURUM = Path(d) / "DURUM.md"
    try:
        yok = re.search(r"^\| (\d+) \| ([^|]+) \| ([^|]+) \| yok \| kaynak — · denetle — \|", gercek_durum, re.M)

        def bozuk(eski, yeni):
            assert eski in gercek_durum, eski
            rp.DURUM.write_text(gercek_durum.replace(eski, yeni, 1), encoding="utf-8")
            return rp.durum_denetle()
        kontrol("var olan metne 'yok' denirse hata", any("'yok' diyor" in h for h in bozuk(
            "| 2 | Gram gümüş nasıl hesaplanır? | 13 Ekim 2026 | onaylandı |",
            "| 2 | Gram gümüş nasıl hesaplanır? | 13 Ekim 2026 | yok |")))
        if yok and not rp.bolum_dosyasi(int(yok.group(1))).exists():
            on = f"| {yok.group(1)} | {yok.group(2)} | {yok.group(3)} | "
            kontrol("olmayan metne 'onaylandı' denirse hata", any("'onaylandı' diyor" in h for h in bozuk(
                on + "yok | kaynak — · denetle — |", on + "onaylandı | kaynak ✓ · denetle ✓ |")))
        kontrol("yanlış Instagram tarihi hata", any("Instagram tarihi" in h for h in bozuk(
            "| 13 | Akçeden kuruşa: gümüş para | 30 Aralık 2026 |", "| 13 | Akçeden kuruşa: gümüş para | 6 Ocak 2027 |")))
        satir14 = re.search(r"^\| 14 \|.*\| 2028 \|$", gercek_durum, re.M).group(0)
        kontrol("yanlış baskı yılı hata", any("baskı" in h for h in bozuk(satir14, satir14[:-8] + "| 2027 |")))
        kontrol("eksik satır hata", any("#14: DURUM.md'de satırı yok" in h for h in bozuk(
            "| 14 | Gerçek gümüş nasıl anlaşılır? |", "| 99 | Gerçek gümüş nasıl anlaşılır? |")))
        # "yok" durumundaki bir satır (DURUM.md değiştikçe kayar; varsa sına)
        yok = re.search(r"^\| (\d+) \| ([^|]+) \| ([^|]+) \| yok \| kaynak — · denetle — \|", gercek_durum, re.M)
        if yok:
            on = f"| {yok.group(1)} | {yok.group(2)} | {yok.group(3)} | "
            kontrol("dalsız 'yazılıyor' hata", any("dal adı" in h for h in bozuk(on + "yok |", on + "yazılıyor |")))
            kontrol("olmayan metne 'denetle ✓' hata", any("kontrol ✓ olamaz" in h for h in bozuk(
                on + "yok | kaynak — · denetle — |", on + "yazılıyor · x | kaynak — · denetle ✓ |")))
        kontrol("denetle() uyuşmazlıkta False", (bozuk("| 2 | Gram gümüş nasıl hesaplanır? | 13 Ekim 2026 | onaylandı |",
                "| 2 | Gram gümüş nasıl hesaplanır? | 13 Ekim 2026 | yok |") and not rp.denetle(yazdir=False)))
    finally:
        rp.DURUM = durum_eski

# Eksik metinle kitap üretilmez
try:
    rp.kitap_verisi(date(2027, 1, 1), bolumler=[2, 98])
    kontrol("eksik metin hata verir", False)
except FileNotFoundError:
    kontrol("eksik metin hata verir", True)

print(f"\n{gecen} sınama geçti")
