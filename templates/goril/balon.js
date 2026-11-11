/* © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE */
// Goril balonu (bot/insan.py, #33): videoda goril sahneye girdikten sonra küçük bir sıçramayla açılır ve ok ucu
// gorilin başını gösterir (Rıdvan, 11 Kasım 2026: "goril gezerken ve konuşma baloncuğu ile birlikte bir video görmek
// istiyorum"; ilk denemede balon ilk kareden görünüyor, goril 1,3 sn'de giriyordu). Balon yerinde durur: gorilin
// peşinden kayarsa Reels düğmelerine (sağdaki 170 px) taşabilirdi.
// Bot her kare için window.kare(t) çağırır; çağrılmazsa (durağan görsel, kapak, yerleşim denetimi) balon açık durur.
(function () {
  const balon = document.getElementById('goril-balon');
  const ok = document.getElementById('goril-balon-ok');
  if (!balon) return;
  // Rıdvan, 12 Kasım 2026 00:03: "goril sola doğru olan ekrana girme hareketini bitirince ortaya çıkmalı" →
  // gezinen goril girişini 3,5 sn'de bitirir; balon 3,2 sn'de açılmaya başlar, duruşla birlikte tamamlanır.
  const GIRIS = 3.2, ACILIS = 0.35;
  // "baloncuk biraz daha sağda gorilin kafasına yakın olmalı": balon Reels düğmelerinin (sağdaki 170 px) dışında
  // durur, ok eğilir: tabanı balonun içinde, ucu her karede gorilin başının üstünde.
  const OK_EN_UZUN = 140, OK_EN_KISA = 24, OK_PAYI = 12, KENAR = 26;
  const kenet = (x, a, b) => Math.min(Math.max(x, a), b);
  balon.style.transformOrigin = '82% 100%';
  let boy = OK_EN_KISA, yan = 14;

  function bas() {
    // gorilin bedeninin (class="goril-beden") en üst parçası: ortası ve üstü; yoksa maskot kutusu
    let r = null;
    for (const p of document.querySelectorAll('.maskot .goril-beden')) {
      const b = p.getBoundingClientRect();
      if (b.width > 0 && (!r || b.top < r.top)) r = b;
    }
    if (!r) { const m = document.querySelector('.maskot'); r = m && m.getBoundingClientRect(); }
    return r ? {x: r.left + r.width / 2, ust: r.top} : null;
  }

  function okCiz() {
    if (!ok) return;
    const g = bas();
    const kutu = balon.getBoundingClientRect();
    const olcek = kutu.width / balon.offsetWidth || 1;
    const w = balon.offsetWidth;
    const hx = g ? (g.x - kutu.left) / olcek : w - 58;
    const taban = kenet(hx, KENAR + yan, w - KENAR - yan);
    const uc = kenet(hx, -40, w + 80);
    ok.setAttribute('points', `${taban - yan},-2 ${taban + yan},-2 ${uc},${boy}`);
  }

  function okBoyu() {
    // ok ucu gorilin başının biraz üstüne kadar uzar (durağan pozdaki baş)
    const g = bas();
    const kutu = balon.getBoundingClientRect();
    const olcek = kutu.height / balon.offsetHeight || 1;
    if (g) boy = kenet((g.ust - kutu.bottom - OK_PAYI) / olcek, OK_EN_KISA, OK_EN_UZUN);
    yan = Math.max(14, Math.round(boy * 0.18));
    okCiz();
  }
  okBoyu();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(okBoyu);

  function ciz(t) {
    const u = kenet((t - GIRIS) / ACILIS, 0, 1);
    const e = 1 - Math.pow(1 - u, 3);
    const zipla = u > 0 && u < 1 ? Math.sin(u * Math.PI) * 0.06 : 0;
    balon.style.opacity = String(u);
    balon.style.transform = 'scale(' + (0.6 + 0.4 * e + zipla) + ')';
    if (u > 0) okCiz();
  }

  const onceki = window.kare;
  window.kare = function (t) { if (typeof onceki === 'function') onceki(t); ciz(t); };
})();
