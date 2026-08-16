# Bonebound

Bonebound, Pygame-ce ile geliştirilen sabit hızlı ve otomatik savaşlara sahip sıra tabanlı bir RPG prototipidir. Bu depo erken geliştirme sürümü `v0.1.0`ı içerir.

## Çalıştırma

Python 3.13 önerilir.

```bash
python -m pip install -r requirements.txt
python main.py
```

Arayüz fareyle kullanılır. `Esc` önceki ekrana döner; savaş sırasında geri çekilmeyi, ana menüde oyundan çıkmayı sağlar.

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
