# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Yeniden üretilen bir paylaşımı, Instagram'a giden asıl paylaşımla karşılaştırır (#51).

Rıdvan, 23 Kasım 2026 19:55–19:56: geçmiş bir paylaşım yeniden üretilirse açıklaması o günün iş akışı günlüğündeki
metinle satır satır karşılaştırılır ("3- uygun", "tamam"). O gün Ekim aylığı yerelde yeniden çizilince "Son 1 yıl"
satırı (MetalCharts'tan canlı gelir, yerelde anahtar yok) sessizce eksik kalmıştı.

Yalnız etiketli veri satırları karşılaştırılır ("Son 1 yıl: …", "Dolar/TL: …"; etiket ": " öncesi, rakamsız, en çok
40 harf; "Son 1 yıl" gibi rakam içerebilir). Etiketsiz cümleler (kaynak, not) sayılmaz: sözleri sonradan kısalmış olabilir (#49).

Kullanım:
  python bot/karsilastir.py <çalıştırma_no> <yerel meta.json>
  python bot/karsilastir.py --yayin <metin dosyası> <yerel meta.json>
Çıkış kodu: 0 uyumlu, 1 eksik ya da farklı rakam var, 2 günlük okunamadı.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEPO = "ridvancoskun1975-cpu/gumus-bot"
RAKAM = re.compile(r"\d+(?:[.,]\d+)*")
ZAMAN = re.compile(r"^(?P<is>[^\t]+)\t[^\t]*\t(?P<zaman>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\.\d+Z ?(?P<metin>.*)$")
SON_SATIR = "Üretilen dosya:"


GUNLUK_ETIKETLERI = {"Başlık", "Üretilen dosya"}   # günlüğe yazılır, açıklamada yok


def etiket(satir):
    """"Son 1 yıl: ▲ %19,8 …" → "Son 1 yıl"; etiketsiz satır → None."""
    bas, ayrac, _ = satir.partition(": ")
    bas = bas.strip()
    if ayrac and 0 < len(bas) <= 40 and bas not in GUNLUK_ETIKETLERI:
        return bas
    return None


def veri_satirlari(metin):
    """{etiket: [rakamlar]} — yalnız etiketli ve rakam taşıyan satırlar."""
    sonuc = {}
    for satir in metin.splitlines():
        satir = satir.strip()
        e = etiket(satir)
        if e is None:
            continue
        rakamlar = RAKAM.findall(satir.partition(": ")[2])
        if rakamlar:
            sonuc.setdefault(e, rakamlar)
    return sonuc


def karsilastir(yayin, yerel):
    """(eksik, fazla, farkli): yayındaki ama yerelde olmayan satırlar, tersi, rakamı değişen satırlar."""
    a, b = veri_satirlari(yayin), veri_satirlari(yerel)
    eksik = [e for e in a if e not in b]
    fazla = [e for e in b if e not in a]
    farkli = [(e, a[e], b[e]) for e in a if e in b and a[e] != b[e]]
    return eksik, fazla, farkli


def gunlukten_aciklama(gunluk):
    """'uret' işinin günlüğünde açıklama, "Üretilen dosya:" satırıyla aynı saniyede yazılır; onu alır."""
    satirlar = [m.groupdict() for m in map(ZAMAN.match, gunluk.splitlines()) if m and m["is"] == "uret"]
    son = [s for s in satirlar if s["metin"].startswith(SON_SATIR)]
    if not son:
        return None
    bitis = len(satirlar) - 1 - satirlar[::-1].index(son[-1])
    zaman = son[-1]["zaman"]
    secili = [s["metin"] for s in satirlar[:bitis] if s["zaman"] == zaman]
    return "\n".join(secili)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("calistirma", nargs="?", help="paylas.yml çalıştırma numarası")
    p.add_argument("meta", help="yerel meta.json (bot/main.py hazirla çıktısı)")
    p.add_argument("--yayin", help="asıl açıklama metni dosyası (günlük yerine)")
    a = p.parse_args()
    yerel = json.loads(Path(a.meta).read_text(encoding="utf-8")).get("aciklama", "")
    if a.yayin:
        yayin = Path(a.yayin).read_text(encoding="utf-8")
    else:
        if not a.calistirma:
            p.error("çalıştırma numarası ya da --yayin gerekli")
        r = subprocess.run(["gh", "run", "view", a.calistirma, "-R", DEPO, "--log"],
                           capture_output=True, text=True)
        yayin = gunlukten_aciklama(r.stdout) if r.returncode == 0 else None
        if not yayin:
            print(f"Günlük okunamadı ya da açıklama bulunamadı (çalıştırma {a.calistirma}).")
            sys.exit(2)
    eksik, fazla, farkli = karsilastir(yayin, yerel)
    for e in eksik:
        print(f"EKSİK (paylaşımda var, yeniden üretilende yok): {e}")
    for e in fazla:
        print(f"FAZLA (yeniden üretilende var, paylaşımda yok): {e}")
    for e, x, y in farkli:
        print(f"FARKLI RAKAM: {e}: paylaşımda {' '.join(x)} · yeniden üretilende {' '.join(y)}")
    if eksik or farkli:
        print("Uyumsuz: Rıdvan'a göndermeden önce düzelt.")
        sys.exit(1)
    print("Uyumlu: rakam taşıyan satırlar aynı." + (" (Fazla satırlara bak.)" if fazla else ""))


if __name__ == "__main__":
    main()
