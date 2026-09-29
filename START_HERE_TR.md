# Başlangıç — v5

## İlk açılış

1. ZIP dosyasını tamamen çıkar. İçindeki `OPEN_DEMO.html` dosyasını Chrome veya Edge ile aç.
2. `Scenario Lab` sekmesine, sonra `Offer decisions` düğmesine bas.
3. Değerleri değiştirmeden `Compare offers and test conditions` düğmesine bas.
4. Başlangıçta önerilen yer CATH_FALL. Seçili üç koşulda en düşük ek rüzgâr kabulü 9,57 MW. Başlangıç koşulunda ek kabul 20,70 MW.
5. `Source demand 1% higher` koşulunu da zorunlu seçip yeniden çalıştır: doğrulanmış karşılaştırma olmadığı için öneri geri çekilir. Bu, gerçek şebekenin çalışamayacağı anlamına gelmez.

Ekrandaki açıklamaları ve sonuçları İngilizce tuttum. Bu dosya sadece senin kullanımın için Türkçe.

## Biz ne yaptık?

Aynı büyüklükte esnek tüketimin hangi bağlantıda rüzgâra daha fazla yer açacağını hesaplıyoruz. Sonra fiyat, bütçe ve zor koşulları kontrol ediyoruz. Öneri dayanmazsa başka seçenek seçiyoruz veya öneriyi geri çekiyoruz. İşletme taşımıyoruz; farklı yerlerdeki varsayımsal esnekliği karşılaştırıyoruz.

Gerçek veri: İrlanda'nın kamuya açık planlama şebekesi. Varsayım: müşteri teklifleri, ek varlıklar, fiyatlar ve olay süresi. Bulduğumuz MW farkı modeldeki güç farkıdır; İrlanda genelinde ölçülmüş tasarruf yüzdesi değildir.

## Sunum

Üstteki `Presentation`, güncel İngilizce PDF'yi açar. `Result walkthrough` ise seçtiğin hesap sonucunu üç adımda gösterir.

Sunumu başka araçla tasarlayabilirsin. `presentation/DESIGN_BRIEF_EN.md` ve `presentation/SPEAKER_NOTES_EN.md` hazır. Düzenlenebilir `Pitch_EN.pptx` de var. Kendi PDF'ni Overview altındaki `Use your own PDF` alanından seç; bu seçim sadece açık sekmede kalır. Kalıcı gömmek için proje içindeki `presentation/Pitch_EN.pdf` dosyasını kendi PDF'nle değiştir ve proje klasöründe `python scripts/build_offline.py` çalıştır.

## Microsoft erişimi gelince

1. `.env.example` dosyasının kopyasını `.env` adıyla oluştur.
2. Verilen Azure endpoint, API key ve deployment adını yaz. Anahtarı bana veya jüriye gösterme; HTML içine koyma.
3. Windows: `START_LOCAL.bat`. macOS/Linux: terminalde `bash START_LOCAL.sh`.
4. Tarayıcıda http://127.0.0.1:8765 adresini aç.
5. Teklif kararını hesaplat; `Run Microsoft AI audit` düğmesini kullan.
6. Ölçüm için proje klasöründe `python evaluation/decision_benchmark.py --run-live` çalıştır. Bu Azure kotası kullanır.

AI'nın görevi hangi kayıtlı zor koşula bakacağını seçmek. Sayıları hesaplayan ve öneriyi geçiren/engelleyen kurallar bağımsız. Canlı Azure henüz sınanmadı. Canlı sonuç yokken AI daha iyi diye sunma.

## Arkadaşına göndermek

Sadece `OPEN_DEMO.html` dosyasını gönderirsen çevrimdışı ekranı ve gömülü sunumu görebilir. E-posta önizlemesi yerine dosyayı indirip tarayıcıda açmalı. Yerel sunucu, kaynak kod ve yeniden üretim için ZIP'in tamamını gönder.

## Son prova

Kendi bilgisayarında HTML'yi aç; üç senaryoyu dene; PDF düğmesini kontrol et. Bu ortamda gerçek tarayıcı çizimi çalışmadığı için uygulamanın görsel tarayıcı kontrolü tamamlanmış sayılmıyor. Sayısal, HTTP, DOM ve çevrimdışı akış kontrollerinin sonuçları validation klasöründe. Slaytlar ayrıca görüntülenerek kontrol edildi.
