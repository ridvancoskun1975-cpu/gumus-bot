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

function nobet() {
  var simdi = new Date();
  var gun = Utilities.formatDate(simdi, SAAT_DILIMI, 'yyyy-MM-dd');
  var hg = Number(Utilities.formatDate(simdi, SAAT_DILIMI, 'u'));   // 1 pazartesi … 7 pazar
  var saat = Utilities.formatDate(simdi, SAAT_DILIMI, 'HH:mm');
  var ozellik = PropertiesService.getScriptProperties();
  temizle_(ozellik, gun);
  for (var i = 0; i < DILIMLER.length; i++) {
    var d = DILIMLER[i];
    if (d.gunler.indexOf(hg) < 0 || saat < d.bas || saat >= d.son) continue;
    var anahtar = 'gonderildi:' + gun + ':' + d.dilim;
    if (ozellik.getProperty(anahtar)) continue;
    var sonuc = baslat_(d.dilim, false);
    if (sonuc.ok) {
      ozellik.setProperty(anahtar, saat);
      console.log(d.ad + ' başlatıldı (' + saat + ' TR).');
    } else {
      console.warn(d.ad + ' başlatılamadı: ' + sonuc.neden);
      if (dakika_(d.son) - dakika_(saat) <= SON_UYARI_DK && !ozellik.getProperty('uyari:' + anahtar)) {
        ozellik.setProperty('uyari:' + anahtar, saat);
        MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
          '⚠️ Gümüş dış tetik: ' + d.ad + ' başlatılamadı',
          gun + ' ' + saat + ' TR: ' + d.ad + ' paylaşımı GitHub\'da başlatılamadı (' + sonuc.neden + ').\n' +
          'Nöbetçiler yine bakacak. Bir Claude sohbetinde "dış tetik hata verdi" yazman yeter.');
      }
    }
  }
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
        payload: JSON.stringify({ref: 'main', inputs: {dilim: dilim, deneme: deneme ? 'true' : 'false', onay: 'false'}}),
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
    var m = /^(?:uyari:)?gonderildi:(\d{4}-\d{2}-\d{2}):/.exec(k);
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
