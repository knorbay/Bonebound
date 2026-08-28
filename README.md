# Bonebound

Bonebound, Pygame-ce ile geliştirilen sabit hızlı ve otomatik savaşlara sahip sıra tabanlı bir RPG prototipidir. Bu depo erken geliştirme sürümü `v0.1.0`ı içerir.

## Çalıştırma

Python 3.13 önerilir.

```bash
python -m pip install -r requirements.txt
python main.py
```

Arayüz fareyle kullanılır. `Esc` önceki ekrana döner; savaş sırasında geri çekilmeyi, ana menüde oyundan çıkmayı sağlar.

## İçerik

- 25 bölümlük kampanya, özel final ekranı ve kampanya sonrasında açılan sınırsız Endless Descent
- Sabit tempolu otomatik savaş, kritik/element/proc efektleri ve dalgalar arasında taşınan can
- 12 slot çanta; silah, kalkan ve yüzük/kolye/tılsım/taş kabul eden iki trinket yuvası
- Kalkanlarda ayrı guard havuzu olmadan doğrudan DEF, element dirençleri ve özel karşı-etkiler
- Kalkansız başlangıç; ilk bölüm ödülüyle açılan +5 DEF tabanlı kalkan ilerlemesi
- Savaş içi envanter ve tut-sürükle-bırak saha mixer'ı
- Her eşya çiftini kabul eden evrensel fusion sistemi; tarifli özel eşyalar, etkili aktarımlar ve görsel koleksiyon birleşimleri
- Beş iksir tipi, iksir-iksir fusion'ları, beş kademeli temper, element bağlama ve otomatik bölüm sonu ganimeti
- 81 ayrı item ikonu; lisanslı el-piksel tabanlar ile Bonebound'a özel relik/rün dönüşümleri ve ele/kabzaya kilitli silah-kalkan çizimi
- Tekil iksir slotları, azalan getirili mixer stat aktarımı ve özel fusion görselleri
- 1000+ HP final boss eğrisi, boss ikinci fazları ve dalgalar arası kısa toparlanma
- Sven Hero Knight'ın katmanlı kaynağından uyarlanan sekiz durumlu kemik maskeli Wayfarer; 57 yerel animasyon karesi, kareye özel ekipman tutuşları, düşman koşu setleri ve uzaktan yaklaşmalı sahne girişleri
- Daha düşük başlangıç saldırısı ve bölüm ilerledikçe daha sert yükselen düşman dayanıklılığı
- 25 düşmanın her animasyonunda ortak taban hizası, güvenli savaş kadrajı ve ayrıntıyı koruyan yenilgi efekti

## Derlemeler

GitHub Actions her `main` gönderiminde ve `v*` etiketi oluşturulduğunda Nuitka ile iki klasör tabanlı paket üretir:

- `Bonebound-v0.1.0-windows-x64.zip`
- `Bonebound-v0.1.0-linux-x64.tar.gz`

Klasör tabanlı `standalone` paket, tek dosyalı paketin başlangıçta kendini açma gecikmesini taşımaz. İndirilen arşivin tamamı çıkarılmalı; Windows'ta `Bonebound.exe`, Linux'ta `Bonebound` çalıştırılmalıdır.

## Kayıt konumları

- Windows: `%LOCALAPPDATA%\Bonebound\savegame.json`
- Linux: `$XDG_DATA_HOME/Bonebound/savegame.json` veya `~/.local/share/Bonebound/savegame.json`
- macOS: `~/Library/Application Support/Bonebound/savegame.json`

Kaynak koddan çalıştırıldığında kayıt dosyası proje klasöründe tutulur ve Git tarafından yok sayılır.

## Varlıklar

Kullanılan üçüncü taraf görsel ve ses varlıklarının kaynakları ile lisansları [ASSET_SOURCES.md](ASSET_SOURCES.md) ve `assets/licenses` altında listelenmiştir. Proje kodu için henüz ayrı bir dağıtım lisansı tanımlanmamıştır.

Özgün piksel varlıklarını yeniden üretmek için `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/build_pixel_assets.py` çalıştırılabilir.
