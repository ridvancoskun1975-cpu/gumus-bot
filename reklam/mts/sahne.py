"""Gümüş külçe sahnesi — Mitsuba 3 ile gerçek ışık hesabı (13 Ekim profil resmiyle aynı yöntem).

Külçe: döküm biçimi, taban geniş, üst yüz dar; kenarlar yuvarlak (8 kürenin dışbükey zarfı).
Üst yüzde oyma "SILVER / 999.9 FINE" ve çerçeve (kabartma haritası; harfleri biz çizeriz, bozulmaz).
Kamera piramidin etrafında döner; ışık düzeni kamerayla kısmen döner, parlamalar külçelerin üstünden kayar.

Kullanım:  python sahne.py kare <t> <genişlik> <yükseklik> <spp> <çıktı.png> [dikey|yatay]
"""
import math
import sys
from pathlib import Path

import numpy as np

KLASOR = Path(__file__).resolve().parent
VARLIK = KLASOR / "varlik"
VARLIK.mkdir(exist_ok=True)

# Külçe ölçüleri (birim ~ 10 cm): taban 1,0 × 2,0, yükseklik 0,5; üst yüz %80 × %88
W, L, H = 1.0, 2.0, 0.5
UST_W, UST_L = 0.80, 0.88
R = 0.035                      # kenar yarıçapı
SURE = 5.0                     # sahne süresi (sn)


def kulce_ply():
    yol = VARLIK / "kulce.ply"
    if yol.exists():
        return yol
    import manifold3d as mf
    import trimesh
    from trimesh import graph
    kureler = []
    for (y, sx, sz) in [(R, W / 2 - R, L / 2 - R), (H - R, UST_W * W / 2 - R, UST_L * L / 2 - R)]:
        for ix in (-1, 1):
            for iz in (-1, 1):
                kureler.append(mf.Manifold.sphere(R, 48).translate([ix * sx, y, iz * sz]))
    zarf = mf.Manifold.batch_hull(kureler)
    m = zarf.to_mesh()
    v = np.asarray(m.vert_properties)[:, :3]
    f = np.asarray(m.tri_verts)
    t = trimesh.Trimesh(vertices=v, faces=f, process=True)
    t = graph.smooth_shade(t, angle=math.radians(25))
    yol.write_bytes(trimesh.exchange.ply.export_ply(t, encoding="binary", vertex_normal=True))
    return yol


def damga_dokulari():
    """Üst yüz plakası için yükseklik ve pürüz haritaları (u: uzun kenar, v: kısa kenar)."""
    h_yol, p_yol = VARLIK / "damga_yukseklik.png", VARLIK / "damga_puruz.png"
    if h_yol.exists() and p_yol.exists():
        return h_yol, p_yol
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    GEN, YUK = 2400, 1000
    img = Image.new("L", (GEN, YUK), 255)                   # 255 = yüzey, 0 = oyuk
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, GEN - 41, YUK - 41], outline=0, width=14)       # çerçeve oyuğu
    f1 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 380)
    f2 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 120)
    d.text((GEN / 2, YUK * 0.42), "SILVER", font=f1, fill=0, anchor="mm")
    d.text((GEN / 2, YUK * 0.80), "999.9      FINE", font=f2, fill=0, anchor="mm")
    from PIL import ImageOps
    img = ImageOps.mirror(img)                                # plaka eşlemesinde yazı düz okunsun
    yuks = img.filter(ImageFilter.GaussianBlur(3.0))          # oyuk kenarları eğimli
    yuks.save(h_yol)
    # pürüz: yüzey ayna (alfa ~0,05), oyuk içi mat (~0,32)
    a = np.asarray(yuks, dtype=np.float32) / 255.0
    puruz = (0.30 + (0.04 - 0.30) * a) * 255.0
    Image.fromarray(puruz.clip(0, 255).astype(np.uint8)).save(p_yol)
    return h_yol, p_yol


def studyo_ortami():
    """Kamera odaklı stüdyo ortamı (eşdikdörtgen, Mitsuba envmap düzeni: u = atan2(x, -z)/2π, v = acos(y)/π).
    Yerel çerçevede kamera +z tarafında, ileri yön -z. Kameranın gördüğü bölge (ileri ±70°, ufkun 8° üstüne
    kadar) tamamen siyah: arka plan siyah kalır. Işıklar kadraj dışında: tepede büyük yumuşak kutu, kameranın
    arkasında geniş panel, iki yanda uzun şerit, külçelerin arkasında yüksekte ince kenar şeridi."""
    yol = VARLIK / "studyo.exr"
    if yol.exists():
        return yol
    import mitsuba as mi
    GEN, YUK = 2048, 1024
    u = (np.arange(GEN) + 0.5) / GEN
    v = (np.arange(YUK) + 0.5) / YUK
    U, V = np.meshgrid(u, v)
    th, ph = V * np.pi, U * 2 * np.pi
    y = np.cos(th); x = np.sin(th) * np.sin(ph); z = -np.sin(th) * np.cos(ph)
    el = np.degrees(np.arcsin(np.clip(y, -1, 1)))               # yükseklik açısı
    az = np.degrees(np.arctan2(x, -z))                          # 0 = ileri (külçelere doğru), ±180 = kameranın arkası

    def kutu(a0, a1, e0, e1, yumus=4.0):
        def adim(t0, t1, t):
            return np.clip((t - t0) / yumus + 0.5, 0, 1) * np.clip((t1 - t) / yumus + 0.5, 0, 1)
        return adim(a0, a1, az) * adim(e0, e1, el)

    L = np.zeros((YUK, GEN, 3), np.float32)
    def ekle(m, parlak, renk=(1, 1, 1)):
        for k in range(3):
            L[..., k] += m * parlak * renk[k]
    # koyu dolgu: ufukta neredeyse siyah, yukarı doğru hafif açılır
    ekle(np.clip((el + 5) / 85, 0, 1) ** 1.3 * 0.10 + 0.01, 1.0)
    # tepe yumuşak kutu: ortası parlak, kenarlara doğru söner (üst yüzlerde geçiş)
    tepe = kutu(-50, 50, 18, 68, 14) * np.exp(-((el - 40) / 18) ** 2)
    ekle(tepe, 1.15)
    # kameranın arkasında iki dikey yumuşak kutu, arada koyu boşluk (yan yüzlerde açık-koyu geçişi)
    for merkez, parlak in ((120, 1.4), (-120, 0.9), (160, 0.5), (-160, 0.7)):
        ekle(kutu(merkez - 14, merkez + 14, -4, 50, 10), parlak)
    # yan şeritler (kenarlarda keskin parlama çizgileri)
    ekle(kutu(-95, -85, -2, 60, 2), 5.0)
    ekle(kutu(85, 95, -2, 60, 2), 3.5)
    # külçelerin arkasında yüksekte ince şerit (üst kenarlarda parlama)
    ekle(kutu(-60, 60, 11, 14, 1.5), 4.0)
    # kameranın gördüğü bölge tamamen siyah: ileri ±75°, ufkun 10° üstüne kadar
    gorus = kutu(-75, 75, -95, 10, 6)
    L *= (1 - gorus)[..., None]
    mi.Bitmap(L).write(str(yol))
    return yol


def zemin_maskesi():
    """Zeminin yansıtıcılığı: piramidin çevresinde 1, uzaklaştıkça 0 (yansıma siyaha karışır)."""
    yol = VARLIK / "zemin_maske.png"
    if yol.exists():
        return yol
    from PIL import Image
    N = 1024
    g = (np.arange(N) + 0.5) / N * 2 - 1                         # -1..1  →  dünya -ZEMIN..ZEMIN
    X, Z = np.meshgrid(g * ZEMIN, g * ZEMIN)
    r = np.sqrt((X / 1.25) ** 2 + (Z / 1.0) ** 2)
    m = np.clip((4.2 - r) / (4.2 - 2.2), 0, 1) ** 1.5
    Image.fromarray((m * 255).astype(np.uint8)).save(yol)
    return yol


ZEMIN = 8.0


GUMUS_YANSITMA = 0.93


def gumus(alfa=0.05):
    return {"type": "roughconductor", "material": "none", "distribution": "ggx", "alpha": alfa,
            "specular_reflectance": {"type": "rgb", "value": GUMUS_YANSITMA}}


def donusum_kulce(x, y, z, yaw):
    import mitsuba as mi
    return mi.ScalarTransform4f().translate([x, y, z]) @ mi.ScalarTransform4f().rotate([0, 1, 0], yaw)


YERLER = [  # x, katman, yaw (derece) — 3-2-1 piramit, uzun kenar derinlikte
    (-1.02, 0, 0.7), (0.0, 0, -0.4), (1.02, 0, 0.5),
    (-0.51, 1, -0.3), (0.51, 1, 0.45),
    (0.0, 2, 0.0),
]


def kamera(t, bicim):
    u = min(max(t / SURE, 0.0), 1.0)
    yum = u * u * (3 - 2 * u)
    aci = -1.20 + 0.85 * u                                # radyan: profil resmindeki açının çevresinde ~49°
    if bicim == "dikey":
        yar, yuk = 9.4 - 1.2 * yum, 3.3 + 1.0 * yum
        hedef = [0.0, 0.25, 0.0]
    else:
        yar, yuk = 10.2 - 0.6 * yum, 3.2 + 0.2 * yum
        # yatayda külçeler sağda, yazı solda: hedef, kameranın sağ yönüne göre sola kaydırılır
        sag = (math.cos(aci), 0.0, -math.sin(aci))
        hedef = [-1.55 * sag[0], 0.55, -1.55 * sag[2]]
    poz = [math.sin(aci) * yar, yuk, math.cos(aci) * yar]
    return poz, hedef, aci


def sahne(t, gen, yuk, spp, bicim="dikey"):
    import mitsuba as mi
    T = mi.ScalarTransform4f
    ply = kulce_ply()
    h_yol, p_yol = damga_dokulari()
    poz, hedef, aci = kamera(t, bicim)
    ortam = studyo_ortami()
    maske = zemin_maskesi()
    s = {
        "type": "scene",
        "integrator": {"type": "path", "max_depth": 8},
        "sensor": {
            "type": "perspective",
            "fov_axis": "smaller", "fov": 27.0 if bicim == "dikey" else 22.0,
            "to_world": T().look_at(origin=poz, target=hedef, up=[0, 1, 0]),
            "sampler": {"type": "independent", "sample_count": spp},
            "film": {"type": "hdrfilm", "width": gen, "height": yuk, "rfilter": {"type": "box"}},
        },
        "env": {"type": "envmap", "filename": str(ortam), "scale": 1.0,
                "to_world": T().rotate([0, 1, 0], math.degrees(aci))},
        # zemin: siyah cilalı; yansıtıcılık yalnız piramidin çevresinde (maske)
        "zemin": {"type": "rectangle", "to_world": T().rotate([1, 0, 0], -90) @ T().scale(ZEMIN),
                  "bsdf": {"type": "plastic", "diffuse_reflectance": {"type": "rgb", "value": 0.0015},
                           "specular_reflectance": {"type": "bitmap", "filename": str(maske), "raw": True},
                           "int_ior": 1.5}},
    }
    plaka_bsdf = {
        "type": "bumpmap",
        "arbitrary": {"type": "bitmap", "filename": str(h_yol), "raw": True},
        "scale": 0.6,
        "bsdf": {"type": "roughconductor", "material": "none", "distribution": "ggx",
                 "specular_reflectance": {"type": "rgb", "value": GUMUS_YANSITMA},
                 "alpha": {"type": "bitmap", "filename": str(p_yol), "raw": True}},
    }
    pw = UST_W * W - 2 * R - 0.05            # plaka genişliği (x)
    pl = UST_L * L - 2 * R - 0.06            # plaka uzunluğu (z)
    for i, (x, kat, yaw) in enumerate(YERLER):
        y = kat * (H + 0.002)
        M = donusum_kulce(x, y, 0.0, yaw)
        s[f"kulce{i}"] = {"type": "ply", "filename": str(ply), "to_world": M, "bsdf": gumus(0.04)}
        # damga plakası: üst yüzün 0,8 mm üstünde; dokunun u ekseni külçenin uzun kenarı (z)
        s[f"plaka{i}"] = {"type": "rectangle", "bsdf": plaka_bsdf,
                          "to_world": M @ T().translate([0, H + 0.0008, 0]) @ T().rotate([1, 0, 0], -90)
                          @ T().rotate([0, 0, 1], 90) @ T().scale([pl / 2, pw / 2, 1])}
    return s


def kare(t, gen, yuk, spp, cikti, bicim="dikey", pozlama=1.0):
    import mitsuba as mi
    import pyoidn
    mi.set_variant("llvm_ad_rgb")
    d = sahne(t, gen, yuk, spp, bicim)
    d["integrator"] = {"type": "aov", "aovs": "alb:albedo,nn:sh_normal",
                       "yol": {"type": "path", "max_depth": 8}}
    sc = mi.load_dict(d)
    img = np.array(mi.render(sc, spp=spp), dtype=np.float32)
    renk, alb, nn = img[..., 0:3], img[..., 3:6], img[..., 6:9]
    if img.shape[-1] > 9:                       # rgba film: renk, alfa, sonra aov'lar
        renk, alb, nn = img[..., 0:3], img[..., 4:7], img[..., 7:10]
    temiz = pyoidn.denoise(np.ascontiguousarray(renk), np.ascontiguousarray(np.clip(alb, 0, 1)),
                           np.ascontiguousarray(nn), hdr=True, quality="high")
    temiz = np.asarray(temiz) * pozlama
    # yumuşak tepe sıkıştırma (parlamalar yanmasın), sonra sRGB
    x = temiz / (1.0 + 0.08 * temiz)
    mi.util.write_bitmap(str(cikti), mi.Bitmap(np.ascontiguousarray(x.astype(np.float32))))


if __name__ == "__main__":
    if sys.argv[1] == "kare":
        import time
        t0 = time.time()
        kare(float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6],
             sys.argv[7] if len(sys.argv) > 7 else "dikey")
        print(f"bitti {time.time() - t0:.1f} sn → {sys.argv[6]}")
