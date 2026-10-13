"""Aylık özetin günü: ayın rehber gönderisi olmayan ilk iş günü, ~14:00 (rehberle aynı saat).

Aylık özet hafta içi 13:50 TR çalışmasını (bilgi cron'u) kullanır: o gün takvimde rehber
bölümü varsa rehber gider, yoksa ve bugün ayın rehbersiz ilk iş günüyse aylık özet gider.
Böylece aylık özet olan gün de en fazla 3 paylaşım olur (10:00, ~14:00, 20:00).
Yalnızca standart kütüphane kullanır ("kontrol" işi paket kurmadan çağırır).

Komut satırı: python bot/aylik.py bugun → bugün aylık özet günüyse "ay" yazar, değilse boş
              python bot/aylik.py gunler 2026 → o yılın aylık özet günlerini listeler
"""
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import bilgi  # noqa: E402

ILK_AY = date(2026, 11, 1)   # ilk aylık özet Kasım başında (Ekim, kayıtlar 13 Ekim'de başladığı için kısmi)


def ozet_gunu(yil, ay):
    """O ayın aylık özet günü: rehber gönderisi olmayan ilk iş günü."""
    takvim = bilgi.takvim()
    gun = date(yil, ay, 1)
    while gun.weekday() >= 5 or gun.isoformat() in takvim:
        gun += timedelta(days=1)
    return gun


def bugun_mu(gun=None):
    gun = gun or datetime.now(ZoneInfo("Europe/Istanbul")).date()
    return gun >= ILK_AY and gun == ozet_gunu(gun.year, gun.month)


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "bugun"
    if komut == "gunler":
        yil = int(sys.argv[2]) if len(sys.argv) > 2 else date.today().year
        for ay in range(1, 13):
            g = ozet_gunu(yil, ay)
            print(g, bilgi.GUNLER[g.weekday()])
    else:
        print("ay" if bugun_mu() else "")
