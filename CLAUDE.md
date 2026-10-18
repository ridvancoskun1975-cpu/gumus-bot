# Claude için kurallar (gumus-bot)

- **Galeri (Rıdvan, 17 Ekim 2026: "Bana gönderdiğin her görsel ve videoyu aynı anda proje galerisine ekle."):**
  Rıdvan'a gönderilen her görsel ve video (önizleme, önce/sonra, deneme çıktısı dahil) aynı turda proje galerisine
  de eklenir: https://claude.ai/artifact/CFKCZroCrWfYDG8b1BgDzm (proje-galerisi becerisi; veri `ogeler`
  koleksiyonunda). Oturumun dosyaları başka sohbetten erişilemez; eklenmeyen dosya kaybolur.
- **Günlük sınır: günde en fazla 4 paylaşım** (14 Ekim 2026 21:23'ten beri; önce 3). 5. ve sonrası yalnızca Rıdvan
  sohbette açıkça onay verirse gider.
  Ayrıntı: README → "Günlük sınır", kod `bot/sinir.py`.
  - Onay işaretini (`Run workflow → onay: true`) ya da `bot/sinir.py` → `GUN_SINIRI` istisnasını Rıdvan
    sohbette açıkça "onayla" / "gitsin" demeden **kullanma**. Bir paylaşımın onayı yalnızca o paylaşım içindir.
  - Paylaşım yapan bir çalıştırmayı elle başlatmadan önce bugünkü sayıyı söyle; o paylaşım akşamki zamanlı
    paylaşımları 5.'ye itecekse bunu da söyle.
- **Ortak çalışma: bu depoda aynı anda birden çok sohbet çalışır** (Rıdvan, 17 Ekim 2026 "Ekle"; o gün bir sohbet
  pazar Reels'ini sesli yaparken diğeri eski kopya üstünde aynı şablona önizleme hazırladı):
  1. İşe başlarken, Rıdvan'a önizleme göstermeden önce ve main'e almadan önce `git fetch origin main` ile son hâli çek;
     son baktığından beri gelen commit'leri (`git log`) oku. Başka bir sohbet aynı dosyalara ya da aynı paylaşım türüne
     dokunmuşsa devam etmeden Rıdvan'a söyle.
  2. Rıdvan'a gösterilen her önizleme o anki main'in (ya da onun üstüne kurulmuş dalın) üstüne kurulur; eski bir
     kopyadan önizleme gösterme.
  3. `CALISMA.md`: işe başlamadan önce oku. İşe başlarken konuyu, dokunacağın dosyaları ve dalı bir satır olarak ekle
     (commit + push); iş bitince ya da bırakılınca satırı sil. Aynı dosyalarda ya da aynı paylaşım türünde başka bir iş
     yazılıysa Rıdvan'a sor. Satır 24 saatten eskiyse Rıdvan'a "hâlâ sürüyor mu" diye sor, kendiliğinden silme.
- Bakım güncellemeleri (eylem ve kütüphane sürümleri) ayrı dalda yapılır. Deneme başarılıysa ve paylaşım çıktısı
  değişmiyorsa main'e alınır, sonra bildirilir. Paylaşım içeriğini ya da takvimi değiştiren her şey önce önizleme ve
  onay ister. (Rıdvan'ın 15 Ekim 2026 tarihli açık isteği; metni kendisi verdi.)
- Rıdvan genelde yalnızca telefondan, Claude üzerinden çalışır: GitHub ayarı, GitHub onay ekranı ya da başka
  bir arayüz gerektiren çözüm önerme.
- Taahhüt: hafta içi her gün 2 kez gram fiyatı (~10:00 Reels, ~20:00 özet); bu ikisi kaldırılmaz, başka içerikle
  değiştirilmez.
- Pazar yorumu 2 paylaşım sayılır (kaydırmalı + Reels). Pazar Reels'i sesli (Rıdvan, 17 Ekim 2026: Gemini erkek
  sesi, analizin tamamı okunur; okumayı ona sormadan kısaltma). Ses **Orus** (`ses.YORUM_SES`; Rıdvan, 3 örnekten "Ses 2"); hikâyeye 24 sn müzikli sürüm
  gider; ses alınamazsa Reels 24 sn müzikli gider (yedek yol kaldırılmaz). Ses, üslup ya da okunan metin
  değişecekse önce önizleme ve onay.
- Pazar yorumunun orta vade geçmişini MetalCharts Starter verir (17 Ekim 2026); Ocak 2027'de iptal (11 Ocak
  hatırlatması), sonra kendi kayıtlarımız. Pazar yorumu önizlemesini Rıdvan'a gerçek veriyle üret (deneme, ornek
  işaretsiz): örnek veride orta vade boş görünür. (Yalnız kısa ve orta vade kuralı aşağıda.)
- Bütün seslendirmeler 1,5 kat hızlı (`ses.HIZ`) ve sesli Reels'te hareketli "Sesi açın" rozeti var (Rıdvan,
  17 Ekim 2026); hız ya da rozet değişecekse önce önizleme ve onay.
- Instagram'a tarayıcıyla bakılmaz.
- Sitede ve açıklamalarda model ya da şirket adı yazılmaz.
  (Bu dört kural: Rıdvan, 16 Ekim 2026 "CLAUDE.md'ye ekle".)
- Goril maskotu (README → "Goril maskotu", `bot/goril.py`): hafta içi sabah Reels'i (19 Ekim 2026'dan; Rıdvan 16 Ekim
  22:25 "sabaha şimdi koy"), akşam özeti, cumartesi haftalık özeti ve aylık özette (Rıdvan, 18 Ekim 2026: aylıkta %5'te
  sevinir; haftalık ve aylıkta dönemde eşik ilk kez aşılır ya da dönem 1 aylık en yüksekte kapanırsa kutlar). Pazar yorumuna hiçbir zaman goril
  eklenmez. Hâller, eşikler ya da açıklama satırı değişecekse önce önizleme ve Rıdvan'ın onayı. Gorilli üretim her
  hatada ve süre aşımında gorilsiz paylaşıma düşmeli; bu yedek yol kaldırılmaz. Goril bir yazıyla üst üste binerse
  paylaşım durmaz, goril kalır ve Rıdvan'a bildirilir (gece kontrolü; Rıdvan, 16 Ekim 2026 22:43).
- Rehber hikâyesi kareler tek tek değil, tek müzikli video olarak gider (kapak 3 sn, kare 6 sn), rehber gönderisiyle
  aynı çalıştırmada (`bot/main.py` → `REHBER_HIKAYE_OTOMATIK = True`); hikâye kalabalık olmamalı.
- Rehber günü (salı ve perşembe ~14:00) akışa kaydırmalı gönderinin yerine bölümün tamamını kare kare okuyan (Rıdvan, 17 Ekim 2026: "Tabii ki tamamının okunması gerekiyor"; okumayı ona sormadan kısaltma) kadın sesli Reels gider,
  hikâyeye müzikli rehber videosu; cumartesi kısa Reels'i kaldırıldı (Rıdvan, 16 Ekim 2026 23:4x: "Kaydırmalı rehber
  kimse bakmaz"; `bot/main.py` → `REHBER_REELS`). Ses **Sulafat** (Rıdvan, 16 Ekim 2026, 3 önizlemeden seçti; README →
  "Rehber Reels seslendirmesi", `bot/ses.py`). Rehber hikâye videoları sesli değil, müzikli kalır. Reels üretilemezse
  o gün kaydırmalı gider; bu yedek yol kaldırılmaz. Ses, üslup ya da okunan metin değişecekse önce önizleme ve onay. Seslendirmenin her hatası Reels'i
  yalnızca müzikle paylaşmaya düşmeli; bu yedek yol kaldırılmaz. Gemini 17 Ekim 2026'dan beri ücretli katmanda (Rıdvan, ön
  ödemeli kredi + otomatik yenileme; günlük 10 okuma sınırı yok). Denemeler yine yalnızca yedek modelle (Rıdvan,
  16 Ekim 2026). Kredi biterse ses 402 verir, Reels müzikle gider; gece kontrolü bildirir. Yeni rehber bölümü eklenince `ses.OKUMA`'ya satır ekle.
- Rehber arşivi Reels'i (Rıdvan, 17 Ekim 2026 "öneriyi uygula"): sesli rehber Reels'inden önce yayımlanan #3–#5 birer
  kez, rehbersiz hafta içi günü ~14:00'te aynı tam okumalı sesli Reels olarak gider (`bot/bilgi.py` → `ARSIV_REELS`:
  22, 26, 28 Ekim; tür `kisa`). Yalnız Reels: kaydırmalı ve hikâye tekrar gitmez; Reels üretilemezse o gün paylaşım
  yok. Tarih ya da bölüm değişecekse önce Rıdvan'a sor.
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
- Dal temizliği otomatik (Rıdvan, 17 Ekim 2026: "Otomatiğe al"): `.github/workflows/dal-temizle.yml` her gece 03:17 TR'de
  içeriği tamamen main'de olan ve 24 saatten eski dalları siler; main'e alınmamış işi olan dala dokunmaz. Rıdvan'a
  dal silmesini söyleme. Onay bekleyen önizlemeyi main'e almadan ayrı dalda tutmak bu yüzden güvenli.
- Pazar yorumu **yalnız kısa ve orta vade, kalıcı** (Rıdvan, 17 Ekim 2026: "Kısa, orta, uzun yerine sadece kısa ve
  orta kalacak", "geleceği de etkilemeli"). Uzun vade hiçbir tarihte, veri birikse de geri gelmez; sesli okuma,
  müzikli video, Reels, kaydırmalı gönderi, cumartesi hatırlatması, bilgi sayfası hep kısa ve orta. Uzun vadeyi geri
  getiren tarih ya da koşul ekleme; yalnızca Rıdvan açıkça isterse. Kendi kayıtlarımız 1 yılı doldurunca 13 Ekim
  2027'de TEK hatırlatma gelir (zamanlanmış görev; Rıdvan 17 Ekim 2026 13:01: "1 yıllık veri dolunca uzun vadeye
  geçelim. bunun için 1 hatırlatma yeterli"); "evet" derse önizleme + onayla eklenir, ilk pazar 17 Ekim 2027.
