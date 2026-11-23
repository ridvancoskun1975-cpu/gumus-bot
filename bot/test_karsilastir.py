# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""bot/karsilastir.py sınaması (#51): yeniden üretilen paylaşımda eksik veri satırı yakalanmalı.

Çalıştır: python bot/test_karsilastir.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import karsilastir as k  # noqa: E402

# 2 Kasım 2026 aylık özetinin (çalıştırma 41433571084) açıklamasından kısaltılmış örnek
YAYIN = """Gümüş 13 Ekim'den bu yana %15,8 düştü: gram gümüş ekim sonunda 79,07 ₺
Aylık gümüş özeti · Ekim 2026 (13–30 Ekim)
Ayın kaynağı: ons gümüş ▼ %16,8 · dolar/TL ▲ %1,2
Son 1 yıl: ▲ %19,8 (30 Ekim 2025: 65,98 ₺)

Ayın en yükseği: 93,88 ₺ (13 Ekim) · en düşüğü: 79,07 ₺ (30 Ekim)
Dolar/TL: 49,95 ₺ (▲ %1,17)
Günlük değerler iş günlerinin son paylaşımına (yaklaşık 20:00) aittir; kayıtlar 13 Ekim tarihinde başladığı için.
Gram fiyatı ons gümüş × dolar/TL ÷ 31,1035 ile hesaplanmıştır.
#gümüş #gramgümüş"""

# Aynı ay, yerelde yeniden üretilmiş; "Son 1 yıl" satırı yok, açıklama cümleleri kısalmış (#49)
YEREL = """Gümüş 13 Ekim'den bu yana %15,8 düştü: gram gümüş ekim sonunda 79,07 ₺
Aylık gümüş özeti · Ekim 2026 (13–30 Ekim)
Ayın kaynağı: ons gümüş ▼ %16,8 · dolar/TL ▲ %1,2

Ayın en yükseği: 93,88 ₺ (13 Ekim) · en düşüğü: 79,07 ₺ (30 Ekim)
Dolar/TL: 49,95 ₺ (▲ %1,17)
Günlük değerler iş günlerinin ~20:00 değerleridir; kayıtlar 13 Ekim tarihinde başladığı için.
Gram fiyatı = ons gümüş × dolar/TL ÷ 31,1035; kuyumcu ve banka fiyatından farklı olabilir.
#gümüş"""

hatalar = []


def bekle(kosul, mesaj):
    if not kosul:
        hatalar.append(mesaj)


# 1) Eksik veri satırı yakalanır; sözü değişen etiketsiz cümleler sayılmaz
eksik, fazla, farkli = k.karsilastir(YAYIN, YEREL)
bekle(eksik == ["Son 1 yıl"], f"eksik yalnız 'Son 1 yıl' olmalı: {eksik}")
bekle(not farkli, f"farklı rakam olmamalı: {farkli}")
bekle(not fazla, f"fazla satır olmamalı: {fazla}")

# 2) Satır eklenince uyumlu
yerel2 = YEREL.replace("Dolar/TL: 49,95", "Son 1 yıl: ▲ %19,8 (30 Ekim 2025: 65,98 ₺)\nDolar/TL: 49,95")
bekle(k.karsilastir(YAYIN, yerel2) == ([], [], []), "satır eklenince uyumlu olmalı")

# 3) Rakam farkı yakalanır
yerel3 = yerel2.replace("49,95", "49,96")
_, _, farkli3 = k.karsilastir(YAYIN, yerel3)
bekle([e for e, _, _ in farkli3] == ["Dolar/TL"], f"Dolar/TL rakam farkı yakalanmalı: {farkli3}")

# 4) Günlükten açıklama: yalnız "uret" işi, "Üretilen dosya" ile aynı saniyede ve ondan önce yazılanlar
GUNLUK = "\n".join([
    "kontrol\tUNKNOWN STEP\t2026-11-02T11:02:42.7625599Z Bugün (TR) takipçinin gördüğü içerik: 1",
    "uret\tUNKNOWN STEP\t2026-11-02T11:03:40.1000000Z Ayın kaynağı: ons gümüş ▼ %99,9",
    "uret\tUNKNOWN STEP\t2026-11-02T11:03:44.4242167Z Son 1 yıl: ▲ %19,8 (30 Ekim 2025: 65,98 ₺)",
    "uret\tUNKNOWN STEP\t2026-11-02T11:03:44.4250000Z Dolar/TL: 49,95 ₺ (▲ %1,17)",
    "uret\tUNKNOWN STEP\t2026-11-02T11:03:44.4260209Z Üretilen dosya: /home/runner/site/ay-20261102-1403.mp4",
    "uret\tUNKNOWN STEP\t2026-11-02T11:03:44.9000000Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.15/x64",
])
metin = k.gunlukten_aciklama(GUNLUK)
bekle(metin is not None and "Son 1 yıl" in metin and "Dolar/TL" in metin, f"açıklama alınmalı: {metin!r}")
bekle(metin is not None and "99,9" not in metin and "pythonLocation" not in metin,
      f"başka saniye ve sonraki satırlar alınmamalı: {metin!r}")
bekle(k.gunlukten_aciklama("uret\tx\t2026-11-02T11:03:44.1Z merhaba") is None, "Üretilen dosya yoksa None")

if hatalar:
    print("BAŞARISIZ:\n- " + "\n- ".join(hatalar))
    sys.exit(1)
print("karsilastir: bütün sınamalar geçti")
