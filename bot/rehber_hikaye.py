"""Gümüş rehberi bölümünün 9:16 hikâye kareleri (templates/rehber-hikaye.html) ve hikâye videosu.

Bot rehber gönderisinden (kaydırmalı) hemen sonra aynı bölümü hikâyeye de koyar: kareler tek tek değil,
tek bir müzikli video olarak (14 Ekim 2026, Rıdvan: kapak 3 sn, her kare 6 sn; hikâye kalabalık olmasın).
Rıdvan bu videoyu profildeki "Rehber" öne çıkanına ekler (Instagram API öne çıkanları yönetmeye izin
vermiyor). Öne çıkan, Instagram'ın 2023'te kaldırdığı "Rehberler" bölümünün yerini tutar: bütün bölümler
bir başlık altında, sırayla okunur. Bir hikâye en çok 60 sn olabildiği için uzun bölüm kareler arasından
eşit parçalara bölünür (video_parcalari).

Kare sayısı içeriğe göre değişir (Rıdvan, 14 Ekim 2026: "İçerik okunaklı olmalı. İçeriğe göre kare
sayısı artabilir ya da azalır."):
- Kapak her zaman ayrı karedir.
- Her sayfa yeni karede başlar; ancak bir sayfa o anki karenin kalan boşluğuna bütünüyle sığarsa
  aynı karede devam eder (kısa sayfalar birleşir, kare sayısı azalır).
- Sığmayan sayfa öğe öğe (büyük sayı, formül, tablo satırı, madde) sonraki karelere bölünür; devam
  karesinin başında "01 · Troy ons (devam)" satırı çıkar. Başlık, ilk öğesinden ayrılmaz.
- "Sığar mı?" sorusu tahminle değil, kare tarayıcıda gerçekten çizilerek yanıtlanır (yazı tipi ve
  satır kırılması dahil); yatay taşma (sığmayan rakam, formül) da taşma sayılır.

Yerelde: python bot/main.py hazirla --tur hikaye --konu 3 --cikti <klasör>
"""
import os
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
SABLONLAR = KOK / "templates"
SABLON = "rehber-hikaye.html"
BOYUT = (1080, 1920)

OLC_JS = """() => {
  const g = document.querySelector('.govde'), i = document.querySelector('.icerik');
  if (i.getBoundingClientRect().height > g.clientHeight + 1) return false;
  for (const e of document.querySelectorAll('.icerik, .icerik *')) {
    if (e.clientWidth && e.scrollWidth > e.clientWidth + 1) return false;
  }
  return true;
}"""


# Hikâye videosu (14 Ekim 2026, Rıdvan: "kapak 3 saniye, her kare için 6 sn yeterli", müzikli).
KAPAK_SN = 3
KARE_SN = 6
HIKAYE_EN_UZUN_SN = 60     # Instagram'da tek hikâyenin en uzun süresi


def kare_suresi(sira):
    """Videoda karenin ekranda kalma süresi (sn); sıra 0 = kapak."""
    return KAPAK_SN if sira == 0 else KARE_SN


def video_parcalari(n, en_uzun=HIKAYE_EN_UZUN_SN):
    """n kareli bölümü (ilki kapak) hikâye videolarına böler: [[kare sıraları (0'dan)], ...].

    Her video en_uzun saniyeyi aşmaz; kesim her zaman kare sınırında olur (bir kare iki videoya
    bölünmez); gerekirse parça sayısı en aza indirilir ve kareler parçalara olabildiğince eşit dağılır."""
    if n < 1:
        return []
    sureler = [kare_suresi(i) for i in range(n)]
    if max(sureler) > en_uzun:
        raise ValueError(f"Bir kare tek başına {en_uzun} sn'yi aşıyor")
    p = max(1, -(-sum(sureler) // en_uzun))
    while True:
        boylar = [n // p + (1 if i < n % p else 0) for i in range(p)]
        parcalar, bas = [], 0
        for boy in boylar:
            parcalar.append(list(range(bas, bas + boy)))
            bas += boy
        if all(sum(sureler[j] for j in parca) <= en_uzun for parca in parcalar):
            return parcalar
        p += 1


def sayfalari_cikar(b):
    """Bölümün sayfalarını öğelere ayırır. Her sayfa: {sayfa, baslik, birimler}. Birim, aynı karede
    kalması gereken öğeler: ilk birim başlık + ilk içerik öğesidir (başlık karenin dibinde yalnız kalmasın)."""
    sayfalar = []
    for no, s in enumerate(b["sayfalar"], 1):
        ogeler = []
        if s.get("buyuk"):
            ogeler.append({"tip": "buyuk", "buyuk": s["buyuk"], "buyuk_alt": s.get("buyuk_alt", "")})
        if s.get("formul"):
            ogeler.append({"tip": "formul", "metin": s["formul"]})
        for etiket, deger in s.get("tablo", []):
            ogeler.append({"tip": "satir", "etiket": etiket, "deger": deger})
        for m in s.get("maddeler", []):
            ogeler.append({"tip": "madde", "metin": m})
        if s.get("kaynak"):
            ogeler.append({"tip": "not", "metin": s["kaynak"]})
        bas = {"tip": "bas", "sayfa": no, "baslik": s["baslik"]}
        birimler = [[bas] + ogeler[:1]] + [[o] for o in ogeler[1:]]
        sayfalar.append({"sayfa": no, "baslik": s["baslik"], "birimler": birimler})
    return sayfalar


def _ogeler(s, devam, birimler):
    """Bir sayfa parçasının öğe listesi; devam parçasının başına "(devam)" satırı eklenir."""
    on = [{"tip": "devam", "sayfa": s["sayfa"], "baslik": s["baslik"]}] if devam else []
    return on + [o for u in birimler for o in u]


def _sayfayi_bol(s, sigar_mi):
    """Bir kareye sığmayan sayfayı parçalara (birim listeleri) böler. Son iki parçayı dengeler:
    son kare tek maddeyle boş kalmasın diye önceki parçanın sonundaki birimler sığdığı sürece
    son parçaya kaydırılır (ilk birim, yani başlık + ilk öğe, yerinde kalır)."""
    parcalar, cur = [], []
    for u in s["birimler"]:
        aday = cur + [u]
        if not cur or sigar_mi(_ogeler(s, bool(parcalar), aday)):
            cur = aday          # tek başına sığmayan birim de kabul edilir; çizimde uyarı çıkar
        else:
            parcalar.append(cur)
            cur = [u]
    parcalar.append(cur)
    if len(parcalar) >= 2:
        a, b = parcalar[-2], parcalar[-1]
        while len(a) > 1 and len(a) - 1 > len(b):
            yeni_b = [a[-1]] + b
            if not sigar_mi(_ogeler(s, True, yeni_b)):
                break
            a, b = a[:-1], yeni_b
        parcalar[-2], parcalar[-1] = a, b
    return parcalar


def kareleri_planla(sayfalar, sigar_mi):
    """İçerik karelerini (kapak hariç) öğe listeleri olarak döndürür. sigar_mi(ogeler) -> bool.

    Her sayfa yeni karede başlar; yalnızca önceki karenin kalan boşluğuna bütünüyle sığan sayfa o
    karede devam eder. Sığmayan sayfa _sayfayi_bol() ile parçalanır."""
    kareler, cur = [], []
    for s in sayfalar:
        tum = _ogeler(s, False, s["birimler"])
        if cur and sigar_mi(cur + tum):          # kısa sayfa: önceki karenin boşluğuna bütünüyle sığdı
            cur = cur + tum
            continue
        if cur:
            kareler.append(cur)
        parcalar = _sayfayi_bol(s, sigar_mi)
        for i, parca in enumerate(parcalar[:-1]):
            kareler.append(_ogeler(s, i > 0, parca))
        cur = _ogeler(s, len(parcalar) > 1, parcalar[-1])
    if cur:
        kareler.append(cur)
    return kareler


class Cizici:
    """Tek tarayıcıyla hem ölçer hem çizer (her kare için yeni tarayıcı açmamak için)."""

    def __init__(self):
        from jinja2 import Environment, FileSystemLoader
        self.env = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True)
        self.gecici = SABLONLAR / "_cikti_rehber_hikaye.html"   # yazı tipleri göreli yolla yüklensin diye burada

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        kwargs = {}
        if os.environ.get("CHROME_YOLU"):
            kwargs["executable_path"] = os.environ["CHROME_YOLU"]
        self._tarayici = self._pw.chromium.launch(**kwargs)
        self.sayfa = self._tarayici.new_page(viewport={"width": BOYUT[0], "height": BOYUT[1]})
        return self

    def __exit__(self, *a):
        self._tarayici.close()
        self._pw.stop()
        self.gecici.unlink(missing_ok=True)

    def _ac(self, veri):
        self.gecici.write_text(self.env.get_template(SABLON).render(**veri), encoding="utf-8")
        self.sayfa.goto(self.gecici.as_uri())
        self.sayfa.evaluate("document.fonts.ready")

    def sigar_mi(self, veri):
        self._ac(veri)
        return self.sayfa.evaluate(OLC_JS)

    def ciz(self, veri, yol):
        """Kareyi JPEG olarak kaydeder; içerik sığıyorsa True döndürür."""
        self._ac(veri)
        self.sayfa.wait_for_timeout(200)
        self.sayfa.screenshot(path=str(yol), clip={"x": 0, "y": 0, "width": BOYUT[0], "height": BOYUT[1]},
                              type="jpeg", quality=92)
        return self.sayfa.evaluate(OLC_JS)


def uret(b, no, sonraki, seri, hesap, cikti, damga, plan=None, reels_kapak=False):
    """Bölümün hikâye karelerini cikti klasörüne yazar; dosya adlarını sırayla döndürür.
    plan (liste) verilirse kare planı (kapak hariç her karenin öğeleri) ona eklenir (rehber Reels'inin okuması).
    reels_kapak: kapağın Reels sürümü de çizilir (hikâyedeki "Dokunun →" yok): bilgi<no>-<damga>-reels-kapak.jpg"""
    ortak = {"b": b, "no": no, "seri": seri, "hesap": hesap, "sonraki": sonraki}
    dosyalar = []
    with Cizici() as c:
        uyarilar = []
        kareler = kareleri_planla(
            sayfalari_cikar(b),
            lambda ogeler: c.sigar_mi({**ortak, "kapak": False, "ogeler": ogeler, "k": 2, "n": 2, "son": True}))
        if plan is not None:
            plan.extend(kareler)
        n = len(kareler) + 1
        if reels_kapak:
            c.ciz({**ortak, "k": 1, "n": n, "son": False, "kapak": True, "reels": True},
                  Path(cikti) / f"bilgi{no}-{damga}-reels-kapak.jpg")
        for k in range(1, n + 1):
            veri = {**ortak, "k": k, "n": n, "son": k == n}
            if k == 1:
                veri["kapak"] = True
            else:
                veri.update(kapak=False, ogeler=kareler[k - 2])
            yol = Path(cikti) / f"bilgi{no}-{damga}-hikaye-{k}.jpg"
            if not c.ciz(veri, yol):
                uyarilar.append(f"kare {k} taşıyor")
            dosyalar.append(yol.name)
    for u in uyarilar:
        print(f"::warning::Rehber hikâyesi #{no}: {u}")
    return dosyalar
