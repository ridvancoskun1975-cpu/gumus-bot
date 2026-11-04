# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Telif notu: depodaki her kod ve şablon dosyasının başında "Tüm hakları saklıdır" satırı.

Rıdvan, 5 Kasım 2026: "Herkesin görebileceği ve kaçıramayacağı her yere ekle." Ayrıntılı metin LICENSE'ta, kısa
hâli README'nin başında. Satır yalnızca yorumdur; görselleri, videoları, siteyi ve PDF'i değiştirmez:
- .py .yml .sh → `# …` (shebang varsa ondan sonra)
- .js .css .gs → `/* … */`
- templates/*.html (Jinja) → `{#- … -#}` (çıktıya hiçbir şey yazmaz, ardındaki satır sonunu da yutar)
- rehber_pdf/*.html (PDF'e ham eklenen parçalar) ve .svg → `<!-- … -->`
JSON, Markdown, yazı tipi, müzik ve lisans dosyalarına dokunulmaz (DURUM.md'yi rehber_pdf.py okur).

Yeni dosya eklenince: python bot/telif.py ekle · Denetim: python bot/telif.py denetle (ya da bot/test_telif.py)
"""
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
ISARET = "Tüm hakları saklıdır"
METIN = ("© 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. "
         "İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE")
PDF_EK = " Yayımlanan PDF baskısı: CC BY-NC-ND 4.0."
BAKILAN_SATIR = 3   # işaret ilk bu kadar satırda aranır


BASLANGIC_YILI = 2026


def yil_metni(simdi=None):
    """Sitenin alt satırındaki yıl: 2026'da "2026", sonra "2026–2027" gibi (kendiliğinden ilerler)."""
    from datetime import datetime
    yil = (simdi or datetime.now()).year
    return str(BASLANGIC_YILI) if yil <= BASLANGIC_YILI else f"{BASLANGIC_YILI}–{yil}"


def satir(yol):
    """Dosyanın türüne göre telif satırı; başlık konmayacak dosyada None."""
    yol = Path(yol)
    uz = yol.suffix.lower()
    parcalar = yol.as_posix().split("/")
    if yol.name.startswith("_"):   # üretim sırasında yazılan geçici dosyalar (ör. templates/_hareket_*.html)
        return None
    if uz in (".py", ".yml", ".yaml", ".sh"):
        return f"# {METIN}"
    if uz in (".js", ".css", ".gs"):
        return f"/* {METIN} */"
    if uz == ".svg":
        return f"<!-- {METIN} -->"
    if uz == ".html":
        if "rehber_pdf" in parcalar:
            return f"<!-- {METIN}{PDF_EK} -->"
        if "templates" in parcalar:
            return "{#- " + METIN + " -#}"
    return None


def dosyalar():
    """git'in izlediği, başlık konacak dosyalar."""
    cikti = subprocess.run(["git", "ls-files"], cwd=KOK, capture_output=True, text=True, check=True).stdout
    return [KOK / y for y in cikti.splitlines() if satir(y)]


def var_mi(metin):
    return ISARET in "\n".join(metin.splitlines()[:BAKILAN_SATIR])


def ekle_metne(yol, metin):
    """Satırı metnin başına (shebang varsa ondan sonraya) ekler; zaten varsa metni değiştirmez."""
    if var_mi(metin):
        return metin
    s = satir(yol)
    if metin.startswith("#!"):
        ilk, _, kalan = metin.partition("\n")
        return f"{ilk}\n{s}\n{kalan}"
    return f"{s}\n{metin}"


def ekle():
    eklenen = 0
    for yol in dosyalar():
        eski = yol.read_text(encoding="utf-8")
        yeni = ekle_metne(yol.relative_to(KOK), eski)
        if yeni != eski:
            yol.write_text(yeni, encoding="utf-8")
            eklenen += 1
    print(f"Telif satırı eklenen dosya: {eklenen}")
    return eklenen


def eksikler():
    return [yol.relative_to(KOK).as_posix() for yol in dosyalar()
            if not var_mi(yol.read_text(encoding="utf-8"))]


def denetle():
    sorun = [f"başlıksız: {y}" for y in eksikler()]
    if not (KOK / "LICENSE").exists() or ISARET.upper() not in (KOK / "LICENSE").read_text(encoding="utf-8"):
        sorun.append("LICENSE yok ya da 'TÜM HAKLARI SAKLIDIR' yazmıyor")
    readme = (KOK / "README.md").read_text(encoding="utf-8").splitlines()[:6]
    if not any("TÜM HAKLARI SAKLIDIR" in s for s in readme):
        sorun.append("README.md'nin başında telif notu yok")
    for s in sorun:
        print(f"✗ {s}")
    print("Telif notu: tamam" if not sorun else f"Telif notu: {len(sorun)} sorun (düzeltmek: python bot/telif.py ekle)")
    return not sorun


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "denetle"
    if komut == "ekle":
        ekle()
    sys.exit(0 if denetle() else 1)
