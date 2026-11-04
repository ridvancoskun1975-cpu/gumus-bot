// Dış tetiğin (Kod.gs) davranış sınaması: Apps Script hizmetleri sahte, ağ yok. Çalıştır: node dis-tetik/test_kod.js
// (bot/test_dis_tetik.py de çağırır.) Gözden geçirme, 4 Kasım 2026: gerçek true/false ve pencere sonu denetimi.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const KOD = fs.readFileSync(path.join(__dirname, 'Kod.gs'), 'utf8');
let gecen = 0;
function esit(a, b, ad) {
  const ja = JSON.stringify(a), jb = JSON.stringify(b);
  if (ja !== jb) throw new Error(ad + ': ' + ja + ' != ' + jb);
  gecen++;
}

// Türkiye UTC+3 (yaz saati yok). tr('2026-11-04 19:20') → o anın Date'i.
function tr(s) {
  return new Date(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10), +s.slice(11, 13) - 3, +s.slice(14, 16)));
}

function ortam(github) {
  const ozellik = {GITHUB_TOKEN: 'sahte'};
  const kayit = {istekler: [], epostalar: [], gunluk: []};
  let simdi = tr('2026-11-04 00:00');
  const AsilDate = Date;
  class SahteDate extends AsilDate {
    constructor(...a) { if (a.length) super(...a); else super(simdi.getTime()); }
  }
  const p2 = n => String(n).padStart(2, '0');
  const yerel = d => new AsilDate(d.getTime() + 3 * 3600 * 1000);
  const ctx = {
    Date: SahteDate, JSON, String, Number, encodeURIComponent,
    console: {log: m => kayit.gunluk.push(m), warn: m => kayit.gunluk.push('UYARI ' + m)},
    Utilities: {
      formatDate(d, tz, bicim) {
        const y = yerel(d);
        if (bicim === 'yyyy-MM-dd') return `${y.getUTCFullYear()}-${p2(y.getUTCMonth() + 1)}-${p2(y.getUTCDate())}`;
        if (bicim === 'HH:mm') return `${p2(y.getUTCHours())}:${p2(y.getUTCMinutes())}`;
        if (bicim === 'u') return String(y.getUTCDay() || 7);
        throw new Error('biçim ' + bicim);
      },
      parseDate(metin, tz, bicim) {
        if (bicim !== 'yyyy-MM-dd HH:mm' || tz !== 'Europe/Istanbul') throw new Error('parseDate ' + bicim);
        return tr(metin);
      }
    },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: k => (k in ozellik ? ozellik[k] : null),
        setProperty: (k, v) => { ozellik[k] = v; },
        deleteProperty: k => { delete ozellik[k]; },
        getProperties: () => Object.assign({}, ozellik)
      })
    },
    UrlFetchApp: {
      fetch(url, sec) {
        const istek = {url, yontem: sec.method, govde: sec.payload ? JSON.parse(sec.payload) : null,
                       yetki: sec.headers.Authorization};
        kayit.istekler.push(istek);
        const [kod, govde] = github(istek);
        return {getResponseCode: () => kod, getContentText: () => (typeof govde === 'string' ? govde : JSON.stringify(govde))};
      }
    },
    MailApp: {sendEmail: (kime, konu, metin) => kayit.epostalar.push(konu)},
    Session: {getEffectiveUser: () => ({getEmail: () => 'rıdvan@ornek'})},
    ScriptApp: {getProjectTriggers: () => [], deleteTrigger() {}, newTrigger() { throw new Error('yok'); }}
  };
  vm.createContext(ctx);
  vm.runInContext(KOD, ctx);
  return {
    ozellik, kayit,
    tik(s) { simdi = tr(s); ctx.nobet(); },
    dene() { ctx.dene(); },
    baslatmalar: () => kayit.istekler.filter(i => i.yontem === 'post'),
    okumalar: () => kayit.istekler.filter(i => i.yontem === 'get')
  };
}

const AKSAM = '10 16 * * 1-5';
const basari = (durum, sonuc) => istek => (istek.yontem === 'post' ? [204, ''] :
  [200, {workflow_runs: durum === null ? [] : [{status: durum, conclusion: sonuc || null}]}]);

// 1) Olağan gün: pencerede bir kez başlatır; gövde gerçek true/false; denetimde süren çalışmayı görür, dokunmaz
let o = ortam(basari('in_progress'));
o.tik('2026-11-04 19:05');
esit(o.kayit.istekler.length, 0, 'pencereden önce istek yok');
o.tik('2026-11-04 19:16');
esit(o.baslatmalar().length, 1, 'pencerede başlatır');
const g = o.baslatmalar()[0].govde;
esit(g, {ref: 'main', inputs: {dilim: AKSAM, deneme: false, onay: false}}, 'gövde: dilim, deneme=false, onay=false');
esit([typeof g.inputs.deneme, typeof g.inputs.onay], ['boolean', 'boolean'], 'deneme ve onay yazı değil, gerçek true/false');
esit(o.baslatmalar()[0].url.endsWith('/repos/ridvancoskun1975-cpu/gumus-bot/actions/workflows/paylas.yml/dispatches'),
  true, 'doğru depo ve iş akışı');
o.tik('2026-11-04 19:26'); o.tik('2026-11-04 19:36');
esit(o.baslatmalar().length, 1, 'aynı pencerede ikinci kez başlatmaz');
o.tik('2026-11-04 19:46');
esit(o.okumalar().length, 1, 'pencere sonunda bir kez okur');
esit(decodeURIComponent(o.okumalar()[0].url.split('created=')[1]), '>=2026-11-04T16:05:00Z',
  'okuma: dilimin cron dakikasından (19:05 TR) bu yana');
esit(o.okumalar()[0].url.includes('/actions/workflows/paylas.yml/runs?'), true, 'okuma: paylaşım iş akışı');
esit(o.baslatmalar().length, 1, 'süren çalışma varken yeniden başlatmaz');
o.tik('2026-11-04 19:56');
esit([o.okumalar().length, o.baslatmalar().length], [1, 1], 'denetim günde dilim başına bir kez');
o.tik('2026-11-04 20:06');
esit(o.kayit.istekler.length, 2, 'denetim penceresinden sonra istek yok');
esit(o.kayit.epostalar.length, 0, 'olağan günde e-posta yok');

// 2) Çalışma iptal olmuş (gruba yeni çalışma girdi): denetim bir kez daha başlatır
o = ortam(basari('completed', 'cancelled'));
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:47'); o.tik('2026-11-04 19:57');
esit(o.baslatmalar().length, 2, 'iptal olan çalışmadan sonra bir kez daha başlatır (bir kez)');
esit(o.baslatmalar()[1].govde, {ref: 'main', inputs: {dilim: AKSAM, deneme: false, onay: false}},
  'ikinci başlatma da paylaşan dilim çalışması');

// 3) Hata vermiş çalışma da yeniden başlatılır; başarıyla bitmiş çalışma başlatılmaz
o = ortam(basari('completed', 'failure'));
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:47');
esit(o.baslatmalar().length, 2, 'hata veren çalışmadan sonra bir kez daha başlatır');
o = ortam(basari('completed', 'success'));
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:47');
esit(o.baslatmalar().length, 1, 'başarıyla bitmiş çalışma varken başlatmaz');

// 4) Çalışmalar okunamazsa: başlatılmışsa dokunmaz (nöbetçiler bakar)
o = ortam(istek => (istek.yontem === 'post' ? [204, ''] : [500, 'sunucu hatası']));
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:47');
esit(o.baslatmalar().length, 1, 'okuma hatasında yeniden başlatmaz');
esit(o.kayit.gunluk.some(m => m.includes('okunamadı')), true, 'okuma hatası günlüğe yazılır');

// 5) Pencerede hiç başlatılamadı: son 10 dakikada tek e-posta; denetimde bir kez daha dener, ikinci e-posta yok
let baslatma_tamam = false;
o = ortam(istek => (istek.yontem === 'post' ? (baslatma_tamam ? [204, ''] : [500, 'hata']) : [200, {workflow_runs: []}]));
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:26');
esit(o.kayit.epostalar.length, 0, 'pencerenin başında e-posta yok');
o.tik('2026-11-04 19:36');
esit(o.kayit.epostalar.length, 1, 'son 10 dakikada e-posta');
o.tik('2026-11-04 19:46');
esit([o.baslatmalar().length, o.kayit.epostalar.length], [4, 1], 'denetim bir kez daha dener, e-posta tekrar gitmez');
baslatma_tamam = true;
o = ortam(istek => (istek.yontem === 'post' ? (baslatma_tamam ? [204, ''] : [500, 'hata']) : [200, {workflow_runs: []}]));
baslatma_tamam = false;
o.tik('2026-11-04 19:16');
baslatma_tamam = true;
o.tik('2026-11-04 19:48');
esit([o.baslatmalar().length, o.ozellik['gonderildi:2026-11-04:' + AKSAM]], [2, '19:48'],
  'pencerede başlatılamayan dilim denetimde başlarsa kaydedilir');

// 6) Gün ve dilim seçimi
o = ortam(basari('in_progress'));
o.tik('2026-11-07 19:16');   // cumartesi akşamı
esit(o.kayit.istekler.length, 0, 'cumartesi akşam dilimi yok');
o.tik('2026-11-07 09:16');
esit(o.baslatmalar().map(i => i.govde.inputs.dilim), ['10 6 * * 6'], 'cumartesi sabahı haftalık özet');
o.tik('2026-11-08 10:20'); o.tik('2026-11-08 10:50');
esit(o.baslatmalar().map(i => i.govde.inputs.dilim), ['10 6 * * 6', '10 7 * * 0'], 'pazar 10:15–10:45 pazar yorumu');
esit(o.okumalar().length, 1, 'pazar pencere sonu denetimi');

// 7) Eski günlerin işaretleri silinir (denetim dahil); bugününkiler kalır
o = ortam(basari('in_progress'));
Object.assign(o.ozellik, {'gonderildi:2026-11-03:x': '19:16', 'denetlendi:2026-11-03:x': '19:46',
  'uyari:gonderildi:2026-11-03:x': '19:36', 'denetlendi:2026-11-04:y': '09:46'});
o.tik('2026-11-04 12:00');
esit(Object.keys(o.ozellik).sort(), ['GITHUB_TOKEN', 'denetlendi:2026-11-04:y'], 'eski işaretler temizlenir');

// 8) dene(): paylaşmayan deneme, gerçek true
o = ortam(basari('in_progress'));
o.dene();
esit(o.baslatmalar()[0].govde, {ref: 'main', inputs: {dilim: AKSAM, deneme: true, onay: false}}, 'dene(): deneme=true');

// 8b) GitHub gerçek true/false'u 422 ile reddederse bir kez yazı değerleriyle yineler; başka hatada yinelemez
o = ortam(istek => (istek.yontem === 'post' ? (typeof istek.govde.inputs.deneme === 'boolean'
  ? [422, '{"message":"For \'additionalProperties\', true is not a string."}'] : [204, '']) : [200, {workflow_runs: []}]));
o.tik('2026-11-04 19:16');
esit(o.baslatmalar().map(i => i.govde.inputs), [{dilim: AKSAM, deneme: false, onay: false},
  {dilim: AKSAM, deneme: 'false', onay: 'false'}], '422: yazı değerleriyle bir kez daha');
esit(o.ozellik['gonderildi:2026-11-04:' + AKSAM], '19:16', '422 sonrası yazıyla başlarsa kaydedilir');
o = ortam(istek => (istek.yontem === 'post' ? [500, 'hata'] : [200, {workflow_runs: []}]));
o.tik('2026-11-04 19:16');
esit(o.baslatmalar().length, 1, '500: aynı tikte yinelemez (sonraki tikte dener)');

// 8c) Denetim yalnız main dalının çalışmalarına bakar (başka daldaki denemeler sayılmaz)
o = ortam(basari('in_progress'));
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:46');
esit(o.okumalar()[0].url.includes('/runs?branch=main&'), true, 'denetim: yalnız main');

// 9) Anahtar yoksa hiçbir şey göndermez
o = ortam(basari('in_progress'));
delete o.ozellik.GITHUB_TOKEN;
o.tik('2026-11-04 19:16'); o.tik('2026-11-04 19:46');
esit(o.kayit.istekler.length, 0, 'anahtar yoksa istek yok');

console.log('test_kod.js: ' + gecen + ' sınama geçti.');
