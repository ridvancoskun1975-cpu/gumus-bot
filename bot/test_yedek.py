"""bot/yedek.py sınamaları (ağa çıkmaz; GitHub yanıtları taklit edilir). Çalıştır: python bot/test_yedek.py"""
import base64
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yedek  # noqa: E402

gecen = 0


def kontrol(ad, kosul, ek=""):
    global gecen
    if not kosul:
        print("HATA", ad, ek)
        sys.exit(1)
    gecen += 1
    print("TAMAM", ad)


class Yanit:
    def __init__(self, durum, veri=None):
        self.status_code, self._veri = durum, veri or {}

    def json(self):
        return self._veri


class SahteDepo:
    """GitHub contents API'sinin yedek dosyası için yeterli taklidi."""

    def __init__(self, kayitlar=None, catisma=0):
        self.kayitlar, self.sha, self.yazim, self.catisma = kayitlar, ("s1" if kayitlar is not None else None), 0, catisma

    def __call__(self, yontem, yol, **kw):
        if yontem == "GET":
            if self.kayitlar is None:
                return Yanit(404)
            icerik = base64.b64encode(json.dumps(self.kayitlar).encode()).decode()
            return Yanit(200, {"content": icerik, "encoding": "base64", "sha": self.sha})
        if yontem == "PUT":
            if self.catisma:
                self.catisma -= 1
                return Yanit(409)
            govde = kw["json"]
            if self.sha and govde.get("sha") != self.sha:
                return Yanit(409)
            self.kayitlar = json.loads(base64.b64decode(govde["content"]))
            self.yazim += 1
            self.sha = f"s{self.yazim + 1}"
            return Yanit(201, {})
        raise AssertionError(yontem)


def k(g):
    return {"saat": "20:00", "gram": 90.0 + int(g[-2:]) / 100}


os.environ["KAYIT_PAT"] = "deneme"
gecici = Path(tempfile.mkdtemp())
yedek.YEREL = gecici / "veri" / "gecmis.json"

# 1) Önbellek boş: kayıtlar yedekten gelir
yedek._github = SahteDepo({"2026-10-13": k("13"), "2026-10-14": k("14")})
yedek.birlestir()
kontrol("boş önbellek yedekten dolar", json.loads(yedek.YEREL.read_text()) == {"2026-10-13": k("13"), "2026-10-14": k("14")})

# 2) Önbellekte eksik gün: tamamlanır, aynı günde yerel üstün
yedek.YEREL.write_text(json.dumps({"2026-10-14": {"saat": "20:10", "gram": 1.0}, "2026-10-15": k("15")}))
yedek.birlestir()
s = json.loads(yedek.YEREL.read_text())
kontrol("eksik gün tamamlanır", list(s) == ["2026-10-13", "2026-10-14", "2026-10-15"], s)
kontrol("aynı günde yerel üstün", s["2026-10-14"]["saat"] == "20:10")

# 3) Uyumluysa dosyaya dokunulmaz
once = yedek.YEREL.read_text()
yedek._github = SahteDepo(dict(s))
yedek.birlestir()
kontrol("uyumluyken yazılmaz", yedek.YEREL.read_text() == once)

# 4) Gönder: yedek hiçbir zaman küçülmez (yerelde olmayan gün silinmez), değişiklik yoksa yazmaz
depo = SahteDepo({"2026-10-12": k("12"), "2026-10-13": k("13")})
yedek._github = depo
yedek.YEREL.write_text(json.dumps({"2026-10-13": k("13"), "2026-10-16": k("16")}))
yedek.gonder()
kontrol("gönder birleştirir", list(depo.kayitlar) == ["2026-10-12", "2026-10-13", "2026-10-16"] and depo.yazim == 1,
        depo.kayitlar)
yedek.gonder()
kontrol("değişiklik yoksa ikinci yazım yok", depo.yazim == 1)

# 5) Yedek yoksa oluşturur; çakışmada bir kez yeniden dener
depo = SahteDepo(None)
yedek._github = depo
yedek.gonder()
kontrol("yedek yoksa oluşturulur", depo.yazim == 1 and "2026-10-16" in depo.kayitlar)
depo = SahteDepo({"2026-10-12": k("12")}, catisma=1)
yedek._github = depo
yedek.gonder()
kontrol("çakışmada yeniden dener", depo.yazim == 1)

# 6) ~2 yıldan eski günler atılır (bot/main.py → gecmis_yaz ile aynı)
s = yedek.birlesik({"2026-10-16": 1}, {"2024-08-01": 1, "2024-08-10": 1})
kontrol("800 günden eski atılır", list(s) == ["2024-08-10", "2026-10-16"], s)

# 7) Hata yalnızca uyarı: anahtar yoksa paylaşım durmaz (çıkış 0)
del os.environ["KAYIT_PAT"]


def anahtarsiz(*a, **kw):
    raise yedek.YedekHatasi("KAYIT_PAT tanımlı değil")


yedek._github = anahtarsiz
sys.argv = ["yedek.py", "gonder"]
try:
    yedek.main()
    cikis = 0
except SystemExit as e:
    cikis = e.code
kontrol("anahtar yokken yalnızca uyarı", cikis == 0)

print(f"\ntest_yedek: {gecen} sınama geçti")
