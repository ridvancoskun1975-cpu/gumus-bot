# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""bot/vitrin.py sınaması: deneme Reels'i takvimi, bölüm seçimi, saat penceresi, açıklama."""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vitrin  # noqa: E402
import rapor  # noqa: E402

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: beklenen {b!r}, gelen {a!r}"
    gecen += 1


gunler = vitrin.gunler()
esit(len(gunler), 6, "3 hafta, haftada 2")
esit({g.weekday() for g in gunler}, {1, 3}, "salı ve perşembe")
esit(gunler[0], vitrin.BASLANGIC, "ilk gün")
esit(vitrin.gunun_bolumu(date(2026, 11, 18)), None, "çarşamba deneme günü değil")
esit(vitrin.gunun_bolumu(date(2026, 12, 8)), None, "dönem bitince yok")
secilen = [vitrin.gunun_bolumu(g) for g in gunler]
for g, no in zip(gunler, secilen):
    esit(no in vitrin.yayimlanmis(g), True, f"{g}: yalnız önceden yayımlanmış bölüm")
esit(len(set(secilen)), len(secilen), "dönemde aynı bölüm tekrar etmez")
TR = vitrin.TR
esit(vitrin.bugun(datetime(2026, 11, 17, 11, 20, tzinfo=TR)), secilen[0], "pencere içinde")
esit(vitrin.bugun(datetime(2026, 11, 17, 13, 30, tzinfo=TR)), None, "pencere dışında (GitHub geç başlattı)")
esit(vitrin.bugun(datetime(2026, 11, 17, 10, 0, tzinfo=TR)), None, "sabah paylaşımından önce değil")
esit(vitrin.DENEME_AYARI, {"graduation_strategy": "MANUAL"}, "takipçilere kendiliğinden açılmaz")

import bilgi  # noqa: E402
for no in range(1, len(bilgi.BOLUMLER) + 1):
    a = vitrin.aciklama(no, bilgi.BOLUMLER[no - 1], True)
    esit(len(a) <= 2000, True, f"#{no}: açıklama kısa ({len(a)})")
    esit(vitrin.ACIKLAMA_ISARETI in a, True, f"#{no}: rapor işareti")
esit(rapor.aciklamadan_ad({"caption": vitrin.aciklama(7, bilgi.BOLUMLER[6], False)}), "Deneme Reels'i",
     "raporda adıyla görünür")
print(f"test_vitrin: {gecen} sınama geçti")
