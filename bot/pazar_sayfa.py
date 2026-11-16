# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Sitede ayrıntılı pazar analizi sayfası (gunlukgumus.com/pazar/ ve her hafta pazar/YYYY-AA-GG/).

Rıdvan, 16 Kasım 2026 15:50: "Web sitesine girenler son pazarın yorumunu daha detaylı bir şekilde görmelerini
istiyorum"; önizleme sonrası 16:06 "1 uygun" (sayfa, ana sayfa düğmesi bu sayfaya, her hafta kendi adresinde arşiv)
ve "2- uygun" (her vadeye ayrıntılı açıklama, pazar yorumundan sonra ayrı küçük bir istekle).

Sayfada Instagram'daki kaydırmalı yorumun tamamı (iki vade, haftanın gelişmeleri) ile görselde olmayanlar durur:
dönem rakamları (gram, ons, dolar/TL, parite, en düşük–en yüksek), hareketin onstan mı kurdan mı geldiği (kuralla
hesaplanır, modele sorulmaz), haber kaynaklarının bağlantıları, ayrıntılı açıklama (varsa), nasıl hazırlandı ve SPK
uyarısı. Haber özetinin kendisi (doğrulanmamış rakamlar) yayımlanmaz; yalnız ayrıntılı açıklamaya dayanak olur.

Kayıtlar sana özel gumus-kayit deposunda: pazar/analizler.json ({"YYYY-AA-GG": kayıt}). Akış:
  1. Pazar yorumu üretilince (paylas.yml → uret):  python bot/pazar_sayfa.py kaydet --meta site/meta.json
     Kaydı yerel veri/pazar.json'a ve (deneme değilse) özel depoya yazar; aynı işteki site bu haftayı da içerir.
  2. Paylaşım bittikten sonra (paylas.yml → yayinla): python bot/pazar_sayfa.py uzun
     Son kayda ayrıntılı açıklamayı ayrı bir istekle ekler (bot/yorum.py → uzun_yaz). Paylaşımdan sonra çalışır,
     söz verilen paylaşımı hiçbir zaman geciktirmez; hata verirse sayfa açıklamasız çıkar.
  3. Siteyi kuran her iş önce:                      python bot/pazar_sayfa.py indir
Her hata yalnızca uyarıdır: paylaşım ve bilgi sayfası bu yüzden durmaz (kayıt yoksa düğme eskisi gibi Instagram'a gider).
"""
import argparse
import base64
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as bot  # noqa: E402
import yorum  # noqa: E402

YEREL = bot.KOK / "veri" / "pazar.json"
HEDEF = "pazar/analizler.json"
SAYFA_YOLU = "pazar/"
GUC_DOLU = {"zayıf": 1, "orta": 2, "belirgin": 3}
ARSIV_LISTE = 12   # sayfadaki "Geçmiş analizler" listesinde en çok bu kadar hafta (hepsinin sayfası yine üretilir)


# ---------------------------------------------------------------- kayıt

def _haftalik(aciklama):
    """Eski meta.json için (16 Kasım 2026 öncesi): açıklamanın ikinci satırından gram, haftalık değişim, veri anı."""
    m = re.search(r"Gram gümüş: ([\d.,]+) ₺ \(haftalık ([▲▼]) (%[\d,]+)\) · (.+)", aciklama or "")
    if not m:
        return {}
    return {"gram": m.group(1), "veri_ani": m.group(4).strip(),
            "gram_deg": {"isaret": m.group(2), "metin": m.group(3), "yon": "dusus" if m.group(2) == "▼" else "artis"}}


def kayit_kur(meta):
    """meta.json (bot/main.py → pazar yorumu) → sayfa kaydı."""
    s = meta.get("sayfa") or {}
    if not s:   # eski meta: tarih dosya adından, gram ve veri anı açıklamadan
        m = re.search(r"yorum-(\d{4})(\d{2})(\d{2})-", " ".join(meta.get("dosyalar") or []))
        s = {"tarih": f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None, **_haftalik(meta.get("aciklama"))}
    if not s.get("tarih"):
        raise ValueError("pazar yorumunun tarihi bulunamadı")
    gel = meta.get("gelismeler") or {}
    return {
        "surum": 1,
        "tarih": str(s["tarih"])[:10],
        "veri_ani": s.get("veri_ani"),
        "gram": s.get("gram"),
        "gram_deg": s.get("gram_deg"),
        "onceki": s.get("onceki") or {},
        "yorum": meta["yorum"],
        "haberler": meta.get("haberler") or [],
        "istatistik": meta.get("istatistik") or {},
        "son_veri": meta.get("son_veri") or {},
        # Haber özeti yalnızca ayrıntılı açıklamaya dayanak; sitede gösterilmez (doğrulanmamış rakamlar içerir)
        "gelismeler": {"metin": gel.get("metin"), "kaynaklar": gel.get("kaynaklar") or [],
                       "oy_gunu": bool(gel.get("oy_gunu"))} if gel else None,
    }


def oku():
    """Yerel kayıtlar {tarih: kayıt}; yoksa {}."""
    try:
        veri = json.loads(YEREL.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def _yerele_yaz(kayitlar):
    YEREL.parent.mkdir(parents=True, exist_ok=True)
    YEREL.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def _uzak_oku():
    """(kayıtlar, sha); dosya yoksa ({}, None). Hata yedek.YedekHatasi."""
    import yedek
    r = yedek._github("GET", f"/contents/{HEDEF}")
    if r.status_code == 404:
        return {}, None
    if r.status_code >= 400:
        raise yedek.YedekHatasi(f"pazar kayıtları okunamadı ({r.status_code})")
    veri = r.json()
    if veri.get("encoding") == "base64" and veri.get("content"):
        metin = base64.b64decode(veri["content"]).decode("utf-8")
    else:   # 1 MB üstü
        import requests
        ham = requests.get(veri["download_url"], timeout=30,
                           headers={"Authorization": f"Bearer {os.environ['KAYIT_PAT'].strip()}"})
        if ham.status_code >= 400:
            raise yedek.YedekHatasi(f"pazar kayıtları okunamadı ({ham.status_code})")
        metin = ham.text
    kayitlar = json.loads(metin)
    if not isinstance(kayitlar, dict):
        raise yedek.YedekHatasi("pazar kayıtları beklenen biçimde değil")
    return kayitlar, veri.get("sha")


def _uzaga_yaz(degistir, mesaj):
    """Özel depodaki dosyayı okuyup degistir(kayıtlar) ile değiştirir ve yazar; aradaki yazımda bir kez yeniden dener."""
    import yedek
    for _ in range(2):
        kayitlar, sha = _uzak_oku()
        yeni = degistir(json.loads(json.dumps(kayitlar)))
        if yeni == kayitlar:
            return kayitlar
        govde = {"message": mesaj, "content": base64.b64encode(
            json.dumps(yeni, ensure_ascii=False, indent=1, default=str).encode("utf-8")).decode()}
        if sha:
            govde["sha"] = sha
        r = yedek._github("PUT", f"/contents/{HEDEF}", json=govde)
        if r.status_code in (409, 422):
            continue
        if r.status_code >= 400:
            raise yedek.YedekHatasi(f"pazar kayıtları yazılamadı ({r.status_code})")
        return yeni
    raise yedek.YedekHatasi("pazar kayıtları yazılamadı (aynı anda başka bir yazım)")


def kaydet(meta_yolu, deneme=False):
    meta = json.loads(Path(meta_yolu).read_text(encoding="utf-8"))
    if meta.get("tur") != "yorum" or not meta.get("yorum"):
        print("Pazar yorumu değil; pazar kaydı atlandı.")
        return
    k = json.loads(json.dumps(kayit_kur(meta), default=str))
    yerel = oku()
    yerel[k["tarih"]] = {**(yerel.get(k["tarih"]) or {}), **k}
    _yerele_yaz(yerel)
    if deneme:
        print(f"Pazar analizi kaydı yalnız yerelde (deneme): {k['tarih']}.")
        return
    _uzaga_yaz(lambda v: {**v, k["tarih"]: {**(v.get(k["tarih"]) or {}), **k}},
               f"Pazar analizi: {k['tarih']}")
    print(f"Pazar analizi kaydedildi: gumus-kayit/{HEDEF} ({k['tarih']}).")


def indir():
    kayitlar, _ = _uzak_oku()
    if not kayitlar:
        print("Pazar analizi kaydı henüz yok; sitede düğme Instagram'daki yoruma gider.")
        return
    yerel = oku()   # aynı işte yeni üretilmiş (deneme) kayıt varsa korunur
    _yerele_yaz({**kayitlar, **{t: k for t, k in yerel.items() if t not in kayitlar}})
    print(f"Pazar analizleri indirildi: {len(kayitlar)} hafta, son {max(kayitlar)}.")


def uzun(tarih=None, yalniz_yerel=False, yeniden=False):
    """Kayda ayrıntılı açıklama ekler (son kayıt ya da tarih). Zaten varsa dokunmaz (yeniden=True değilse)."""
    kayitlar = oku() if yalniz_yerel else _uzak_oku()[0]
    if not kayitlar:
        print("Pazar analizi kaydı yok; ayrıntılı açıklama atlandı.")
        return
    tarih = tarih or max(kayitlar)
    k = kayitlar.get(tarih)
    if not k:
        raise SystemExit(f"{tarih} için pazar kaydı yok")
    if k.get("uzun") and not yeniden:
        print(f"{tarih} için ayrıntılı açıklama zaten var.")
        return
    sonuc = yorum.uzun_yaz(k)
    if not sonuc:
        print(f"::warning::Pazar sayfası: {tarih} için ayrıntılı açıklama yazılamadı; sayfa açıklamasız çıkar.")
        return
    yerel = oku()
    yerel[tarih] = {**(yerel.get(tarih) or k), "uzun": sonuc}
    _yerele_yaz(yerel)
    if not yalniz_yerel:
        _uzaga_yaz(lambda v: {**v, tarih: {**(v.get(tarih) or k), "uzun": sonuc}},
                   f"Pazar analizi: {tarih} ayrıntılı açıklama")
    print(f"Ayrıntılı açıklama eklendi: {tarih}" + (" (yalnız yerel)" if yalniz_yerel else " (gumus-kayit)"))


# ---------------------------------------------------------------- sayfa verisi

def _yuzde(x, basamak=1):
    """{"isaret", "metin", "yon"}: ▲ %1,7 gibi."""
    if x is None:
        return None
    yon = "dusus" if x < 0 else "artis"
    return {"yon": yon, "isaret": "▼" if x < 0 else "▲", "metin": "%" + bot.tr_sayi(abs(x), basamak)}


def _gun(iso):
    return date.fromisoformat(str(iso)[:10])


def _uzun_tarih(iso):
    g = _gun(iso)
    return f"{g.day} {bot.AYLAR[g.month - 1]} {g.year}"


def _kisa(iso):
    g = _gun(iso)
    return f"{g.day} {bot.AYLAR[g.month - 1]}"


def hareket_kaynagi(ist):
    """Gram fiyattaki değişimin onstan mı kurdan mı geldiği; yalnız rakamlardan, kuralla (gram ≈ ons × kur).
    Bir etken öbürünün en az 2 katıysa ona yazılır, değilse "birlikte"."""
    ons, kur, gram = ist.get("ons"), ist.get("dolar"), ist.get("gram")
    if ons is None or kur is None or gram is None:
        return None
    o, k, g = _yuzde(ons), _yuzde(kur), _yuzde(gram)
    if abs(ons) >= 2 * abs(kur):
        pay = "onstan"
    elif abs(kur) >= 2 * abs(ons):
        pay = "dolar/TL kurundan"
    else:
        pay = "ons ve kurdan birlikte"
    ek = ""
    if (ons < 0) != (kur < 0):   # ters yönlü: küçük olan büyüğün bir kısmını dengeledi
        if pay == "onstan":
            ek = (" Kurdaki artış düşüşün bir kısmını dengeledi." if kur > 0
                  else " Kurdaki düşüş yükselişin bir kısmını sınırladı.")
        elif pay == "dolar/TL kurundan":
            ek = (" Onstaki düşüş artışın bir kısmını dengeledi." if ons < 0
                  else " Onstaki artış düşüşün bir kısmını dengeledi.")
    cumle = (f"Ons gümüş (dolar) {o['metin']} {'düştü' if ons < 0 else 'yükseldi'}, dolar/TL {k['metin']} "
             f"{'geriledi' if kur < 0 else 'arttı'}; gram fiyat {g['metin']} {'düştü' if gram < 0 else 'yükseldi'}. "
             f"Değişimin büyük kısmı {pay} geldi.{ek}")
    olcek = max(abs(ons), abs(kur), abs(gram), 0.01)
    cubuk = [{"ad": ad, "deg": _yuzde(x), "oran": round(abs(x) / olcek * 100, 1)}
             for ad, x in (("Gram (₺)", gram), ("Ons ($)", ons), ("Dolar/TL", kur))]
    return {"cumle": cumle, "cubuk": cubuk}


def hafta_sonu_notu(k):
    """Analiz pazar günü yazılır ama gümüş hafta sonu işlem görmez: son fiyat cuma kapanışıdır. Analiz günüyle son
    veri günü farklıysa sayfada bunu söyleyen not (Rıdvan, 16 Kasım 2026 18:50: "neden son pazar günü yer almıyor")."""
    son = (k.get("son_veri") or {}).get("tarih")
    if not son or str(son)[:10] == k["tarih"]:
        return None
    return (f"Gümüş hafta sonu işlem görmediği için rakamlar son işlem günü olan {_kisa(son)} "
            f"{bot.GUNLER[_gun(son).weekday()]} kapanışına kadardır; analiz {_kisa(k['tarih'])} "
            f"{bot.GUNLER[_gun(k['tarih']).weekday()]} sabahı yazıldı.")


def veri(k, instagram=None, liste=None):
    """Şablon (templates/pazar.html) için tek haftanın sayfa verisi. liste: geçmiş analizler [{tarih, yol, ...}]."""
    yz, ist = k["yorum"], k.get("istatistik") or {}
    gel = k.get("gelismeler") or {}
    kaynaklar = gel.get("kaynaklar") or []
    alan_url = {}
    for x in kaynaklar:
        alan_url.setdefault(x.get("alan"), x.get("url"))
    bitis = (k.get("son_veri") or {}).get("tarih")
    uzun = k.get("uzun") or {}
    vadeler = []
    for v in yorum.VADELER:
        a = v["anahtar"]
        y, s = yz[a], ist.get(a) or {}
        vadeler.append({
            "ad": v["ad"], "ufuk": v["ufuk"], "anahtar": a,
            "yon": y["yon"], "yon_sinif": "dusus" if y["yon"] == "düşüş" else "artis",
            "ok": "▼" if y["yon"] == "düşüş" else "▲",
            "guc": yorum.GUC_ADI[y["guc"]], "guc_dolu": GUC_DOLU[y["guc"]],
            "ozet": y["ozet"], "durum": y["durum"], "seyir": y["seyir"],
            "izlenecek": [x.strip() for x in y["izlenecek"].split(",") if x.strip()],
            "degisim": (y.get("degisim") or "").strip(),
            "onceki": (k.get("onceki") or {}).get(a),
            "uzun": uzun.get(a),
            "donem": s.get("etiket"),
            "aralik_tarih": f"{_kisa(s['baslangic'])} – {_kisa(bitis)}" if s.get("baslangic") and bitis else None,
            "veri_yeterli": s.get("veri_yeterli", True),
            "rakamlar": [r for r in (
                {"ad": "Gram gümüş (₺)", "deg": _yuzde(s.get("gram"))},
                {"ad": "Ons gümüş ($)", "deg": _yuzde(s.get("ons"))},
                {"ad": "Dolar/TL", "deg": _yuzde(s.get("dolar"))},
                {"ad": "Altın/gümüş paritesi", "deg": _yuzde(s.get("parite"))},
            ) if r["deg"]],
            "parite": _yuzde(s.get("parite")),
            "aralik": (f"{bot.tr_sayi(s['gram_en_dusuk'])} – {bot.tr_sayi(s['gram_en_yuksek'])} ₺"
                       if s.get("gram_en_dusuk") and s.get("gram_en_yuksek") else None),
            "hareket": hareket_kaynagi(s) if s.get("veri_yeterli", True) else None,
        })
    son = k.get("son_veri") or {}
    return {
        "tarih": _uzun_tarih(k["tarih"]),
        "tarih_iso": k["tarih"],
        "veri_ani": k.get("veri_ani"),
        "hafta_sonu": hafta_sonu_notu(k),
        "gram": k.get("gram") or (bot.tr_sayi(son["gram"]) if son.get("gram") else None),
        "gram_hafta": k.get("gram_deg"),
        "ons": bot.tr_sayi(son["gumus"]) if son.get("gumus") else None,
        "dolar": bot.tr_sayi(son["dolar"], 4) if son.get("dolar") else None,
        "parite": bot.tr_sayi(son["altin"] / son["gumus"], 1) if son.get("altin") and son.get("gumus") else None,
        "vadeler": vadeler,
        "uzun_var": bool(uzun),
        "haberler": [{**h, "baslik": h.get("baslik") or yorum.HABER_KONU_BASLIK.get(h["konu"], h["konu"].upper()),
                      "url": alan_url.get(h.get("kaynak"))} for h in (k.get("haberler") or [])],
        "kaynaklar": [{"alan": x.get("alan"), "baslik": x.get("baslik"), "url": x.get("url")} for x in kaynaklar
                      if str(x.get("url", "")).startswith(("https://", "http://"))],
        # Instagram açıklamasındaki "aşağıdaki fiyat ve kur verileri" sitede yukarıda duruyor
        "nasil": yorum._nasil_hazirlandi(gel.get("metin")).replace("Nasıl hazırlandı: ", "")
                 .replace("aşağıdaki fiyat ve kur verileri", "bu sayfadaki fiyat ve kur verileri"),
        "uyari": yorum.UYARI,
        "yz_notu": yorum.YZ_NOTU,
        "secim_notu": yorum.SECIM_NOTU if gel.get("oy_gunu") else None,
        "instagram": instagram,
        "liste": liste or [],
    }


def uret(cikti, env, v, kayitlar, instagram_son=None):
    """site/pazar/ (son hafta) ve site/pazar/YYYY-AA-GG/ (her hafta). Site haritası için [(adres, tarih)] döndürür.
    v: bot/sayfa.py → veri_hazirla. instagram_son: son yorumun Instagram bağlantısı (sayfa.son_pazar_analizi)."""
    tarihler = sorted(kayitlar, reverse=True)
    if not tarihler:
        return []
    liste = [{"tarih": _uzun_tarih(t), "tarih_iso": t, "yol": f"{SAYFA_YOLU}{t}/",
              "kisa": kayitlar[t]["yorum"]["kisa"]["yon"], "orta": kayitlar[t]["yorum"]["orta"]["yon"]}
             for t in tarihler[:ARSIV_LISTE]]
    # Sayfada "Son pazar analizi" düğmesi kendine gitmesin
    taban = {**v, "tanitim": {**v["tanitim"], "pazar": None}}
    sablon = env.get_template("pazar.html")
    harita = []
    for i, t in enumerate(tarihler):
        ig = instagram_son if i == 0 and instagram_son else v["instagram"]
        p = veri(kayitlar[t], instagram=ig, liste=liste)
        yol = cikti / SAYFA_YOLU / t
        yol.mkdir(parents=True, exist_ok=True)
        (yol / "index.html").write_text(sablon.render(**taban, p=p, kok="../../", adres=f"{SAYFA_YOLU}{t}/",
                                                      son_mu=i == 0), encoding="utf-8")
        harita.append((v["url"] + f"{SAYFA_YOLU}{t}/", t))
        if i == 0:
            (cikti / SAYFA_YOLU / "index.html").write_text(
                sablon.render(**taban, p=p, kok="../", adres=SAYFA_YOLU, son_mu=True), encoding="utf-8")
            harita.insert(0, (v["url"] + SAYFA_YOLU, t))
    return harita


def dugme(kayitlar, url):
    """Ana sayfadaki "Son pazar analizi" düğmesi: {"url", "tarih"} (kayıt yoksa None)."""
    if not kayitlar:
        return None
    return {"url": url + SAYFA_YOLU, "tarih": _kisa(max(kayitlar))}


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("kaydet")
    a.add_argument("--meta", default="site/meta.json")
    alt.add_parser("indir")
    a = alt.add_parser("uzun")
    a.add_argument("--tarih")
    a.add_argument("--yalniz-yerel", action="store_true", help="özel depoya yazma (önizleme)")
    a.add_argument("--yeniden", action="store_true")
    a = ap.parse_args()
    deneme = os.environ.get("DENEME", "").strip().lower() in ("1", "true", "evet")
    try:
        if a.komut == "kaydet":
            kaydet(a.meta, deneme=deneme)
        elif a.komut == "indir":
            indir()
        else:
            uzun(a.tarih, yalniz_yerel=a.yalniz_yerel or deneme, yeniden=a.yeniden)
    except Exception as e:  # noqa: BLE001 — paylaşım ve site hiçbir zaman bu yüzden durmaz
        print(f"::warning::Pazar sayfası ({a.komut}): {type(e).__name__}: {str(e)[:300]}")


if __name__ == "__main__":
    main()
