# Şu an ne üzerinde çalışılıyor

Bu depoda aynı anda birden çok Claude sohbeti çalışır. Her sohbet işe başlamadan önce bu dosyayı okur, işe
başlarken bir satır ekler (commit + push), iş bitince ya da bırakılınca satırını siler. Aynı dosyalarda ya da aynı
paylaşım türünde başka bir iş yazılıysa Rıdvan'a sorar (CLAUDE.md → "Ortak çalışma").

| Başladı | Konu | Dokunduğu dosyalar | Dal / durum |
|---|---|---|---|
| 9 Kas 2026 13:00 | #31 Pazar yorumunda siyaset zorunlu (haber özetinde varsa) | bot/yorum.py, bot/test_yorum*.py, bot/test_pazar.py, README.md, CLAUDE.md (pazar siyaset satırı) | dal siyaset-zorunlu-2026-11-09 (önizleme 9 Kas 14:03 Rıdvan'a gitti, onay bekliyor; onayla main'e alınır) |
| 9 Kas 13:00 | Pazar Reels'i 4 sayfa: "Haftanın gelişmeleri" sahnesi sesli okunur (Rıdvan 12:54; 13:05 iş bölümü: siyasi madde kuralı #31 diğer sohbette, ben yalnız Reels). yorum.py'de YALNIZ seslendirme_parcalari ve ORNEK_HABERLER'e dokunurum, istem ve denetimlere dokunmam | bot/main.py, bot/ses.py, templates/yorum-reels.html, bot/yorum.py (seslendirme_parcalari), bot/test_pazar.py, bot/test_ses.py, README.md, CLAUDE.md | pazar-4-sayfa-siyaset / sürüyor |
| 9 Kas 2026 18:10 | #29-1 Sesli Reels'lere Meta "AI info" etiketi (is_ai_generated); Rıdvan 18:05 "hepsini sıra ile yapalım" | bot/main.py (_reels_konteyneri, _yayinla, yorum_reelsi yalnız etiket satırları), bot/test_ai_etiketi.py (yeni), README.md, CLAUDE.md | dal `ai-etiketi` · önizleme bekliyor |
