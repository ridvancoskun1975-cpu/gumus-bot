# Claude için kurallar (gumus-bot)

- **Günlük sınır: günde en fazla 4 paylaşım** (14 Ekim 2026 21:23'ten beri; önce 3). 5. ve sonrası yalnızca Rıdvan
  sohbette açıkça onay verirse gider.
  Ayrıntı: README → "Günlük sınır", kod `bot/sinir.py`.
  - Onay işaretini (`Run workflow → onay: true`) ya da `bot/sinir.py` → `GUN_SINIRI` istisnasını Rıdvan
    sohbette açıkça "onayla" / "gitsin" demeden **kullanma**. Bir paylaşımın onayı yalnızca o paylaşım içindir.
  - Paylaşım yapan bir çalıştırmayı elle başlatmadan önce bugünkü sayıyı söyle; o paylaşım akşamki zamanlı
    paylaşımları 5.'ye itecekse bunu da söyle.
- Bakım güncellemeleri (eylem ve kütüphane sürümleri) ayrı dalda yapılır. Deneme başarılıysa ve paylaşım çıktısı
  değişmiyorsa main'e alınır, sonra bildirilir. Paylaşım içeriğini ya da takvimi değiştiren her şey önce önizleme ve
  onay ister. (Rıdvan'ın 15 Ekim 2026 tarihli açık isteği; metni kendisi verdi.)
- Rıdvan genelde yalnızca telefondan, Claude üzerinden çalışır: GitHub ayarı, GitHub onay ekranı ya da başka
  bir arayüz gerektiren çözüm önerme.
- Taahhüt: hafta içi her gün 2 kez gram fiyatı (~10:00 Reels, ~20:00 özet); bu ikisi kaldırılmaz, başka içerikle
  değiştirilmez.
- Pazar yorumu 2 paylaşım sayılır (kaydırmalı + Reels).
- Instagram'a tarayıcıyla bakılmaz.
- Sitede ve açıklamalarda model ya da şirket adı yazılmaz.
  (Bu dört kural: Rıdvan, 16 Ekim 2026 "CLAUDE.md'ye ekle".)
- Goril maskotu (README → "Goril maskotu", `bot/goril.py`): hafta içi sabah Reels'i (19 Ekim 2026'dan; Rıdvan 16 Ekim
  22:25 "sabaha şimdi koy"), akşam özeti ve cumartesi haftalık özetinde her gün. Pazar yorumuna hiçbir zaman goril
  eklenmez. Hâller, eşikler ya da açıklama satırı değişecekse önce önizleme ve Rıdvan'ın onayı. Gorilli üretim her
  hatada gorilsiz paylaşıma düşmeli; bu yedek yol kaldırılmaz. (Rıdvan, 16 Ekim 2026.)
- Rehber hikâyesi kareler tek tek değil, tek müzikli video olarak gider (kapak 3 sn, kare 6 sn), rehber gönderisiyle
  aynı çalıştırmada (`bot/main.py` → `REHBER_HIKAYE_OTOMATIK = True`); hikâye kalabalık olmamalı.
- Rehber kısa Reels'i (cumartesi ~14:00) kadın sesiyle seslendirilir: ses **Sulafat** (Rıdvan, 16 Ekim 2026, 3
  önizlemeden seçti; README → "Rehber Reels seslendirmesi", `bot/ses.py`). Rehber hikâye videoları sesli değil,
  müzikli kalır. Ses, üslup ya da okunan metin değişecekse önce önizleme ve onay. Seslendirmenin her hatası Reels'i
  yalnızca müzikle paylaşmaya düşmeli; bu yedek yol kaldırılmaz. Ücretsiz kota günde ~10 okuma/model, modeller ayrı:
  denemeler yalnızca yedek modelle (Rıdvan, 16 Ekim 2026), ana model paylaşıma kalır; cumartesi 14:00'ten önce
  aynı gün art arda deneme yapma (yedeğin kotası da paylaşımın güvencesi). Yeni rehber bölümü eklenince `ses.OKUMA`'ya satır ekle.
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
