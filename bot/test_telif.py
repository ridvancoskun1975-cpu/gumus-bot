# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""bot/telif.py sınamaları: her kod ve şablon dosyasında telif satırı var mı, satır çıktıyı değiştiriyor mu?

Çalıştırma: python bot/test_telif.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telif  # noqa: E402

hatalar = []


def bak(kosul, ad):
    if not kosul:
        hatalar.append(ad)


# 1. Depodaki bütün dosyalar başlıklı, LICENSE ve README tamam
bak(telif.denetle(), "depo denetimi")

# 2. Türlere göre doğru yorum biçimi
bak(telif.satir("bot/main.py").startswith("# "), "py yorumu")
bak(telif.satir(".github/workflows/paylas.yml").startswith("# "), "yml yorumu")
bak(telif.satir("templates/hareket.js").startswith("/* "), "js yorumu")
bak(telif.satir("templates/ortak.css").startswith("/* "), "css yorumu")
bak(telif.satir("templates/sayfa.html").startswith("{#- ") and telif.satir("templates/sayfa.html").endswith(" -#}"),
    "jinja yorumu")
bak(telif.satir("rehber_pdf/bolum-01.html").startswith("<!-- ") and "CC BY-NC-ND" in telif.satir("rehber_pdf/bolum-01.html"),
    "kitap parçası yorumu")
bak(telif.satir("templates/goril/istif.svg").startswith("<!-- "), "svg yorumu")
for dokunulmaz in ("rehber_pdf/DURUM.md", "README.md", "dis-tetik/appsscript.json", "assets/fonts/OFL-Archivo.txt",
                   "assets/muzik.mp3.enc", "requirements.txt"):
    bak(telif.satir(dokunulmaz) is None, f"dokunulmaz: {dokunulmaz}")

# 3. Shebang önce kalır; ikinci kez eklenmez
m = telif.ekle_metne("bot/x.sh", "#!/usr/bin/env bash\necho a\n")
bak(m.splitlines()[0] == "#!/usr/bin/env bash" and telif.ISARET in m.splitlines()[1], "shebang sırası")
bak(telif.ekle_metne("bot/x.sh", m) == m, "ikinci ekleme")

# 4. Jinja şablonunda satır çıktıya hiçbir şey yazmaz (satır sonu dahil)
from jinja2 import Environment  # noqa: E402

env = Environment(autoescape=True)
ham = "<!DOCTYPE html>\n<p>{{ a }}</p>\n"
bak(env.from_string(telif.ekle_metne("templates/x.html", ham)).render(a=1) == env.from_string(ham).render(a=1),
    "jinja çıktısı aynı")

if hatalar:
    print("BAŞARISIZ:", ", ".join(hatalar))
    sys.exit(1)
print("test_telif: hepsi geçti")
