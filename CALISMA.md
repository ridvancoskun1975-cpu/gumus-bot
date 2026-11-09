# Şu an ne üzerinde çalışılıyor

Bu depoda aynı anda birden çok Claude sohbeti çalışır. Her sohbet işe başlamadan önce bu dosyayı okur, işe
başlarken bir satır ekler (commit + push), iş bitince ya da bırakılınca satırını siler. Aynı dosyalarda ya da aynı
paylaşım türünde başka bir iş yazılıysa Rıdvan'a sorar (CLAUDE.md → "Ortak çalışma").

| Başladı | Konu | Dokunduğu dosyalar | Dal / durum |
|---|---|---|---|
| 9 Kas 2026 13:00 | #31 Pazar yorumunda siyaset zorunlu (haber özetinde varsa) | bot/yorum.py, bot/test_yorum*.py, bot/test_pazar.py, README.md, CLAUDE.md (pazar siyaset satırı) | dal siyaset-zorunlu-2026-11-09 (önizleme bekliyor) |
| 9 Kas 13:00 | Pazar Reels'i 4 sayfa: "Haftanın gelişmeleri" sahnesi sesli okunur (Rıdvan 12:54; 13:05 iş bölümü: siyasi madde kuralı #31 diğer sohbette, ben yalnız Reels). yorum.py'de YALNIZ seslendirme_parcalari ve ORNEK_HABERLER'e dokunurum, istem ve denetimlere dokunmam | bot/main.py, bot/ses.py, templates/yorum-reels.html, bot/yorum.py (seslendirme_parcalari), bot/test_pazar.py, bot/test_ses.py, README.md, CLAUDE.md | pazar-4-sayfa-siyaset / sürüyor |
| 9 Kas 2026 13:05 | #22 Üretimde kod içi süre bütçesi: ffmpeg/seslendirme süre sınırı, takılınca yedek yol (Rıdvan "Başla") | bot/main.py, bot/ses.py, bot/butce.py (yeni), bot/test_butce.py (yeni), bot/test_ses.py (4 sahte seslendir imzası), README.md | dal `sure-butcesi` · önizleme hazırlanıyor |
