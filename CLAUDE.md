# Claude için kurallar (gumus-bot)

- **Günlük sınır: günde en fazla 4 paylaşım** (14 Ekim 2026 21:23'ten beri; önce 3). 5. ve sonrası yalnızca Rıdvan
  sohbette açıkça onay verirse gider.
  Ayrıntı: README → "Günlük sınır", kod `bot/sinir.py`.
  - Onay işaretini (`Run workflow → onay: true`) ya da `bot/sinir.py` → `GUN_SINIRI` istisnasını Rıdvan
    sohbette açıkça "onayla" / "gitsin" demeden **kullanma**. Bir paylaşımın onayı yalnızca o paylaşım içindir.
  - Paylaşım yapan bir çalıştırmayı elle başlatmadan önce bugünkü sayıyı söyle; o paylaşım akşamki zamanlı
    paylaşımları 5.'ye itecekse bunu da söyle.
- Rıdvan genelde yalnızca telefondan, Claude üzerinden çalışır: GitHub ayarı, GitHub onay ekranı ya da başka
  bir arayüz gerektiren çözüm önerme.
- Rehber hikâyesi kareler tek tek değil, tek müzikli video olarak gider (kapak 3 sn, kare 6 sn), rehber gönderisiyle
  aynı çalıştırmada (`bot/main.py` → `REHBER_HIKAYE_OTOMATIK = True`); hikâye kalabalık olmamalı.
- "Rehber" öne çıkanının standardı (Rıdvan, 14 Ekim 2026): her bölüm tek video; öne çıkandaki sıra önemli değil,
  eksik olmaması önemli. Tek tek kare olarak giden eski #1–#2 yerine videoları 18 Ekim'de paylaşılır, eski
  kareleri Rıdvan siler. Rehber hikâyesini elle kareler hâlinde paylaşma.
- Claude API kredisi (pazar yorumu): bakiye Anthropic'ten okunamıyor, özel gumus-kayit deposundaki `api-bakiye.md`
  tahmin eder (bot/bakiye.py): yüklenen (Anthropic makbuz maillerinden, "credit purchase" satırı, KDV hariç) −
  harcanan (bot her yorumda kaydeder). Rıdvan kredi yüklemesini takip etmek istemiyor: makbuzları Claude'un
  "Claude API kredisi: Gmail makbuzları" zamanlanmış görevi işler (`python bot/bakiye.py yukleme --usd <kredi>
  --tarih <ISO> --kaynak "makbuz #<no>" --yerel <gumus-kayit klonu>/api-bakiye.md`, commit + push; aynı makbuz iki
  kez işlenmez). Rıdvan Billing'deki bakiyeyi kendisi söylerse `okuma` ile işle. Tutarları herkese açık yerlere
  (bu depo, iş akışı günlükleri, girdiler) yazma. Billing: https://platform.claude.com/settings/billing
