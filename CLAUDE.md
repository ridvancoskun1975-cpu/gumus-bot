# Claude için kurallar (gumus-bot)

- **Günlük sınır: günde en fazla 3 paylaşım.** 4. ve sonrası yalnızca Rıdvan sohbette açıkça onay verirse gider.
  Ayrıntı: README → "Günlük sınır", kod `bot/sinir.py`.
  - Onay işaretini (`Run workflow → onay: true`) ya da `bot/sinir.py` → `GUN_SINIRI` istisnasını Rıdvan
    sohbette açıkça "onayla" / "gitsin" demeden **kullanma**. Bir paylaşımın onayı yalnızca o paylaşım içindir.
  - Paylaşım yapan bir çalıştırmayı elle başlatmadan önce bugünkü sayıyı söyle; o paylaşım akşamki zamanlı
    paylaşımları 4.'ye itecekse bunu da söyle.
- Rıdvan genelde yalnızca telefondan, Claude üzerinden çalışır: GitHub ayarı, GitHub onay ekranı ya da başka
  bir arayüz gerektiren çözüm önerme.
- Rehber hikâye kareleri otomatik paylaşılmaz (`bot/main.py` → `REHBER_HIKAYE_OTOMATIK = False`); hikâye
  kalabalık olmamalı.
