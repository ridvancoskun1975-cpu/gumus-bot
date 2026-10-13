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
3. (İsteğe bağlı) Aynı sayfada **Variables** sekmesi → `HESAP_ADI` → görsellerde yazacak kullanıcı adı. Boş bırakırsan bot hesabından otomatik alır.

**ANTHROPIC_API_KEY nasıl alınır:** **platform.claude.com** (Claude Console) → hesap aç → **Billing** bölümünden kredi yükle (en düşük tutar yeterli) → **API keys → Create key** → anahtarı `ANTHROPIC_API_KEY` olarak kaydet. Haftada tek çağrı yapılır; maliyeti ayda birkaç sente denk gelir. İstersen Console'da aylık harcama sınırı koy. Model varsayılanı `claude-sonnet-5-5`; değiştirmek için **Variables** sekmesinde `YZ_MODEL`.

**GH_PAT nasıl alınır:** GitHub → sağ üstte profil → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Repository access: sadece bu depo. Permissions → **Secrets: Read and write**. Süreyi en uzun seç, oluşan anahtarı `GH_PAT` olarak kaydet.

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
| Pazar yorumu metni | Anthropic Claude API (`claude-sonnet-5-5`) | Yorum kişiye özel değildir ve al/sat/tut önerisi içermez; bu yüzden [Anthropic kullanım politikasındaki](https://www.anthropic.com/legal/aup) yüksek riskli finans tavsiyesi kapsamına girmez. Yapay zekâyla üretildiği görselde ve açıklamada yazılır. Model internete çıkmaz, yalnızca yukarıdaki fiyat ve kur verilerini görür. |
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
- **Saatleri değiştirmek:** `.github/workflows/paylas.yml` içindeki `cron` satırları. Saatler UTC'dir (TR saati − 3). Post ya da haftalık özet saatini değiştirirsen aynı dosyadaki `"50 16 * * 1-5"` / `"50 6 * * 6"` kontrollerini de güncelle.
- **Tasarım:** `templates/reels.html`, `templates/post.html` ve `templates/hafta.html`.
- **Gümüş rehberi (bilgi gönderileri):** fiyat verisi kullanmayan, sürekli devam eden kaydırmalı seri (kapak + 3 sayfa, müziksiz). Metinler `bot/bilgi.py` → `BOLUMLER`, tasarım `templates/bilgi.html`. Takvim `bot/bilgi.py` → `takvim()`: ilk 6 bölüm 14–21 Ekim 2026 her iş günü, sonrası salı ve perşembe (`DUZENLI_GUNLER`; haftada 1 için `{1}`). Yeni bölümü `BOLUMLER`'in sonuna eklemek yeter, sıradaki salı/perşembeye kendiliğinden yerleşir; `python bot/bilgi.py takvim` tarihleri gösterir. Zamanlı çalışma hafta içi 13:50 TR'de başlar; o gün bölüm yoksa "kontrol" işi birkaç saniyede biter. Elle göndermek ya da önizlemek için **Run workflow → tür: bilgi, konu: <no>**.
- **Pazar yapay zekâ yorumu:** her pazar ~11:00 (cron `50 7 * * 0`) kapak + kısa (1–4 hafta), orta (1–6 ay), uzun (1 yıl+) vade sayfası. Rakamlar (değişim yüzdeleri) koddan, yorum metni Claude'dan gelir. Kod `bot/yorum.py`, tasarım `templates/yorum.html`.
  - **Yasal çerçeve:** SPK III-37.1 Tebliğ'in medya ve elektronik ortamdaki yorumlara uygulanan ilkeleri (md. 78-80) esas alındı: yönlendirici değil (al/sat/tut, hedef fiyat, destek/direnç yok), tahminler koşullu ve iki yönlü, varsayımlar, veri tarihi, kaynaklar ve güncelleme sıklığı açıklamada, standart "yatırım danışmanlığı kapsamında değildir" uyarısı açıklamada, "yapay zekâ ile üretilmiştir" ibaresi görselde.
  - **Denetim:** model çıktısı yayımlanmadan önce kodla denetlenir: rakam, yüzde, al/sat/tut, fırsat, hedef, kesin/garanti, güncel olay (Fed, TCMB, seçim, savaş…) ve kelime sınırı. Kurala uymazsa hatalar gösterilerek 2 kez yeniden istenir; yine uymazsa iş hata verir ve **paylaşım yapılmaz**. Yasak ifadeler `bot/yorum.py → YASAK`.
  - **Veri:** botun kendi günlük kayıtları (`veri/gecmis.json`, ~2 yıl tutulur) + 13 aylık ECB dolar/TL. MetalCharts ücretli plana (Starter, 1 yıl geçmiş) geçilirse bot geçmişi kendiliğinden kullanır; ücretsiz planda geçmiş isteği 403 döner ve hakka sayılmaz. Kayıtlar 12 Ekim 2026'da başladığı için orta ve uzun vadede gram/ons değişimi bir süre "—" görünür; yorum bunu açıkça söyler.
  - **Deneme:** Run workflow → tür: yorum, deneme işaretli. Önizleme `onizleme-yorum` içinde; `meta.json` modelin ham yanıtını ve hesaplanan değerleri de içerir.
- **Yasal bilgilendirme (profilde sabit gönderi):** metni `bot/yasal.py`, tasarımı `templates/yasal.html`. Kaydırmalı 5 görsel olarak paylaşılır (Instagram API kaydırmalı gönderiye müzik eklemeye izin vermiyor). Metni değiştirirsen `GUNCELLEME` tarihini de güncelle, sonra **Actions → Gümüş paylaşımı → Run workflow → tür: yasal** ile yeniden paylaş; eski gönderinin sabitlemesini kaldırıp yenisini Instagram uygulamasından sabitle (API sabitlemeyi desteklemiyor).
