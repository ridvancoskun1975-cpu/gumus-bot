/* © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE */
// Goril balonu (bot/insan.py, #33): videoda goril sahneye girdikten sonra küçük bir sıçramayla açılır ve ok ucu
// gorilin başını izler (Rıdvan, 11 Kasım 2026: "goril gezerken ve konuşma baloncuğu ile birlikte bir video görmek
// istiyorum"; ilk denemede balon ilk kareden görünüyor, goril 1,3 sn'de giriyordu). Balon yerinde durur: gorilin
// peşinden kayarsa Reels düğmelerine (sağdaki 170 px) taşabilirdi.
// Bot her kare için window.kare(t) çağırır; çağrılmazsa (durağan görsel, kapak, yerleşim denetimi) balon açık durur.
(function () {
  const balon = document.getElementById('goril-balon');
  const kuyruk = document.getElementById('goril-balon-kuyruk');
  if (!balon) return;
  const GIRIS = 1.7, ACILIS = 0.35;   // sn: goril (gezinen 1,35 sn'de) sahneye girdikten sonra açılır
  const kenet = x => Math.min(Math.max(x, 0), 1);
  balon.style.transformOrigin = '82% 100%';

  function bas() {
    // gorilin bedeninin (class="goril-beden") en üst parçasının ortası; yoksa maskot kutusu
    const parcalar = Array.from(document.querySelectorAll('.maskot .goril-beden'));
    let r = null;
    for (const p of parcalar) {
      const b = p.getBoundingClientRect();
      if (b.width > 0 && (!r || b.top < r.top)) r = b;
    }
    if (!r) { const m = document.querySelector('.maskot'); r = m && m.getBoundingClientRect(); }
    return r ? r.left + r.width / 2 : null;
  }

  function ciz(t) {
    const u = kenet((t - GIRIS) / ACILIS);
    const e = 1 - Math.pow(1 - u, 3);
    const zipla = u > 0 && u < 1 ? Math.sin(u * Math.PI) * 0.06 : 0;
    balon.style.opacity = String(u);
    balon.style.transform = 'scale(' + (0.6 + 0.4 * e + zipla) + ')';
    if (!kuyruk || u === 0) return;
    const x = bas();
    if (x === null) return;
    const kutu = balon.getBoundingClientRect();
    const olcek = kutu.width / balon.offsetWidth || 1;
    const sol = Math.min(Math.max(x, kutu.left + 40 * olcek), kutu.right - 40 * olcek);
    kuyruk.style.right = 'auto';
    kuyruk.style.left = ((sol - kutu.left) / olcek - 14) + 'px';
  }

  const onceki = window.kare;
  window.kare = function (t) { if (typeof onceki === 'function') onceki(t); ciz(t); };
})();
