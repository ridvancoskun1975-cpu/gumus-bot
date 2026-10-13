# Gümüş Fiyat Botu

Instagram'a otomatik paylaşım yapar:

| Saat (TR) | Paylaşım |
|---|---|
| ~10:00 | Reels (7 sn video) |
| ~20:00 | Günün özeti (10 sn video) |
| Cumartesi ~10:00 | Haftalık özet (10 sn video: haftanın son değeri, günlük grafik, en yüksek/en düşük) |
| Pazar ~11:00 | Yapay zekâ yorumu: kısa, orta ve uzun vade (kaydırmalı 4 görsel, müziksiz) |

Hepsi müzikli Reels olarak paylaşılır ve profil ızgarasında da görünür. Günün özeti ve haftalık özet aynı videoyla hikâyeye de konur (hikâye başarısız olursa Reels etkilenmez). Açıklamalarda en fazla 5 hashtag var (Instagram sınırı). Etiketler paylaşımlara dağıtılır: Reels, günün özeti ve haftalık özet farklı set kullanır; haftalık özet iki set arasında hafta hafta döner. Değiştirmek için bot/main.py → HASHTAG_REELS / HASHTAG_POST / HASHTAG_HAFTA.

Her paylaşımda: **gram gümüş (₺)**, **altın/gümüş paritesi**, **dolar/TL** ve her birinin önceki iş gününe göre değişimi (ok ile).

İlk ikisi hafta içi her gün paylaşılır. Hafta sonu ons gümüş ve dolar/TL işlem görmediği için günlük paylaşım yapılmaz; onun yerine cumartesi haftalık özet gelir (değişimler önceki haftanın son değerine göre). GitHub zamanlı işleri genelde 5-15 dakika gecikmeyle başlatır.

---

## Kurulum (bir kerelik)

### 1. Instagram hesabını profesyonel hesaba çevir
Instagram → Ayarlar → **Hesap türü ve araçlar** → **Profesyonel hesaba geç** → İşletme ya da İçerik Üretici.

### 2. Meta'dan erişim anahtarı (token) al
1. Bilgisayardan **developers.facebook.com** adresine Facebook hesabınla gir, **Uygulamalarım → Uygulama oluştur**.
2. Kullanım alanı olarak **Instagram API** ile içerik yönetimini seç (Instagram'da mesaj ve içerik yönetimi).
3. Uygulama panelinde **Instagram → API setup with Instagram login** bölümüne gir.
4. **Add account** ile kendi Instagram hesabını ekle ve izin ver.
5. Hesabın yanındaki **Generate token** ile anahtarı oluştur ve bir yere kopyala. (`instagram_business_basic` ve `instagram_business_content_publish` izinleri açık olmalı.)

> Meta menü adlarını zaman zaman değiştiriyor; adımlar birebir aynı görünmeyebilir.

### 3. GitHub ayarları
Bu depo **herkese açık (Public)** olmalı. Görseller ücretsiz GitHub Pages üzerinden Instagram'a verilir; gizli bilgiler (token) yine de güvende kalır.

1. **Settings → Pages → Source:** `GitHub Actions` seç.
2. **Settings → Secrets and variables → Actions → New repository secret:**
   - `IG_TOKEN` → 2. adımda aldığın anahtar
   - `GH_PAT` → token'ın otomatik yenilenmesi için (aşağıya bak)
   - `METALCHARTS_KEY` → metalcharts.org ücretsiz hesabındaki API anahtarı (`mc_live_…`). Yoksa paylaşım yapılmaz, iş uyarı verip atlar.
   - `MUZIK_ANAHTAR` → şifreli müzik dosyasını açan parola. Yoksa videolar müziksiz üretilir.
   - `ANTHROPIC_API_KEY` → pazar yapay zekâ yorumu için Claude API anahtarı (`sk-ant-…`, aşağıya bak). Yoksa pazar paylaşımı uyarıyla atlanır.
   - `KAYIT_PAT` → takipçi kaydı için (aşağıya bak). Yoksa kayıt atlanır, paylaşım etkilenmez.
3. (İsteğe bağlı) Aynı sayfada **Variables** sekmesi → `HESAP_ADI` → görsellerde yazacak kullanıcı adı. Boş bırakırsan bot hesabından otomatik alır.

**ANTHROPIC_API_KEY nasıl alınır:** **platform.claude.com** (Claude Console) → hesap aç → **Billing** bölümünden kredi yükle (en düşük tutar yeterli) → **API keys → Create key** → anahtarı `ANTHROPIC_API_KEY` olarak kaydet. Haftada tek çağrı yapılır; maliyeti ayda birkaç sente denk gelir. İstersen Console'da aylık harcama sınırı koy. Model varsayılanı `claude-sonnet-5-5`; değiştirmek için **Variables** sekmesinde `YZ_MODEL`.

**GH_PAT nasıl alınır:** GitHub → sağ üstte profil → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Repository access: sadece bu depo. Permissions → **Secrets: Read and write**. Süreyi en uzun seç, oluşan anahtarı `GH_PAT` olarak kaydet.

**Takipçi kaydı (KAYIT_PAT):** Bot her paylaşımda takipçi sayısını sana özel (private) `gumus-kayit` deposundaki `takipci.md` dosyasına yazar: son 7 ve 30 günün değişimi ve her kaydın tablosu. Bu depo ve iş akışı günlükleri herkese açık olduğu için sayı günlüğe hiç yazdırılmaz. Kurmak için: private `gumus-kayit` deposu aç (README ile) → **Settings → Developer settings → Fine-grained tokens → Generate new token** (doğrudan: github.com/settings/personal-access-tokens/new) → Repository access: yalnızca `gumus-kayit` → Permissions → **Contents: Read and write** → anahtarı bu depoda `KAYIT_PAT` olarak kaydet. Farklı bir depo kullanmak istersen iş akışındaki "Takipçi kaydı" adımına `KAYIT_DEPO: sahip/depo` eklenir. Kod: `bot/kayit.py`.

### 4. Dene
1. **Actions** sekmesi → **Gümüş paylaşımı** → **Run workflow**.
2. `tur`: reels, `deneme`: işaretli bırak → çalıştır.
3. İş bitince sayfanın altındaki **onizleme-reels** dosyasını indirip videoya bak.
4. Her şey doğruysa `deneme` işaretini kaldırıp tekrar çalıştır: bu sefer Instagram'a gerçekten paylaşır.

Bundan sonra bot kendi kendine çalışır.

---

## Kaynaklar ve lisanslar

Her kaynak herkese açık paylaşıma izin verir; şartları kaynağın gösterilmesidir. Kaynak satırları görselin altında ve Instagram açıklamasında otomatik yer alır.

| Ne | Kaynak | Şart |
|---|---|---|
| Ons gümüş, ons altın (USD, spot) | [MetalCharts API](https://metalcharts.org/api-terms), ücretsiz plan | Herkese açık gösterimde metalcharts.org kaynağı görünür olmalı. Ayda 200 istek hakkı var; bot ayda ~50 kullanır. Ücretsiz planda geçmiş veri yok. |
| Dolar/TL | [Avrupa Merkez Bankası (ECB)](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) euro referans kurları, [Frankfurter](https://frankfurter.dev) üzerinden (`/v2/providers/ecb/rates`, anahtarsız) | [ECB yeniden kullanım şartları](https://www.ecb.europa.eu/services/disclaimer/html/index.en.html): ücretsiz, ticari kullanım dahil; ECB kaynak gösterilmeli ve USD/TRY'nin EUR çaprazından hesaplandığı belirtilmeli (açıklamada otomatik yazılır). TCMB kuru Ekim 2026'da bırakıldı (ticari kullanımı yazılı izne bağlı). |
| Müzik | "Autumn Piano" – leberch, [Pixabay İçerik Lisansı](https://pixabay.com/tr/service/license/) | Videoda kullanmak serbest; müziği tek başına dağıtmak yasak. Bu yüzden depoda sadece şifreli hali (`assets/muzik.mp3.enc`) durur. |
| Pazar yorumu metni | Anthropic Claude API (`claude-sonnet-5-5`) | Yorum kişiye özel değildir ve al/sat/tut önerisi içermez; bu yüzden [Anthropic kullanım politikasındaki](https://www.anthropic.com/legal/aup) yüksek riskli finans tavsiyesi kapsamına girmez. Yapay zekâyla üretildiği görselde ve açıklamada yazılır. Pazar sabahı Claude'un web arama aracıyla haftanın haberleri derlenir (haftada en fazla 6 arama); haber kaynakları yorumun açıklamasında listelenir. |
| Yazı tipleri | Archivo, JetBrains Mono — SIL Open Font License | Lisans metinleri `assets/fonts` içinde. |
| Paylaşım | Instagram API (Instagram ile giriş), Standard Access | Uygulama yalnızca kendi hesabına paylaştığı için uygulama incelemesi gerekmez. |

ECB kuru her iş günü ~16:00 CET'de (≈17:00 TR) yayımlanır; sabah paylaşımında bir önceki iş gününün kuru kullanılır (görselde kurun tarihi yazar). Not: MetalCharts'ın `/v1/currency/` uç noktası da aynı Frankfurter/ECB kurunu verir; aylık hakkı harcamamak için kur doğrudan Frankfurter'dan alınır.

**Günlük kayıtlar:** MetalCharts'ın ücretsiz planında geçmiş veri olmadığı için bot her hafta içi paylaşımda o anki değerleri `veri/gecmis.json` dosyasına yazar ve bu dosyayı GitHub Actions önbelleğinde saklar (depoya girmez). "Önceki gün" karşılaştırması ve cumartesi özeti bu kayıtlardan hesaplanır. Önceki haftaya ait kayıt yoksa (ilk hafta ya da bot bir hafta durduysa) haftalık özet o hafta atlanır. Önbellek 7 gün hiç kullanılmazsa GitHub siler; bot düzenli çalıştığı sürece sorun olmaz.

**Müziği değiştirmek:** Yeni telifsiz mp3'ü şifreleyip eskisinin yerine koy, künyesini `assets/muzik-kunye.txt` dosyasına yaz:

```
MUZIK_ANAHTAR='parola' openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
  -in yeni.mp3 -out assets/muzik.mp3.enc -pass env:MUZIK_ANAHTAR
```

Açık mp3'ü (`assets/muzik.mp3`) asla depoya ekleme; `.gitignore` bunu engeller.

## Notlar
- **Hesaplama:** Gram gümüş TL fiyatı `ons gümüş × dolar/TL ÷ 31,1035` ile hesaplanır; Kapalıçarşı ya da banka alış-satış fiyatlarından biraz farklı olabilir.
- **Müzik:** iş akışı `assets/muzik.mp3.enc` dosyasını `MUZIK_ANAHTAR` ile açıp her videoya koyar (şu an Pixabay'den "Autumn Piano", leberch; ilk 30 sn). Değiştirmek için yukarıdaki "Müziği değiştirmek" adımları. Instagram'ın kendi müzik kütüphanesi otomatik paylaşımda ancak Facebook sayfası bağlı hesaplarda kullanılabiliyor.
- **Saatleri değiştirmek:** `.github/workflows/paylas.yml` içindeki `cron` satırları. Saatler UTC'dir (TR saati − 3). Post, haftalık özet ya da pazar yorumu saatini değiştirirsen aynı dosyadaki `"50 16 * * 1-5"` / `"50 6 * * 6"` / `"50 7 * * 0"` kontrollerini de güncelle.
- **Tasarım:** `templates/reels.html`, `templates/post.html` ve `templates/hafta.html`.
- **Rehberden kısa Reels:** her cumartesi ~14:00 (cron '50 10 * * 6') Gümüş rehberinin sıradaki bölümü 12 sn'lik müzikli Reels olur: soru, sayarak gelen büyük cevap, ilk sayfanın formülü/ilk maddesi ve "Rehberin tamamı profilde" çağrısı (`templates/kisa.html`, `bot/main.py` → `kisa_hazirla()`). Metin bölümden üretilir. Takvim `bot/bilgi.py` → `kisa_takvim()` (17 Ekim 2026'dan itibaren cumartesi n → bölüm n; `python bot/bilgi.py kisa-takvim`). Elle: Run workflow → tür: kisa, konu: <no>.
- **Aylık özet:** ayın rehber gönderisi olmayan ilk iş günü ~14:00'te (rehberle aynı zamanlı çalışma; `bot/aylik.py` gün seçer, ilki 2 Kasım 2026) önceki ayın özeti hareketli Reels ve hikâye olarak gider: ay sonu gram fiyatı, önceki ayın son değerine göre değişim, ayın grafiği, en yüksek/en düşük, parite ve dolar/TL. Kayıtlardan hesaplanır (MetalCharts hakkı harcanmaz); ayda 5'ten az kayıt varsa atlanır. Önceki aya ait kayıt yoksa (Ekim 2026) ayın ilk kaydına göre hesaplanır. %8'den büyük aylık harekette manşet çıkar (`BUYUK_HAREKET_AYLIK`). Tasarım `templates/ay.html`; elle: Run workflow → tür: ay. Yerelde örnek: `python bot/main.py hazirla --tur ay --cikti <klasör> --ornek` (kısmi ay için `ORNEK_KISMI=1`).
- **Bilgi sayfası:** her paylaşımda `bot/sayfa.py` GitHub Pages adresinin ana sayfasını (https://ridvancoskun1975-cpu.github.io/gumus-bot/) son kayıtlarla yeniden üretir: gram fiyatı, ons, dolar/TL, parite, gram ↔ TL hesap makinesi, son günlerin grafiği ve tablosu, hesaplama yöntemi, yayımlanmış Gümüş rehberi bölümleri, kaynaklar ve yasal bilgi. WhatsApp/Instagram bağlantı önizlemesi için `og.png` (1200×630) çizilir. Sayfa çerez ve dış istek kullanmaz; yazı tipleri sitenin içindedir. Tasarım `templates/sayfa.html` ve `templates/sayfa-og.html`. Yerelde örnekle: `python bot/sayfa.py --cikti <klasör> --ornek`. Hata verirse iş akışında yalnızca uyarı çıkar, paylaşım etkilenmez.
- **Reels kapağı:** her fiyat paylaşımı için `templates/kapak.html` ile 1080×1920 JPEG kapak üretilir (tarih, gram fiyatı, değişim; profil ızgarasının gördüğü orta alanda büyük) ve `cover_url` ile gönderilir. Kapak alınamazsa ya da Instagram işleyemezse paylaşım kapaksız yeniden denenir ve videonun son karelerinden biri kullanılır.
- **Açıklama soruları:** 20:00 özeti için güne göre dönen sorular `bot/main.py` → `SORULAR_OZET`; şimdilik kapalı (`SORU_ACIK = False`, takipçi artınca açılacak). Büyük hareket günlerinde açıklamaya "Gümüşü takip eden bir tanıdığınıza gönderebilirsiniz." satırı eklenir; düzenli günler için `PAYLASIM_GUNLERI`.
- **Büyük hareket manşeti:** gram gümüş önceki iş gününe göre %2'den (haftalık özette önceki haftaya göre %5'ten) fazla oynarsa görselde "GRAM GÜMÜŞ" başlığının yerine renkli manşet çıkar ("Gümüş bugün %3,1 yükseldi") ve açıklama bu manşetle başlar. Eşikler `bot/main.py` → `BUYUK_HAREKET_GUNLUK` / `BUYUK_HAREKET_HAFTALIK`.
- **Günlük başlık:** hafta içi fiyat paylaşımlarında (Reels ~10:00, özet ~20:00) o günün verisinden kurallı bir başlık çıkarsa görselde "GRAM GÜMÜŞ" başlığının yerine, kapakta ve açıklamanın ilk satırında yer alır: "Üst üste 3. gün yükseliş", "3 günlük düşüş sona erdi", "Son 1 haftanın en yükseği" (2 hafta, 3 hafta, 1 ay … 1 yıl; en düşüğü de), "Haftaya yükselişle başladı", "100 liranın altına indi", "Yeniden 100 liranın üzerinde". Hiçbir kural tutmazsa görsel eskisi gibi kalır. Hepsi botun kendi günlük kayıtlarından hesaplanan olgulardır, tahmin içermez; bir pencere ("son 1 ayın") ancak kayıtlar o pencereyi baştan sona kapsıyorsa yazılır ve açıklamaya dayanak notu eklenir. Öncelik: özel gün > büyük hareket manşeti > günlük başlık. Kurallar ve ayarlar `bot/baslik.py` (`PENCERELER`, `SERI_ALT`, `ESIK_ADIM`, `ESIK_SAKIN`), sınama `python bot/test_baslik.py`, görünüm `templates/ortak.css` → `.gun-baslik`.
- **Özel gün görseli (eşik ve en yüksek):** gram gümüş yuvarlak bir eşiği (10 ₺'lik adımlar: 100, 110 …) kayıtlarda ilk kez aşarsa ya da en az bir aylık en yükseğine çıkarsa o saatteki paylaşım (Reels ya da özet; ek paylaşım yapılmaz) özel görselle gider: büyük manşet ("Gram gümüş 100 lirayı aştı" / "Gram gümüş son 1 ayın en yükseğinde"), sayan fiyat, son günlerin grafiği ve aşılan eşiğin ya da önceki en yükseğin kesikli çizgisi (`templates/ozel.html`, 10 sn). Aynı ya da daha geniş pencereli bir en yüksek son 5 iş gününde zaten paylaşıldıysa özel görsel yinelenmez (günlük başlık olarak çıkar). "Kayıtlarımızda ilk kez" ifadesi ancak kayıtlar en az 30 günü kapsıyorsa yazılır; kayıtlar 13 Ekim 2026'da başladığı için "rekor" ya da "tarihinde ilk kez" denmez. Ayarlar `bot/baslik.py` → `ESIK_ADIM`, `OZEL_PENCERE`, `OZEL_ARA`, `ILK_KEZ_GUN`; grafik `bot/main.py` → `ozel_grafik()`. Yerelde örnek: `ORNEK_SENARYO=esik python bot/main.py hazirla --tur reels --cikti <klasör> --ornek` (senaryolar: seri, donus, yuksek, dusuk, esik-alti, esik, zirve).
- **Hareketli video:** üç şablon da `templates/hareket.js` dosyasını içerir. Bot her kare için `window.kare(t)` çağırır ve kareleri tarayıcıda çizip ffmpeg'e akıtır (30 kare/sn): fiyat önceki değerden (önceki iş günü ya da önceki hafta) bugüne sayar, parite ve dolar kayarak gelir, başlıktaki nokta atar, gümüş parıltısı iki kez geçer; haftalıkta grafik soldan sağa çizilir. Şablonda `window.kare` yoksa ya da veri eksikse eski durağan video üretilir. Kapak son karelerden alınır (`meta.json` → `kapak_ms`, Instagram'a `thumb_offset`). PNG görsel her zaman son hâldir.
- **Gümüş rehberi (bilgi gönderileri):** fiyat verisi kullanmayan, sürekli devam eden kaydırmalı seri (kapak + 3 sayfa, müziksiz). Metinler `bot/bilgi.py` → `BOLUMLER`, tasarım `templates/bilgi.html`. Takvim `bot/bilgi.py` → `takvim()`: ilk 6 bölüm 14–21 Ekim 2026 her iş günü, sonrası salı ve perşembe (`DUZENLI_GUNLER`; haftada 1 için `{1}`). Yeni bölümü `BOLUMLER`'in sonuna eklemek yeter, sıradaki salı/perşembeye kendiliğinden yerleşir; `python bot/bilgi.py takvim` tarihleri gösterir. Zamanlı çalışma hafta içi 13:50 TR'de başlar; o gün bölüm yoksa "kontrol" işi birkaç saniyede biter. Elle göndermek ya da önizlemek için **Run workflow → tür: bilgi, konu: <no>**.
- **Pazar yapay zekâ yorumu:** her pazar ~11:00 (cron `50 7 * * 0`) kapak + kısa (1–4 hafta), orta (1–6 ay), uzun (1 yıl+) vade sayfası. Rakamlar (değişim yüzdeleri) koddan, yorum metni Claude'dan gelir. Kod `bot/yorum.py`, tasarım `templates/yorum.html`.
  - **Pazar günü bütün verilerle şekillenir:** (1) MetalCharts'tan o anki fiyat alınır (hafta sonu = haftanın kapanışı, cuma 20:00 kaydından sonraki saatleri de kapsar; 1 istek, kayıt dosyasına yazılmaz). (2) Claude web aramasıyla haftanın gelişmelerini kaynaklı olarak derler: gümüşün haftalık seyri, dolar ve faiz, sanayi talebi ve arz, Türkiye (dolar/TL, TCMB), son üç ay/bir yıllık bağlam, önümüzdeki haftanın takvimi. Forum ve sosyal medya sonuçları engelli (`ENGELLI_SITELER`). (3) Yorum; günlük kayıtlar, kapanış, 13 aylık dolar/TL ve bu özetle birlikte yazılır. Haber taraması başarısız olursa yorum yalnızca fiyat ve kur verileriyle yazılır ve açıklamada öyle belirtilir. Haber özeti iş akışı günlüğüne ve `meta.json`'a (`gelismeler`) yazılır.
  - **Yasal çerçeve:** SPK III-37.1 Tebliğ'in medya ve elektronik ortamdaki yorumlara uygulanan ilkeleri (md. 78-80) esas alındı: yönlendirici değil (al/sat/tut, hedef fiyat, destek/direnç yok), tahminler koşullu ve iki yönlü, varsayımlar, veri tarihi, kaynaklar ve güncelleme sıklığı açıklamada, standart "yatırım danışmanlığı kapsamında değildir" uyarısı açıklamada, "yapay zekâ ile üretilmiştir" ibaresi görselde.
  - **Denetim:** model çıktısı yayımlanmadan önce kodla denetlenir: rakam, yüzde, al/sat/tut, fırsat, hedef, kesin/garanti ve kelime sınırı. Kurum ve olay adları (Fed, TCMB, seçim, savaş, gümrük vergisi…) yalnızca o haftanın haber özetinde geçiyorsa kullanılabilir (`OLAY_GRUPLARI`); özet yoksa hiç kullanılamaz. Kurala uymazsa hatalar gösterilerek 2 kez yeniden istenir; yine uymazsa iş hata verir ve **paylaşım yapılmaz**. Yasak ifadeler `bot/yorum.py → YASAK`, araştırma talimatı `ARASTIRMA_SISTEM` ve `_arastirma_istegi()`.
  - **Veri:** botun kendi günlük kayıtları (`veri/gecmis.json`, ~2 yıl tutulur) + pazar günkü kapanış fiyatı + 13 aylık ECB dolar/TL + haftanın haberleri. MetalCharts ücretli plana (Starter, 1 yıl geçmiş) geçilirse bot geçmişi kendiliğinden kullanır; ücretsiz planda geçmiş isteği 403 döner ve hakka sayılmaz. Kayıtlar 12 Ekim 2026'da başladığı için orta ve uzun vadede gram/ons değişimi bir süre "—" görünür; yorum bunu açıkça söyler ve o vadeleri haber özetindeki uzun dönem bağlamla yazar.
  - **Maliyet:** haftada 2 Claude çağrısı + en fazla 6 web araması (arama başına 1 sent); ayda yaklaşık 1 dolar.
  - **Deneme:** Run workflow → tür: yorum, deneme işaretli. Önizleme `onizleme-yorum` içinde; `meta.json` modelin ham yanıtını ve hesaplanan değerleri de içerir.
- **Yasal bilgilendirme (profilde sabit gönderi):** metni `bot/yasal.py`, tasarımı `templates/yasal.html`. Kaydırmalı 5 görsel olarak paylaşılır (Instagram API kaydırmalı gönderiye müzik eklemeye izin vermiyor). Metni değiştirirsen `GUNCELLEME` tarihini de güncelle, sonra **Actions → Gümüş paylaşımı → Run workflow → tür: yasal** ile yeniden paylaş; eski gönderinin sabitlemesini kaldırıp yenisini Instagram uygulamasından sabitle (API sabitlemeyi desteklemiyor).
