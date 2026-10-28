# Şu an ne üzerinde çalışılıyor

Bu depoda aynı anda birden çok Claude sohbeti çalışır. Her sohbet işe başlamadan önce bu dosyayı okur, işe
başlarken bir satır ekler (commit + push), iş bitince ya da bırakılınca satırını siler. Aynı dosyalarda ya da aynı
paylaşım türünde başka bir iş yazılıysa Rıdvan'a sorar (CLAUDE.md → "Ortak çalışma").

| Başladı | Konu | Dokunduğu dosyalar | Dal / durum |
|---|---|---|---|
| 2026-10-28 21:00 | **Zamanlı paylaşımlar hedef saate kadar bekler** (Rıdvan 28 Ekim 20:18 "takipçilere 20 00 yazdık … işleme önce başlamalıyız", 20:54 "söze uymamız gerekiyor"): cron'lar 40 dk erkene, hedef 09:55 / 13:55 / 19:55 / 10:55; önizleme + onayla main'e. | `.github/workflows/paylas.yml`, `bot/program.py`, `bot/test_program.py`, `bot/test_kart.py`, `bot/test_pazar.py`, README | `zamanlama-hedef` |
