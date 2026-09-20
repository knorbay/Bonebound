# Bonebound

Bonebound, Pygame-ce ile geliştirilen sabit hızlı ve otomatik savaşlara sahip sıra tabanlı bir RPG prototipidir. Bu depo geliştirme önizlemesi `v0.3.0` sürümünü içerir.

## Çalıştırma

Python 3.13 önerilir.

```bash
python -m pip install -r requirements.txt
python main.py
```

Arayüz fareyle kullanılır. `Esc` önceki ekrana döner; savaş sırasında geri çekilmeyi, ana menüde oyundan çıkmayı sağlar.

## İçerik

- 40 bölümlük, 8 bölgeli kampanya; özel final ekranı ve 25. bölümde açılan Endless Descent
- Sabit tempolu otomatik savaş, kritik/element/proc efektleri ve dalgalar arasında taşınan can
- 12 slot çanta; silah, kalkan ve yüzük/kolye/tılsım/taş kabul eden iki trinket yuvası
- Kalkanlarda ayrı guard havuzu olmadan doğrudan DEF, element dirençleri ve özel karşı-etkiler
- Kalkansız başlangıç; ilk bölüm ödülüyle açılan +5 DEF tabanlı kalkan ilerlemesi
- Savaş içi envanter ve tut-sürükle-bırak saha mixer'ı
- Her eşya çiftini kabul eden evrensel fusion sistemi; tarifli özel eşyalar, etkili aktarımlar ve görsel koleksiyon birleşimleri
- Beş iksir tipi, iksir-iksir fusion'ları, beş kademeli temper, element bağlama ve otomatik bölüm sonu ganimeti
- 103 eşya ikonu; 100 sanatçı çizimi CC0 ikon, 3 özgün relik ve ele/kabzaya kilitli silah-kalkan çizimi
- Tekil iksir slotları, azalan getirili mixer stat aktarımı ve özel fusion görselleri
- 1000+ HP final boss eğrisi, boss ikinci fazları ve dalgalar arası kısa toparlanma
- Sven Hero Knight'ın katmanlı kaynağından uyarlanan sekiz durumlu kemik maskeli Wayfarer; 57 yerel animasyon karesi, kareye özel ekipman tutuşları, düşman koşu setleri ve uzaktan yaklaşmalı sahne girişleri
- Daha düşük başlangıç saldırısı ve bölüm ilerledikçe daha sert yükselen düşman dayanıklılığı
- 40 düşmanın her animasyonunda ortak taban hizası, güvenli savaş kadrajı ve ayrıntıyı koruyan yenilgi efekti

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

## 0.2.0 önizlemesi — 14 Eylül 2026

- Beş bölgeye ayrı mimari katmanlar: mezar nişleri, fırın bacaları ve lav, buz kristalleri, zehirli sarmaşıklar, yıldızsız saray halkaları. Hareketli atmosfer parçacıkları.
- 10 yeni bölgesel eşya, özgün piksel ikonları, 10 deterministik fusion tarifi ve bölgelere bağlı ganimet havuzları.
- Eşyada fareyi kısa süre bekletince tam açıklama, sayısal özel etkiler, tarif ve düşme bölgeleri. Uzun açıklamalarda fare tekerleğiyle kaydırma.
- Beş element için ayrı saldırı efektleri ve sentezlenmiş sesler; blok kalkanı, boss fazı ve zafer sesleri.
- Proc, yansıma ve karşı saldırı hasarlarının doğru hedefte gösterilmesi; boss/infaz sayısal bonuslarının tek başına da çalışması.
- Eski 25 bölümlük kampanya kayıtları korunarak 40 bölüme taşınır. Sürüm henüz GitHub veya itch.io'ya yayımlanmadı.

Özgün yeni varlıkları üretmek: `python tools/build_presentation_assets.py`.
Doğrulama: `python tools/qa_release.py` ve `python tools/qa_presentation.py`.

## 0.2.1 — piksel asset yenilemesi

- 0x72'nin CC0 zindan setiyle oda ve koridorlardan oluşan kaydırılabilir harita; beş bölge sekmesi.
- Savaş arka planları aynı setle kurulur. Önceki geometrik dekorlar ve düşman çevresindeki büyük halkalar kaldırıldı.
- Yeni 10 eşya, Idylwild ve 7Soul'un CC0 çizimleriyle yenilendi. İkonlar görünür sınıra göre boyutlanır; renkleri tek renge boyayan filtre kaldırıldı.
- Haritada iksir ve giriş düğmesi çakışması, savaş panelinde yazı/düğme çakışması düzeltildi.
- Kenney RPG Audio: kılıç, darbe, ekipman, kapı, kitap ve ganimet sesleri. Müzik kısıldı, efektler yükseltildi.
- `M`: müzik aç/kapat; `N`: efektleri aç/kapat. Ayarlar bu oturum için geçerlidir.
- Test: `python tools/qa_map.py`, `python tools/qa_presentation.py`, `python tools/qa_release.py`.

## 0.2.2 — savaş görsel hata düzeltmeleri

- Kılıç izi, ölüm parlaması ve solan bildirimlerde çıkan renkli dikdörtgenler giderildi.
- Aynı vuruşun hasar/ek hasar satırları ayrıldı; hedef konumu sprite sınırlarından hesaplanıyor.
- Buz etkisi düşmanın, bariyer ve iyileşme oyuncunun üzerinde gösteriliyor.
- İksir, iyileşme ve durum etkileri ekran sarsıntısı oluşturmuyor; stat iksirleri `+0` yazmıyor.
- Kritik hasardan sonra saldırı animasyonu ikinci kez başlatılmıyor.
- Boss ikinci evre bildiriminin süresi ve dalga geçişinde eski efektlerin temizlenmesi düzeltildi.
- Can çalma iyileşmesi görünür hale getirildi; ilk düşmanın ölçeği küçültüldü.

Doğrulama: macOS canlı arayüzde normal savaş, iksir kullanımı ve kontrollü çoklu hasar;
`tools/qa_combat_feedback.py`, `tools/qa_release.py`, `tools/qa_presentation.py`, `tools/qa_map.py`.

## 0.2.3 — müzik ve item görselleri

88 item için açıkça seçilmiş CC0 piksel çizimleri: doğal renkler, doğru ahşap/kemik/metal
malzemeler, ayrı iksir biçimleri. 32px kaynaklar ara ölçekleme olmadan kullanılıyor.

Dört yeni müzik; toplam altı parça. Menü/atölye, bölge keşfi, normal ve boss savaşları
ayrı müziklere yönleniyor. Parçalar arasındaki ses farkı dengelendi ve yumuşak geçiş
eklendi. Sağ alttaki AUDIO düğmesinden müzik ve efekt seviyeleri ayrı ayarlanıp
kalıcı kaydedilebilir. M/N kısayolları korunur; ses paneli açıkken savaş durur.

## 0.2.4 — sabit ölüm efekti ve savaş kontrolleri

Canavar öldüğünde son çizilen poz ve konum sabitlenir. Yana yatma, dönme,
çökme ve kaynak sprite ölüm animasyonu kaldırıldı; beyaz parlama ve saydam
kaybolma korunur. Dalga değişiminde yeni canavar kendi pozunu kullanır.

P / Escape veya PAUSE düğmesi savaşı durdurur. Duraklatma panelinde son beş
savaş olayı görülebilir; RESUME devam ettirir, RETREAT TO MAP geri çekilir.
Escape artık yanlışlıkla doğrudan zindandan çıkarmaz.

Bariyer, iksir stat bonusu/kalan turu, hazır dirilme ve düşmanın buz etkisi savaş
alanında görünür. İksir süresi dolduğunda BOOST ENDED bildirimi gösterilir.


## 0.3.0 — Beyond the Hollow Crown

- 40 bölüm, 8 bölge, 40 yaratık; Drowned Archive, Iron Cathedral ve Dawn Gate.
- 15 yeni yaratık için 0x72 CC0 animasyonları, 12 yeni eşya için 7Soul CC0 ikonları.
- 103 eşya, 8 yeni birleşim tarifi; yeni bölgelere uygun ödüller ve açıklamalar.
- Sekiz sekmeli kaydırılabilir atlas, yeni bölge oda düzenleri ve renkleri.
- Gerçek HP sayısını geciktirmeden yumuşayan can çubukları; üst üste element seslerini sınırlayan ses kanalı.
- Altı müzik parçası, bölge/boss geçişleri ve kalıcı müzik/efekt ayarları.
- Ölümde yaratık sabit durur; beyazlaşır ve silinir. P/Escape savaşı duraklatır.
- Kayıt biçimi v5: eski finali bitirenler 26. bölüme devam eder, Endless erişimi korunur.

Doğrulama: `tools/qa_expansion.py` eski kayıt dönüşümü, yeni animasyon dosyaları,
40. bölüm kayıt turu, can çubuğu geçişi ve altı bölümde 480 savaş simülasyonunu denetler.

- 0.3 son görsel kontrolü: yeni rakipler sola, kahramana bakar; arena kenarlarındaki kapı gibi okunan sandıklar kaldırıldı. Zindan pikselleri eşit oranda ölçeklenir.
