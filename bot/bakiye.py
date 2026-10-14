"""Claude API kredi takibi: pazar yorumunun kullandığı ön ödemeli Console kredisi.

Anthropic ön ödemeli kredi bakiyesini okuyan bir API sunmuyor (Admin API bireysel hesaplarda yok,
bakiye uç noktası da yok). Bu yüzden bakiye şöyle izlenir:
  1. Pazar yorumu her API çağrısının token ve web arama sayısını bir dosyaya yazar
     (bot/yorum.py → API_HARCAMA_DOSYA). İş akışı bunları fiyatlandırıp özel gumus-kayit deposundaki
     api-bakiye.md'ye ekler (kaydet). Deneme çalıştırmaları da gerçek para harcadığı için kaydedilir.
  2. Kredi yüklemeleri (elle ya da Console'un otomatik yüklemesi) Anthropic'in makbuz mailinden
     ("Your receipt from Anthropic, PBC", satır "… credit purchase") okunur: "Claude API kredisi:
     Gmail makbuzları" zamanlanmış görevi (Claude, pazartesi ve cumartesi ~11:52) yeni makbuzları
     bulup buraya işler (yukleme). Tahmini bakiye = yüklenen − harcanan. Rıdvan Billing'de gördüğü
     bakiyeyi söylerse "son okuma" olarak işlenir (okuma); o zaman tahmin o andan başlar.
  3. "API bakiye kontrolü" iş akışı (bakiye.yml) pazartesi ve cumartesi ~12:20 çalışır (kontrol):
     tahmini bakiyeye bakar ve API'ye çok küçük bir istek atar (anahtar geçerli mi, kredi bitti mi).
     Riskli alanda iş kırmızı biter: GitHub hata maili gelir, Mail Özeti onu en üste koyar.

Bot deposu ve iş akışı günlükleri herkese açık; tutarlar günlüğe hiç yazılmaz, yalnızca özel
depodaki api-bakiye.md'de durur.

Kullanım:
  python bot/bakiye.py kaydet --tur yorum            (iş akışı; KAYIT_PAT, API_HARCAMA_DOSYA, DENEME)
  python bot/bakiye.py kontrol                       (bakiye.yml; ANTHROPIC_API_KEY, KAYIT_PAT)
  python bot/bakiye.py yukleme --usd 20 --tarih 2026-10-13T14:45+03:00 --kaynak "makbuz #2902-7959-3803" \
         --yerel <api-bakiye.md>                     (Claude, özel deponun klonunda; aynı makbuz iki kez işlenmez)
  python bot/bakiye.py okuma --usd 7.40 --yerel <api-bakiye.md>   (Claude: Billing'deki bakiye, isteğe bağlı)
  python bot/bakiye.py durum --yerel <api-bakiye.md>               (Claude: dosyadaki durumu yazdırır)
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import kayit

TR_SAAT = ZoneInfo("Europe/Istanbul")
DOSYA = "api-bakiye.md"
BILLING_URL = "https://platform.claude.com/settings/billing"

# Milyon token başına USD (girdi, çıktı). Düşünme tokenları çıktıya dahildir.
# Kaynak: platform.claude.com/docs/en/models/overview (14 Ekim 2026).
FIYAT = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
}
BILINMEYEN_FIYAT = (4.0, 20.0)      # listede olmayan model: Opus fiyatıyla (temkinli) hesaplanır
ONBELLEK_YAZMA_KAT = 1.25           # 5 dakikalık önbellek yazımı, girdi fiyatının katı
ONBELLEK_OKUMA_KAT = 0.10
ARAMA_FIYATI = 0.01                 # web araması: 1.000 arama 10 $

VARSAYILAN_HAFTALIK = 0.70          # henüz gerçek pazar kaydı yokken haftalık harcama varsayımı (USD)
RISK_HAFTA = 4                      # bundan az pazar yetecek kredi kaldıysa: riskli (uyarı)
KRITIK_HAFTA = 2                    # bundan az: kritik (bir sonraki pazar yetmeyebilir)
KONTROL_MODELI = "claude-haiku-5-5"  # canlı denetim isteği (maliyeti binde bir sentin altında)

VERI_BASI = "<!-- api-bakiye-veri"
VERI_DESEN = re.compile(r"<!-- api-bakiye-veri\n(.*?)\n-->", re.S)


# ---------------------------------------------------------------- hesap

def _usd(n):
    return f"{n:.2f}".replace(".", ",") + " $"


def _sayi(n):
    return f"{n:,}".replace(",", ".")


def _tarih_tr(iso):
    return datetime.fromisoformat(iso).astimezone(TR_SAAT).strftime("%d.%m.%Y %H:%M")


def satir_tutari(s):
    girdi_f, cikti_f = FIYAT.get(s.get("model") or "", BILINMEYEN_FIYAT)
    return ((s.get("girdi", 0) + s.get("onbellek_yazma", 0) * ONBELLEK_YAZMA_KAT
             + s.get("onbellek_okuma", 0) * ONBELLEK_OKUMA_KAT) * girdi_f
            + s.get("cikti", 0) * cikti_f) / 1_000_000 + s.get("arama", 0) * ARAMA_FIYATI


def durum_hesapla(veri):
    """{tahmini, harcanan, haftalik, hafta, seviye} — seviye: normal / riskli / kritik / bilinmiyor."""
    gercek = [h["usd"] for h in veri["harcamalar"] if not h.get("deneme") and h.get("tur") == "yorum"]
    haftalik = (sum(gercek[-6:]) / len(gercek[-6:])) if gercek else VARSAYILAN_HAFTALIK
    haftalik = max(haftalik, 0.05)
    okuma = veri.get("son_okuma")
    if not okuma and not veri["yuklemeler"]:
        return {"tahmini": None, "harcanan": None, "yuklenen": None, "haftalik": haftalik, "hafta": None,
                "seviye": "bilinmiyor"}
    if okuma:
        taban, sinir = okuma["usd"], datetime.fromisoformat(okuma["tarih"])
    else:
        taban, sinir = 0.0, None

    def sonra(kayitlar):
        return [k for k in kayitlar if sinir is None or datetime.fromisoformat(k["tarih"]) > sinir]

    harcanan = sum(h["usd"] for h in sonra(veri["harcamalar"]))
    yuklenen = sum(y["usd"] for y in sonra(veri["yuklemeler"]))
    tahmini = taban + yuklenen - harcanan
    hafta = tahmini / haftalik
    seviye = "kritik" if hafta < KRITIK_HAFTA else "riskli" if hafta < RISK_HAFTA else "normal"
    return {"tahmini": tahmini, "harcanan": harcanan, "yuklenen": yuklenen, "haftalik": haftalik, "hafta": hafta,
            "seviye": seviye}


# ---------------------------------------------------------------- dosya biçimi

def veriyi_oku(metin):
    m = VERI_DESEN.search(metin or "")
    if not m:
        return {"son_okuma": None, "yuklemeler": [], "harcamalar": [], "son_kontrol": None}
    veri = json.loads(m.group(1))
    veri.setdefault("son_okuma", None)
    veri.setdefault("yuklemeler", [])
    veri.setdefault("harcamalar", [])
    veri.setdefault("son_kontrol", None)
    return veri


SEVIYE_ADI = {"normal": "🟢 normal", "riskli": "🟠 riskli — kredi yüklemek gerekiyor",
              "kritik": "🔴 kritik — bir sonraki pazar yetmeyebilir", "bilinmiyor": "⚪ bilinmiyor"}
KONTROL_ADI = {"tamam": "API isteği başarılı (anahtar geçerli, kredi var)",
               "kredi_bitti": "🔴 API kredi bitti diyor",
               "anahtar_gecersiz": "🔴 API anahtarı geçersiz ya da süresi dolmuş",
               "ulasilamadi": "API'ye ulaşılamadı (geçici olabilir)",
               "istek_hatasi": "denetim isteği hata verdi (kod incelenmeli)"}


def dosyayi_olustur(veri):
    d = durum_hesapla(veri)
    okuma = veri.get("son_okuma")
    if okuma:
        bakiye = (f"**Tahmini bakiye:** {_usd(d['tahmini'])} (son okuma {_usd(okuma['usd'])} · "
                  f"{_tarih_tr(okuma['tarih'])}; sonrasında {_usd(d['yuklenen'])} yükleme, "
                  f"{_usd(d['harcanan'])} harcama)")
        sure = f" · yaklaşık {int(d['hafta'])} pazar yeter (pazar başına ~{_usd(d['haftalik'])})"
    elif d["tahmini"] is not None:
        bakiye = (f"**Tahmini bakiye:** {_usd(d['tahmini'])} (yüklenen {_usd(d['yuklenen'])} − "
                  f"harcanan {_usd(d['harcanan'])})")
        sure = f" · yaklaşık {int(d['hafta'])} pazar yeter (pazar başına ~{_usd(d['haftalik'])})"
    else:
        bakiye = "**Tahmini bakiye:** bilinmiyor — henüz kredi yüklemesi kaydı yok"
        sure = ""
    k = veri.get("son_kontrol")
    kontrol = (f"**Son kontrol:** {_tarih_tr(k['tarih'])} · {KONTROL_ADI.get(k['sonuc'], k['sonuc'])}"
               if k else "**Son kontrol:** henüz yok")
    satirlar = []
    for h in reversed(veri["harcamalar"]):
        calisma = f"#{h['calisma']}" if h.get("calisma") else "—"
        satirlar.append(f"| {_tarih_tr(h['tarih'])} | {h['etiket']} | {calisma} | {h['model']} | "
                        f"{_sayi(h['girdi'])} | {_sayi(h['cikti'])} | {h['arama']} | {_usd(h['usd'])} |")
    if not satirlar:
        satirlar.append("| — | henüz kayıt yok | | | | | | |")
    yukleme_satirlari = [f"| {_tarih_tr(y['tarih'])} | {_usd(y['usd'])} | {y.get('kaynak', '')} |"
                         for y in reversed(veri["yuklemeler"])] or ["| — | henüz kayıt yok | |"]
    gorunur = "\n".join([
        "# Claude API kredisi · gumus-bot",
        "",
        bakiye,
        "",
        f"**Durum:** {SEVIYE_ADI[d['seviye']]}{sure}",
        "",
        kontrol,
        "",
        f"Gerçek bakiye: {BILLING_URL} (Anthropic bakiyeyi okuyan bir API sunmadığı için buradaki tahmindir). "
        "Kredi yüklemeleri (elle ya da otomatik yükleme) Anthropic'in makbuz mailinden kendiliğinden işlenir "
        "(\"Claude API kredisi: Gmail makbuzları\" görevi, pazartesi ve cumartesi ~11:52). "
        f"Uyarı: {RISK_HAFTA} pazardan az yetecek kredi kalınca ya da API kredi bitti deyince \"API bakiye kontrolü\" "
        "işi (pazartesi ve cumartesi ~12:20) kırmızı biter, hata maili gelir.",
        "",
        "Bu dosyayı gumus-bot kendisi günceller (bot/bakiye.py); elle değiştirme. Saatler Türkiye saatidir. "
        "Tutarlar token sayısından hesaplanan tahmindir (Opus 5.5: milyon token 4 $ girdi / 20 $ çıktı, arama 1 sent).",
        "",
        "## Kredi yüklemeleri (makbuzlardan, KDV hariç)",
        "",
        "| Tarih | Kredi | Kaynak |",
        "|---|---|---|",
        *yukleme_satirlari,
        "",
        "## Harcamalar",
        "",
        "| Tarih | Ne | Çalışma | Model | Girdi token | Çıktı token | Arama | Tutar |",
        "|---|---|---|---|---|---|---|---|",
        *satirlar,
        "",
    ])
    return gorunur + "\n" + VERI_BASI + "\n" + json.dumps(veri, ensure_ascii=False, indent=1) + "\n-->\n"


# ---------------------------------------------------------------- özel depo

def _al():
    kayit.DOSYA = DOSYA
    return kayit.dosyayi_al()


def _guncelle(degistir, mesaj):
    """Dosyayı okur, degistir(veri) uygular, yazar (aynı anda yazımda 3 kez dener). Güncel veriyi döndürür."""
    kayit.DOSYA = DOSYA
    for _ in range(3):
        metin, sha = kayit.dosyayi_al()
        veri = veriyi_oku(metin)
        degistir(veri)
        if kayit.dosyayi_yaz(dosyayi_olustur(veri), sha, mesaj):
            return veri
    raise kayit.KayitHatasi("dosya üç denemede de kaydedilemedi (aynı anda başka yazım)")


# ---------------------------------------------------------------- komutlar

def harcamayi_oku(yol):
    satirlar = []
    with open(yol, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                satirlar.append(json.loads(line))
    return satirlar


def kaydet(tur, deneme=False, simdi=None):
    yol = os.environ.get("API_HARCAMA_DOSYA", "").strip()
    if not yol or not os.path.exists(yol):
        print("API harcaması yok (bu çalıştırmada Claude API çağrılmadı); kayıt atlandı.")
        return
    cagrilar = harcamayi_oku(yol)
    if not cagrilar:
        print("API harcaması yok; kayıt atlandı.")
        return
    simdi = simdi or datetime.now(TR_SAAT)
    modeller = sorted({c.get("model") or "?" for c in cagrilar})
    bilinmeyen = [m for m in modeller if m not in FIYAT]
    if bilinmeyen:
        print(f"::warning::Fiyat listesinde olmayan model {bilinmeyen}: Opus fiyatıyla hesaplandı "
              "(bot/bakiye.py → FIYAT güncellenmeli).")
    kayit_satiri = {
        "tarih": simdi.isoformat(timespec="minutes"),
        "tur": tur,
        "deneme": bool(deneme),
        "etiket": kayit.ETIKET.get(tur, tur) + (" (deneme)" if deneme else ""),
        "calisma": os.environ.get("GITHUB_RUN_ID", ""),
        "model": ", ".join(modeller),
        "cagri": len(cagrilar),
        "girdi": sum(c.get("girdi", 0) + c.get("onbellek_yazma", 0) + c.get("onbellek_okuma", 0) for c in cagrilar),
        "cikti": sum(c.get("cikti", 0) for c in cagrilar),
        "arama": sum(c.get("arama", 0) for c in cagrilar),
        "usd": round(sum(satir_tutari(c) for c in cagrilar), 4),
    }
    veri = _guncelle(lambda v: v["harcamalar"].append(kayit_satiri),
                     f"API harcaması: {kayit_satiri['tarih'][:16]} ({kayit_satiri['etiket']})")
    seviye = durum_hesapla(veri)["seviye"]
    # Tutar bilerek yazdırılmıyor: bu depo ve günlükleri herkese açık.
    print(f"API harcama kaydı güncellendi: {kayit.DEPO}/{DOSYA} (özel depo). Kredi durumu: {seviye}.")
    if seviye in ("riskli", "kritik"):
        print(f"::warning::Claude API kredisi azaldı ({seviye}). Kredi yükle: {BILLING_URL}")


def canli_denetim(anahtar):
    """Claude API'ye çok küçük bir istek: tamam / kredi_bitti / anahtar_gecersiz / ulasilamadi / istek_hatasi."""
    son = "ulasilamadi"
    for deneme in range(3):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
                "x-api-key": anahtar, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": KONTROL_MODELI, "max_tokens": 16,
                      "messages": [{"role": "user", "content": "Sadece 'tamam' yaz."}]})
        except requests.RequestException:
            son = "ulasilamadi"
            time.sleep(15 * (deneme + 1))
            continue
        if r.status_code == 200:
            return "tamam", ""
        metin = r.text[:300]
        kucuk = metin.lower()
        if "credit balance" in kucuk or ("billing" in kucuk and r.status_code in (400, 402, 403)):
            return "kredi_bitti", metin
        if r.status_code in (401, 403):
            return "anahtar_gecersiz", metin
        if r.status_code in (429, 500, 502, 503, 504, 529):
            son = "ulasilamadi"
            time.sleep(15 * (deneme + 1))
            continue
        return "istek_hatasi", f"HTTP {r.status_code}: {metin}"
    return son, ""


def kontrol(simdi=None):
    anahtar = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    simdi = simdi or datetime.now(TR_SAAT)
    if anahtar:
        sonuc, ayrinti = canli_denetim(anahtar)
    else:
        sonuc, ayrinti = "anahtar_gecersiz", "ANTHROPIC_API_KEY tanımlı değil"

    def isle(v):
        v["son_kontrol"] = {"tarih": simdi.isoformat(timespec="minutes"), "sonuc": sonuc}

    try:
        veri = _guncelle(isle, f"API bakiye kontrolü: {simdi:%Y-%m-%d %H:%M}")
    except kayit.KayitHatasi as e:
        print(f"::warning::Bakiye dosyası okunamadı/yazılamadı: {e}. Yalnızca API isteğine bakılıyor.")
        veri = None
    d = durum_hesapla(veri) if veri else {"seviye": "bilinmiyor", "hafta": None}

    hatalar = []
    if sonuc == "kredi_bitti":
        hatalar.append("Claude API kredisi bitmiş görünüyor: pazar yorumu paylaşılamaz.")
    elif sonuc == "anahtar_gecersiz":
        hatalar.append(f"Claude API anahtarı geçersiz ya da süresi dolmuş ({ayrinti[:120]}).")
    elif sonuc in ("ulasilamadi", "istek_hatasi"):
        print(f"::warning::Canlı denetim yapılamadı ({KONTROL_ADI[sonuc]}). {ayrinti[:200]}")
    if d["seviye"] == "kritik":
        hatalar.append(f"Claude API kredisi kritik: {KRITIK_HAFTA} pazardan az yetecek kadar kaldı (tahmini).")
    elif d["seviye"] == "riskli":
        hatalar.append(f"Claude API kredisi azaldı: {RISK_HAFTA} pazardan az yetecek kadar kaldı (tahmini).")
    elif d["seviye"] == "bilinmiyor" and veri is not None:
        print("::warning::Kredi yüklemesi kaydı yok; yalnızca kredinin bitip bitmediği denetlenebiliyor.")

    ozet = os.environ.get("GITHUB_STEP_SUMMARY")
    if hatalar:
        ileti = " ".join(hatalar) + f" Kredi yükle: {BILLING_URL} → Buy credits; sonra Claude'a yeni bakiyeyi yaz."
        print(f"::error title=Claude API kredisi::{ileti}")
        if ozet:
            with open(ozet, "a", encoding="utf-8") as f:
                f.write(f"## ⚠️ Claude API kredisi\n\n{ileti}\n")
        return 1
    # Tutar bilerek yazdırılmıyor: bu depo ve günlükleri herkese açık.
    print(f"Kredi durumu: {d['seviye']}; canlı denetim: {sonuc}.")
    if ozet:
        with open(ozet, "a", encoding="utf-8") as f:
            f.write(f"Claude API kredisi: {d['seviye']} · canlı denetim: {KONTROL_ADI.get(sonuc, sonuc)}\n")
    return 0


def yukleme(usd, yol, tarih, kaynak):
    """Kredi yüklemesini (makbuzdaki KDV hariç tutar) yerel dosyaya işler. Aynı kaynak varsa eklemez.

    True: eklendi, False: zaten vardı."""
    metin = open(yol, encoding="utf-8").read() if os.path.exists(yol) else ""
    veri = veriyi_oku(metin)
    if any(y.get("kaynak") == kaynak for y in veri["yuklemeler"]):
        return False
    veri["yuklemeler"].append({"tarih": datetime.fromisoformat(tarih).isoformat(timespec="minutes"),
                               "usd": round(float(usd), 2), "kaynak": kaynak})
    veri["yuklemeler"].sort(key=lambda y: y["tarih"])
    with open(yol, "w", encoding="utf-8") as f:
        f.write(dosyayi_olustur(veri))
    return True


def okuma(usd, yol, simdi=None):
    """Rıdvan'ın Billing sayfasında okuduğu bakiyeyi yerel dosyaya (özel deponun klonu) işler."""
    simdi = simdi or datetime.now(TR_SAAT)
    metin = open(yol, encoding="utf-8").read() if os.path.exists(yol) else ""
    veri = veriyi_oku(metin)
    veri["son_okuma"] = {"tarih": simdi.isoformat(timespec="minutes"), "usd": round(float(usd), 2)}
    with open(yol, "w", encoding="utf-8") as f:
        f.write(dosyayi_olustur(veri))
    return durum_hesapla(veri)


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    a_kaydet = alt.add_parser("kaydet")
    a_kaydet.add_argument("--tur", default="yorum")
    alt.add_parser("kontrol")
    a_okuma = alt.add_parser("okuma")
    a_okuma.add_argument("--usd", required=True)
    a_okuma.add_argument("--yerel", required=True)
    a_okuma.add_argument("--tarih", help="ISO zaman (varsayılan şimdi)")
    a_yukleme = alt.add_parser("yukleme")
    a_yukleme.add_argument("--usd", required=True)
    a_yukleme.add_argument("--tarih", required=True, help="makbuzdaki ödeme zamanı, ISO (ör. 2026-10-13T14:45+03:00)")
    a_yukleme.add_argument("--kaynak", required=True, help='ör. "makbuz #2902-7959-3803"')
    a_yukleme.add_argument("--yerel", required=True)
    a_durum = alt.add_parser("durum")
    a_durum.add_argument("--yerel", required=True)
    a = ap.parse_args()

    if a.komut == "kaydet":
        if not os.environ.get("KAYIT_PAT"):
            print("::warning::KAYIT_PAT tanımlı değil; API harcaması kaydedilemedi.")
            return 0
        try:
            kaydet(a.tur, os.environ.get("DENEME", "").lower() == "true")
        except (kayit.KayitHatasi, ValueError, OSError) as e:
            print(f"::warning::API harcaması kaydedilemedi: {e}")
        return 0
    if a.komut == "kontrol":
        return kontrol()
    if a.komut == "okuma":
        simdi = datetime.fromisoformat(a.tarih) if a.tarih else None
        d = okuma(a.usd.replace(",", "."), a.yerel, simdi)
        print(json.dumps(d, ensure_ascii=False))
        return 0
    if a.komut == "yukleme":
        eklendi = yukleme(a.usd.replace(",", "."), a.yerel, a.tarih, a.kaynak)
        print("eklendi" if eklendi else "zaten kayıtlı")
        return 0
    if a.komut == "durum":
        veri = veriyi_oku(open(a.yerel, encoding="utf-8").read())
        print(json.dumps({**durum_hesapla(veri), "son_okuma": veri.get("son_okuma"),
                          "yuklemeler": veri["yuklemeler"],
                          "son_kontrol": veri.get("son_kontrol"), "kayit": len(veri["harcamalar"])},
                         ensure_ascii=False))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
