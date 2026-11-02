# Site tanıtım (reklam) videosu — kaynaklar

2 Kasım 2026. Rıdvan: "3 boyutlu gümüş etrafında dönen kamera … sloganlar … takip edin"; metin "Gümüş sırtlı goril takipte. Ya siz?", açılış "Gümüş bugün kaç lira?" (Rıdvan "2"); ses Orus (Rıdvan "Ses 1"), hız 1,15, reklam spikeri üslubu; dikey 9:16.

- `kulce.html` — 1. sahne (0–5 sn): Three.js ile gümüş külçe piramidi, 13 Ekim 3B profil resmindeki gibi (döküm biçimi: üst geniş alt dar; canvas ile çizilen "SILVER 999.9 FINE" damgası ve çerçeve, kabartma + pürüz haritası; uzun kenar derinlikte, 3-2-1), soldan dolaşan kamera, stüdyo ışık çevresi (Rıdvan 2 Kasım 15:38: "Böyle bir külçe standardı yok").
- `sahne2.html` — 2. sahne (5–11 sn): program (~10:00 güncel fiyat, ~20:00 günün özeti, pazar üst düzey yapay zekâ analizi; kısa ve orta vade).
- `sahne3.html` — 3. sahne (11–16 sn): "Gümüş sırtlı goril takipte. Ya siz?", istifçi goril (templates/goril/istif.svg/js kopyası), Takip edin, @hesap, site, yasal satır + "Seslendirme: yapay zekâ".
- `render.mjs` — sahneyi 30 fps JPEG kare akışıyla ffmpeg'e çizer (`node render.mjs <html> <sn> <mp4> [fadein] [fadeout]`); `kare.mjs` tek kare.
- Ses: `python bot/ses.py ornek --sesler Orus --metin "a || b || c || d" --hiz 1.15 --uslup "<reklam üslubu>"` (ses-ornek.yml iş akışı; parçalar 0,8 / 5,3 / 11,2 / 13,9 sn'ye yerleştirildi).
- Müzik: gumus-kayit/muzik Motivate (NastelBom, Pixabay), 1:47'den 16 sn, %20 ses. Geçiş sesleri: Mixkit (whoosh-fast, transition-snap; Mixkit SFX Free License).
- Çalışma ortamı: Playwright Chromium (`--use-gl=angle --use-angle=swiftshader --allow-file-access-from-files`), `npm i three@0.170.0`, fontlar assets/fonts, goril templates/goril.
- Yatay (16:9) sürüm: `*-yatay.html` sahneleri, `W=1920 H=1080` ile render; ses izi dikey videodan kopyalanır (Rıdvan 2 Kasım 13:50: "Instagram reklamı ve Google reklamı olarak").
