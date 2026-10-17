#!/usr/bin/env bash
# Bilgi sayfasını üretir ve site klasörüne koyar; iş akışları (paylas.yml, sayfa.yml) çağırır.
#   bash bot/sayfa_uret.sh <site klasörü>
#
# Rıdvan, 18 Ekim 2026 ("2 kere belirli aralıklarda tekrar denesin. başarısız olursa önceki hali kalsın bana
# haber gelsin"): sayfa ayrı bir klasöre, hata kontrolüyle (--kati) üretilir. Hata verirse 30 sn ve 90 sn sonra
# iki kez yeniden denenir. Başarılıysa site klasörüne kopyalanır ve "son başarılı sayfa" olarak veri/sayfa_son'a
# da konur (iş akışı bunu önbelleğe yazar). Üç deneme de başarısızsa çıkış kodu 1: iş akışı sitenin önceki
# hâlini yayınlar ve günlüğe "BİLGİ SAYFASI YEDEK YOL" yazar; gece kontrolü bunu görüp Rıdvan'a bildirir.
# Sayfa sonucu GITHUB_OUTPUT'a yazılır: sonuc=yeni | hata.
set -u
SITE="${1:?site klasörü}"
GECICI="$(mktemp -d)"
SONUC_DOSYA="${GITHUB_OUTPUT:-/dev/null}"
BEKLEMELER=(30 90)

for deneme in 1 2 3; do
  rm -rf "$GECICI/sayfa"
  if python bot/sayfa.py --cikti "$GECICI/sayfa" --kati \
      && test -s "$GECICI/sayfa/index.html" && test -s "$GECICI/sayfa/rehber/index.html" \
      && test -s "$GECICI/sayfa/sitemap.xml" && grep -q "Gram gümüş fiyatı" "$GECICI/sayfa/index.html"; then
    mkdir -p "$SITE"
    cp -r "$GECICI/sayfa/." "$SITE/"
    rm -rf veri/sayfa_son && mkdir -p veri && cp -r "$GECICI/sayfa" veri/sayfa_son
    [ "$deneme" -gt 1 ] && echo "::notice::Bilgi sayfası ${deneme}. denemede üretildi."
    echo "sonuc=yeni" >> "$SONUC_DOSYA"
    exit 0
  fi
  if [ "$deneme" -lt 3 ]; then
    bekle="${BEKLEMELER[$((deneme - 1))]}"
    echo "::warning::Bilgi sayfası üretilemedi (deneme ${deneme}/3); ${bekle} sn sonra yeniden denenecek."
    sleep "$bekle"
  fi
done
echo "::warning::Bilgi sayfası 3 denemede de üretilemedi; sitenin önceki hâli kullanılacak."
echo "sonuc=hata" >> "$SONUC_DOSYA"
exit 1
