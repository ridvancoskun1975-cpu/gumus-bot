# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Site dosyasının yayına çıkmasını bekleme (bot/main.py → _url_hazir_mi, DosyaYok) ve iş akışının yeniden
deneme yolu (paylas.yml). Ağ yok. Çalıştır: python bot/test_url_hazir.py

6 Kasım 2026: sitenin önbelleği "dosya yok" (404) cevabını da saklıyor; dosya çıkmadan bir kez bakılınca sonraki
bakışlar da 404 aldı, akşam özeti iki kez "Dosya yayına çıkmadı" ile düştü. Rıdvan: "1 saat içerisinde mutlaka
post çıkmalı. en geç!" Her bakış önbelleği atlar (benzersiz ?v=), 15 dk bekler; hiçbir şey gitmeden düşerse iş
akışı siteyi yeniden kurup bir kez daha dener.
"""
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


class Cevap:
    def __init__(self, kod):
        self.status_code = kod


class SahteSaat:
    def __init__(self):
        self.t = 1_000_000.0

    def time(self):
        return self.t

    def time_ns(self):
        return int(self.t * 1e9)

    def sleep(self, sn):
        self.t += sn


asil = (main.requests.head, main.time.time, main.time.time_ns, main.time.sleep)
saat = SahteSaat()
main.time.time, main.time.time_ns, main.time.sleep = saat.time, saat.time_ns, saat.sleep
bakilan = []
try:
    # 1) İlk bakışlar 404, sonra 200: dosya çıktığı an döner; her bakış ayrı adres (önbellek atlanır)
    sira = [404, 404, 404, 200]

    def head(url, **kw):
        bakilan.append((url, kw.get("headers", {})))
        return Cevap(sira.pop(0))
    main.requests.head = head
    main._url_hazir_mi("https://gunlukgumus.com/post-20261106-1955.mp4")
    esit(len(bakilan), 4, "200 gelince hemen döner")
    esit(len({u for u, _ in bakilan}), 4, "her bakış benzersiz adres (önbellekteki 404'e takılmaz)")
    esit(all(re.fullmatch(r"https://gunlukgumus\.com/post-20261106-1955\.mp4\?v=\d+", u) for u, _ in bakilan), True,
         "adres ?v=<sayı> ile")
    esit(all(h.get("Cache-Control") == "no-cache" for _, h in bakilan), True, "no-cache başlığı")

    # 2) Zaten sorgulu adrese & eklenir
    bakilan.clear()
    sira = [200]
    main._url_hazir_mi("https://ornek.invalid/a.jpg?x=1")
    esit(bakilan[0][0].startswith("https://ornek.invalid/a.jpg?x=1&v="), True, "sorgulu adrese & ile eklenir")

    # 3) Hiç çıkmazsa varsayılan 15 dk bekler, sonra DosyaYok (RuntimeError alt sınıfı: kapak yedeği bozulmaz)
    esit(main.URL_BEKLEME_SN, 900, "varsayılan bekleme 15 dk")
    esit(issubclass(main.DosyaYok, RuntimeError), True, "DosyaYok bir RuntimeError")
    main.requests.head = lambda url, **kw: Cevap(404)
    basla = saat.t
    try:
        main._url_hazir_mi("https://ornek.invalid/yok.mp4")
        esit(True, False, "DosyaYok bekleniyordu")
    except main.DosyaYok as e:
        esit("15 dk beklendi" in str(e), True, "hata mesajında süre")
    esit(saat.t - basla <= 900, True, "15 dk'yı aşmaz")
    esit(saat.t - basla >= 890, True, "15 dk'ya yakın bekler")

    # 4) Ağ hatası beklemeyi durdurmaz
    sira = ["hata", 200]

    def head2(url, **kw):
        k = sira.pop(0)
        if k == "hata":
            raise main.requests.ConnectionError("bağlantı yok")
        return Cevap(k)
    main.requests.head = head2
    main._url_hazir_mi("https://ornek.invalid/b.mp4")
    esit(sira, [], "ağ hatasından sonra yeniden bakar")
finally:
    main.requests.head, main.time.time, main.time.time_ns, main.time.sleep = asil

# 5) main(): DosyaYok ile hiçbir şey paylaşılmadan düşünce işaret bırakır; bir şey paylaşıldıysa bırakmaz
asil_yayinla, asil_argv = main.yayinla, sys.argv
with tempfile.TemporaryDirectory() as d:
    isaret = Path(d) / "dosya-yok.txt"
    os.environ["DOSYA_YOK_ISARETI"] = str(isaret)
    os.environ["GORUNEN_DOSYA"] = str(Path(d) / "gorunen.txt")
    sys.argv = ["main.py", "yayinla", "--cikti", d, "--url", "https://ornek.invalid/"]
    try:
        for gorunen, beklenen in ((0, True), (1, False)):
            isaret.unlink(missing_ok=True)

            def yayinla(*a, _g=gorunen):
                main._GORUNEN[0] = _g
                raise main.DosyaYok("Dosya yayına çıkmadı (15 dk beklendi): x")
            main.yayinla = yayinla
            try:
                main.main()
                esit(True, False, "hata yükselmeliydi")
            except main.DosyaYok:
                pass
            esit(isaret.exists(), beklenen, f"görünen {gorunen}: işaret {'var' if beklenen else 'yok'}")
    finally:
        main.yayinla, sys.argv = asil_yayinla, asil_argv
        main._GORUNEN[0] = 0
        os.environ.pop("DOSYA_YOK_ISARETI", None)
        os.environ.pop("GORUNEN_DOSYA", None)

# 6) İş akışı: ilk deneme düşerse site yeniden kurulur ve bir kez daha denenir; ikisi de düşerse iş kırmızı
yml = (KOK / ".github/workflows/paylas.yml").read_text(encoding="utf-8")
esit("DOSYA_YOK_ISARETI: ${{ runner.temp }}/dosya-yok.txt" in yml, True, "ilk denemede işaret dosyası")
esit("- name: Dosyayı yeniden internete koy (yedek)\n        if: steps.dosya_yok.outputs.var == '1'" in yml, True,
     "işaret varsa site yeniden kurulur")
esit("- name: Instagram'a paylaş (yeniden deneme)\n        id: paylas2\n        if: steps.dosya_yok.outputs.var == '1'"
     in yml, True, "işaret varsa paylaşım yeniden denenir")
esit("if: steps.paylas.outcome == 'failure' && steps.paylas2.outcome != 'success'\n        run: |" in yml, True,
     "ikisi de düşerse iş kırmızı biter")
esit(yml.index("Paylaşım sonucu") < yml.index("- name: Görünen içerik sayısı\n"), True,
     "görünen sayı adımları sonuçtan sonra (always) çalışır")

print(f"test_url_hazir: {gecen} sınama geçti")
