"""Dolar/TL kurunun yedek yolları (bot/main.py → kurlar, ecb_xml_kurlari, kayitli_kurlar). Ağ yok.
Çalıştır: python bot/test_kur_yedek.py

4 Kasım 2026: Frankfurter 522 verdi; paylaşmayan akşam özeti denemesi "Dolar/TL kuru alınamadı" ile durdu. Akşam
özeti (taahhüt: hafta içi her gün 2 kez gram fiyatı) tek bir kur aracına bağlı kalmasın diye ECB'nin kendi dosyası ve
botun son kaydı yedek yol oldu.
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main as bot  # noqa: E402
import requests  # noqa: E402

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


bugun = datetime.now(bot.TR_SAAT).date()
d1, d2 = (bugun - timedelta(days=1)).isoformat(), (bugun - timedelta(days=2)).isoformat()
XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
<gesmes:subject>Reference rates</gesmes:subject>
<Cube>
<Cube time="{d1}"><Cube currency="USD" rate="1.1500"/><Cube currency="TRY" rate="57.5000"/></Cube>
<Cube time="{d2}"><Cube currency="USD" rate="1.1600"/><Cube currency="TRY" rate="57.9420"/></Cube>
</Cube></gesmes:Envelope>""".encode()

(t1, k1), (t2, k2) = bot.ecb_xml_kurlari(XML)
esit((t1.isoformat(), k1), (d1, 50.0), "ECB dosyası: son kur TRY ÷ USD")
esit((t2.isoformat(), k2), (d2, round(57.942 / 1.16, 5)), "ECB dosyası: önceki kur")
eski = XML.replace(d1.encode(), b"2020-01-02").replace(d2.encode(), b"2020-01-01")
try:
    bot.ecb_xml_kurlari(eski)
    esit(True, False, "eski ECB dosyası reddedilir")
except ValueError:
    esit(True, True, "eski ECB dosyası reddedilir")

kayit = {d2: {"dolar": 49.97, "kur_tarihi": d2}, d1: {"dolar": 50.0, "kur_tarihi": d1}}
esit(bot.kayitli_kurlar(kayit), ((date.fromisoformat(d1), 50.0), (date.fromisoformat(d2), 49.97)),
     "kayıtlardan son iki ECB tarihi")
gun_ici = {"gunler": {bugun.isoformat(): [{"dolar": 50.1, "kur_tarihi": bugun.isoformat()}]}}
esit(bot.kayitli_kurlar(kayit, gun_ici)[0], (bugun, 50.1), "gün içi noktadaki daha yeni kur da sayılır")
esit(bot.kayitli_kurlar({d1: {"dolar": 50.0, "kur_tarihi": d1}}), None, "tek kur yetmez")
esit(bot.kayitli_kurlar({"2020-01-01": {"dolar": 7, "kur_tarihi": "2020-01-01"},
                         "2020-01-02": {"dolar": 7.1, "kur_tarihi": "2020-01-02"}}), None, "eski kayıt kullanılmaz")


class Yanit:
    def __init__(self, kod, json_=None, icerik=b""):
        self.status_code, self._json, self.content = kod, json_, icerik

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error")

    def json(self):
        return self._json


def calistir(frankfurter, ecb, kayitlar):
    def get(url, **kw):
        if url == bot.KUR_URL:
            return frankfurter()
        if url == bot.ECB_XML_URL:
            return ecb()
        raise AssertionError(url)
    asil = (bot.requests.get, bot._bekle, bot.gecmis_oku, bot.gun_ici_oku, bot.KUR_ARACI[0])
    bot.requests.get, bot._bekle = get, lambda d: None
    bot.gecmis_oku, bot.gun_ici_oku = (lambda: kayitlar), (lambda: {})
    try:
        return bot.kurlar(), bot.KUR_ARACI[0]
    finally:
        bot.requests.get, bot._bekle, bot.gecmis_oku, bot.gun_ici_oku, bot.KUR_ARACI[0] = asil


tamam = lambda: Yanit(200, [{"date": d2, "quote": "TRY", "rate": 49.9}, {"date": d1, "quote": "TRY", "rate": 50.2}])
coktu = lambda: Yanit(522)
ecb_iyi = lambda: Yanit(200, icerik=XML)


def ecb_kotu():
    raise requests.ConnectionError("bağlantı yok")


(s, o), arac = calistir(tamam, ecb_kotu, {})
esit((s, arac), ((date.fromisoformat(d1), 50.2), "Frankfurter (frankfurter.dev) üzerinden"), "olağan yol değişmedi")
(s, o), arac = calistir(coktu, ecb_iyi, {})
esit(s, (date.fromisoformat(d1), 50.0), "Frankfurter 522 → ECB dosyası")
esit("ECB'nin kendi sitesinden" in arac, True, "açıklamadaki kaynak satırı ECB'yi söyler")
(s, o), arac = calistir(coktu, ecb_kotu, kayit)
esit(s, (date.fromisoformat(d1), 50.0), "ikisi de yoksa botun son kaydı")
esit("botun son kaydından" in arac, True, "açıklamada son kayıt olduğu yazar")
try:
    calistir(coktu, ecb_kotu, {})
    esit(True, False, "hiçbir yol yoksa hata")
except RuntimeError as e:
    esit("Dolar/TL kuru alınamadı" in str(e), True, "hiçbir yol yoksa hata")
esit(bot.KUR_ARACI[0], "Frankfurter (frankfurter.dev) üzerinden", "sınamalar kaynak satırını geri bırakır")
esit("{KUR_ARACI[0]}" in Path(bot.__file__).read_text(encoding="utf-8"), True, "kaynak satırı KUR_ARACI'ndan")

print(f"test_kur_yedek: {gecen} sınama geçti.")
