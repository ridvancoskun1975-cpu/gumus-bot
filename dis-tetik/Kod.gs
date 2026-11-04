/**
 * Gümüş paylaşımı dış tetiği (Google Apps Script, Rıdvan'ın Google hesabında).
 *
 * Neden (4 Kasım 2026, Rıdvan "A başla. Kontrollü git"): GitHub'ın zamanlayıcısı 3 Kasım'da paylaşımları 5,5–8 saat
 * geç başlattı, 4 Kasım'da hiç başlatmadı. Dışarıdan gönderilen "başlat" isteği (workflow_dispatch) ise saniyeler
 * içinde çalışıyor. Bu betik her 10 dakikada bir saate bakar; bir paylaşım diliminin penceresindeyse ve o dilim bugün
 * henüz başlatılmadıysa paylas.yml'yi "dilim" girdisiyle başlatır. O çalışma zamanlı çalışmanın aynısıdır: türü
 * dilimden belirlenir, hedef saate kadar bekler (~10:00 / ~14:00 / ~20:00), iki çift paylaşım kilidi ve günlük sınır
 * aynen geçerlidir. GitHub cron'ları ve nöbetçiler yedek olarak kalır.
 *
 * Kurulum (bir kez): Proje ayarları → Komut dosyası özellikleri → GITHUB_TOKEN = yalnız gumus-bot deposunda
 * "Actions: Read and write" yetkili ince GitHub anahtarı. Sonra kur() bir kez çalıştırılır (izin penceresi onaylanır).
 * Deneme: dene() paylaşmayan bir çalıştırma başlatır. Kapatmak: kaldir().
 *
 * Pencere sonu denetimi (gözden geçirme, 4 Kasım 2026): GitHub başlatmayı kabul ettikten sonra çalışma iptal olabilir
 * (aynı gruba yeni bir çalışma girerse) ya da hata verebilir. Pencere bittikten sonraki 15 dakikada betik bir kez
 * bakar: pencereden bu yana paylaşım iş akışında süren ya da başarıyla biten bir çalışma yoksa o dilimi bir kez daha
 * başlatır. Paylaşım gittiyse ikinci çalışma iki kilide takılıp paylaşmadan biter.
 * deneme ve onay gerçek true/false olarak gönderilir (yazı olarak "false" değil; GitHub'ın yazıyı nasıl okuduğu belirsiz).
 * DILIMLER, paylas.yml cron'ları ve bot/program.py → HEDEF_SAATLERI ile uyumlu olmalı: python bot/test_dis_tetik.py.
 */

var DEPO = 'ridvancoskun1975-cpu/gumus-bot';
var IS_AKISI = 'paylas.yml';
var SAAT_DILIMI = 'Europe/Istanbul';

// gunler: 1 pazartesi … 7 pazar (TR). bas–son: başlatma penceresi (TR, son hariç). dilim: paylas.yml'deki cron.
// Pencere cron saatinden sonra başlar, hedef saatten (09:55 / 13:55 / 19:55 / 10:55) en az 10 dk önce biter; bot
// pencere içinde nerede başlarsa başlasın hedefe kadar bekler (en çok 40 dk).
var DILIMLER = [
  {ad: 'sabah Reels', gunler: [1, 2, 3, 4, 5], bas: '09:15', son: '09:45', dilim: '10 6 * * 1-5'},
  {ad: 'rehber / aylık özet', gunler: [1, 2, 3, 4, 5], bas: '13:15', son: '13:45', dilim: '10 10 * * 1-5'},
  {ad: 'akşam özeti', gunler: [1, 2, 3, 4, 5], bas: '19:15', son: '19:45', dilim: '10 16 * * 1-5'},
  {ad: 'haftalık özet', gunler: [6], bas: '09:15', son: '09:45', dilim: '10 6 * * 6'},
  {ad: 'pazar yorumu', gunler: [7], bas: '10:15', son: '10:45', dilim: '10 7 * * 0'}
];
var SON_UYARI_DK = 10;   // pencerenin son 10 dakikasında hâlâ başlatılamadıysa Rıdvan'a e-posta
var DENETIM_DK = 15;     // pencere bittikten sonraki 15 dakikada bir kez denetim (tetik 10 dakikada bir; en az biri düşer)

function nobet() {
  var simdi = new Date();
  var gun = Utilities.formatDate(simdi, SAAT_DILIMI, 'yyyy-MM-dd');
  var hg = Number(Utilities.formatDate(simdi, SAAT_DILIMI, 'u'));   // 1 pazartesi … 7 pazar
  var saat = Utilities.formatDate(simdi, SAAT_DILIMI, 'HH:mm');
  var ozellik = PropertiesService.getScriptProperties();
  temizle_(ozellik, gun);
  for (var i = 0; i < DILIMLER.length; i++) {
    var d = DILIMLER[i];
    if (d.gunler.indexOf(hg) < 0) continue;
    var anahtar = 'gonderildi:' + gun + ':' + d.dilim;
    if (saat >= d.bas && saat < d.son) {
      if (ozellik.getProperty(anahtar)) continue;
      var sonuc = baslat_(d.dilim, false);
      if (sonuc.ok) {
        ozellik.setProperty(anahtar, saat);
        console.log(d.ad + ' başlatıldı (' + saat + ' TR).');
      } else {
        console.warn(d.ad + ' başlatılamadı: ' + sonuc.neden);
        if (dakika_(d.son) - dakika_(saat) <= SON_UYARI_DK) uyar_(ozellik, anahtar, gun, saat, d, sonuc.neden);
      }
    } else if (dakika_(saat) >= dakika_(d.son) && dakika_(saat) < dakika_(d.son) + DENETIM_DK) {
      denetle_(ozellik, anahtar, gun, saat, d);
    }
  }
}

/** Pencere sonu denetimi: bu dilim için süren ya da başarıyla biten çalışma yoksa bir kez daha başlatır. */
function denetle_(ozellik, anahtar, gun, saat, d) {
  var dAnahtar = 'denetlendi:' + gun + ':' + d.dilim;
  if (ozellik.getProperty(dAnahtar)) return;
  ozellik.setProperty(dAnahtar, saat);
  var durum = calisma_durumu_(gun, d.bas);
  if (durum.hata) {
    console.warn(d.ad + ' denetimi: çalışmalar okunamadı (' + durum.hata + ').');
    if (ozellik.getProperty(anahtar)) return;   // başlatılmıştı; okunamayınca dokunma, nöbetçiler bakar
  } else if (durum.var) {
    console.log(d.ad + ' denetimi: çalışma ' + durum.var + '; ek başlatma yok.');
    return;
  }
  var sonuc = baslat_(d.dilim, false);
  if (sonuc.ok) {
    if (!ozellik.getProperty(anahtar)) ozellik.setProperty(anahtar, saat);
    console.log(d.ad + ' denetimi: süren ya da başarılı çalışma yoktu, bir kez daha başlatıldı (' + saat + ' TR).');
  } else {
    console.warn(d.ad + ' denetimi: yeniden başlatılamadı: ' + sonuc.neden);
    uyar_(ozellik, anahtar, gun, saat, d, sonuc.neden);
  }
}

/** Pencere başından 10 dk önceden (dilimin cron'u) bu yana paylas.yml çalışmaları: {var: 'sürüyor' | 'başarıyla bitti'},
 *  {} (yok) ya da {hata: neden}. Yalnız okur. */
function calisma_durumu_(gun, bas) {
  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) return {hata: 'GITHUB_TOKEN özelliği yok'};
  var basla = new Date(Utilities.parseDate(gun + ' ' + bas, SAAT_DILIMI, 'yyyy-MM-dd HH:mm').getTime() - 10 * 60000);
  var url = 'https://api.github.com/repos/' + DEPO + '/actions/workflows/' + IS_AKISI + '/runs?per_page=30&created=' +
    encodeURIComponent('>=' + basla.toISOString().slice(0, 19) + 'Z');
  try {
    var yanit = UrlFetchApp.fetch(url, {
      method: 'get',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      muteHttpExceptions: true
    });
    var kod = yanit.getResponseCode();
    if (kod !== 200) return {hata: 'HTTP ' + kod + ' ' + yanit.getContentText().slice(0, 200)};
    var calismalar = JSON.parse(yanit.getContentText()).workflow_runs || [];
    for (var j = 0; j < calismalar.length; j++) {
      if (calismalar[j].status !== 'completed') return {var: 'sürüyor'};
      if (calismalar[j].conclusion === 'success') return {var: 'başarıyla bitti'};
    }
    return {};
  } catch (e) {
    return {hata: String(e).slice(0, 200)};
  }
}

/** Dilim başına en çok bir e-posta. */
function uyar_(ozellik, anahtar, gun, saat, d, neden) {
  if (ozellik.getProperty('uyari:' + anahtar)) return;
  ozellik.setProperty('uyari:' + anahtar, saat);
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
    '⚠️ Gümüş dış tetik: ' + d.ad + ' başlatılamadı',
    gun + ' ' + saat + ' TR: ' + d.ad + ' paylaşımı GitHub\'da başlatılamadı (' + neden + ').\n' +
    'Nöbetçiler yine bakacak. Bir Claude sohbetinde "dış tetik hata verdi" yazman yeter.');
}

function baslat_(dilim, deneme) {
  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) return {ok: false, neden: 'GITHUB_TOKEN özelliği yok'};
  try {
    var yanit = UrlFetchApp.fetch(
      'https://api.github.com/repos/' + DEPO + '/actions/workflows/' + IS_AKISI + '/dispatches', {
        method: 'post',
        contentType: 'application/json',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Accept': 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28'
        },
        // deneme ve onay gerçek true/false (yazı değil): paylas.yml'de inputs.deneme == false karşılaştırılır
        payload: JSON.stringify({ref: 'main', inputs: {dilim: dilim, deneme: !!deneme, onay: false}}),
        muteHttpExceptions: true
      });
    var kod = yanit.getResponseCode();
    if (kod === 204 || kod === 200) return {ok: true};
    return {ok: false, neden: 'HTTP ' + kod + ' ' + yanit.getContentText().slice(0, 200)};
  } catch (e) {
    return {ok: false, neden: String(e).slice(0, 200)};
  }
}

function dakika_(hhmm) {
  var p = hhmm.split(':');
  return Number(p[0]) * 60 + Number(p[1]);
}

function temizle_(ozellik, bugun) {
  var hepsi = ozellik.getProperties();
  for (var k in hepsi) {
    var m = /^(?:uyari:)?(?:gonderildi|denetlendi):(\d{4}-\d{2}-\d{2}):/.exec(k);
    if (m && m[1] < bugun) ozellik.deleteProperty(k);
  }
}

/** Bir kez çalıştırılır: her 10 dakikada bir nobet(). Eskisi varsa silinir (iki tetik olmasın). */
function kur() {
  kaldir();
  ScriptApp.newTrigger('nobet').timeBased().everyMinutes(10).create();
  console.log('Kuruldu: nobet() her 10 dakikada bir çalışacak.');
}

function kaldir() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'nobet') ScriptApp.deleteTrigger(t);
  });
}

/** Paylaşmayan deneme: akşam diliminin çalışmasını deneme olarak başlatır (bekleme yok, Instagram'a gitmez). */
function dene() {
  var sonuc = baslat_('10 16 * * 1-5', true);
  console.log(sonuc.ok ? 'Deneme başlatıldı; GitHub → Actions → Gümüş paylaşımı.' : 'Deneme başlatılamadı: ' + sonuc.neden);
}
