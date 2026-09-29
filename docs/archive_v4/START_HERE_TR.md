# Senin için kısa kullanım rehberi

ZIP'in **tamamını çıkar**, ardından **OPEN_DEMO.html** dosyasına çift tıkla. Microsoft hesabı ve kurulum gerekmiyor. Ürünün bütün ekranları İngilizce; bu rehber yalnızca senin için Türkçe.

## Ne yaptık?

Şu soruya cevap veren bir planlama aracı yaptık: **“Aynı miktardaki esnek tüketim hangi bağlantı noktasında daha fazla rüzgâr kullanılmasına yardımcı olur; bu fayda için ne kadar ek ücret ödemeye değer?”**

Hedef kullanıcı şebeke planlama mühendisi veya onunla çalışan esneklik agregatörü. Tüketicinin rüzgâr çiftliğine özel kabloyla bağlı olması gerektiğini varsaymıyoruz. Fakat hangi şebeke noktasına bağlı olduğu önemli. Sekiz gerçek şebeke bağlantı noktasında varsayımsal esnek tüketim denedik; buralarda gerçekten o kapasitede müşteri olduğunu doğrulamadık.

## Önce neye bakayım?

1. **Scenario Lab → Single comparison → Run comparison.** Varsayılan İrlanda örneğinde rüzgâr kabulü **47,66 → 61,72 MW**. Aynı 20 MW tüketimin yeri değişince yaklaşık **14,06 MW** daha fazla rüzgâr kabul ediliyor.
2. **Robustness & value.** Rüzgâr miktarını, esnek tüketimi ve hat durumunu değiştir. Burada yeni hesap yapılıyor gibi gösterilmiyor; gerçekten hesaplayıp kontrol ettiğimiz 60 koşulun kayıtlarını seçiyorsun.
3. Aşağıdaki **How do simple alternatives compare?** bölümünde sekiz noktayı ve basit kuralları karşılaştır. **Inspect best checked location** düğmesi en iyi bulunan noktayı açar: **47,66 → 68,36 MW**, yani **20,70 MW ek kabul**. Bu, önceki 14,06 MW örneğinden farklı bir bağlantıdır; oran veya yıllık tasarruf değildir.
4. **Evidence** sekmesinde kaynakları, varsayımları ve geçmeyen kontrolleri gör.

**Bu 14,06 MW bir yüzde veya yıllık tasarruf değildir.** Hazırlanan model senaryosundaki güç farkıdır. Kamuya açık gerçek İrlanda şebeke planlama dosyası kullanıldı; eklenen rüzgâr ve esnek tüketiciler varsayımsal. Sahada ölçülmüş azaltım demiyoruz.

## Para hesabını nasıl göstereyim?

**Robustness & value → What could this event be worth?** bölümünde kendi varsayımlarını gir. Üstteki **Comparison** menüsünden sekiz bağlantı noktasından birini de seçebilirsin; para hesabı seçtiğin noktanın gerçek hesap kaydını kullanır:

- **Assumed duration:** koşulların kaç saat sürdüğünü varsayıyorsun?
- **Extra wind value:** ek kabul edilen rüzgârın MWh başına değeri.
- **Extra activation premium:** alternatif tüketim için başlangıca göre MWh başına ek maliyet.
- **Other event costs:** diğer ek maliyetler.
- **Flexible-energy envelope:** tüketicinin olay boyunca sağlayabildiği toplam esnek enerji; biliyorsan gir.
- Karbon alanı isteğe bağlıdır; dayanağın yoksa boş bırak.

**Calculate conditional value** düğmesine bas. Ek maliyet faydayı geçiyorsa sonuç negatif çıkar; bunu gizlemiyoruz. Yeterli esnek enerji yoksa hesap engellenir. Buradaki EUR sonucu gerçek müşteri kârı değildir; yazdığın koşullara bağlı örnek hesaptır. **Export this case** düğmesi girilen varsayımları sonuçla birlikte indirir.

## Model sorunu ne oldu?

Kaynak dosyayı değiştirip her şey düzeldi demedik. Ayrı bir çalışma senaryosu oluşturduk: kaynak sınırları içinde 60 trafo ayarı değişti ve bir kondansatörün kapatıldığı varsayıldı. Hesaplar ayrı elektrik denklemleriyle kontrol edildi. Kaynağın eksik/temsili ekipman sınırları ve sahadaki izinler hâlâ gerçek işletmeci bilgisi gerektirir.

Bu nedenle ürünün iddiası **“bu açık varsayımlar altında kontrol edilmiş karar desteği”**. Gerçek cihaz kontrolü veya İrlanda genelinde ölçülmüş tasarruf iddiası değil. Test sayısı kurtarılan enerji veya gerçek tesis sayısı değildir.

## Microsoft gelmeden yerelde kullanmak

Çevrimdışı dosya bütün kayıtlı örnekleri gösterir. Yerel sunucu için Python 3.12 önerilir:

- **Windows:** START_LOCAL.bat dosyasını aç.
- **Mac/Linux:** proje klasöründe `bash START_LOCAL.sh` çalıştır.

Tarayıcıda `http://127.0.0.1:8765` adresine git. İrlanda kayıtları ve para hesabı için bilimsel paket kurmak gerekmiyor. Ayrı dokuz baralı referans şebekede yeni hesap yapmak istersen önce INSTALL_SIMULATOR dosyasını çalıştır. İlk kurulum internetten paket indirir.

## Microsoft AI erişimi gelince

Endpoint, API key ve deployment name bilgilerini `.env.example` dosyasının `.env` isimli kopyasına yaz. Anahtarı sohbete veya sunuma koyma. Sunucuyu yeniden başlat ve **AI Analyst** ekranını kullan.

AI, izin verilen bağlantı seçeneklerinin kayıtlarını inceleyip açıklayacak; sayıları kendi yazmayacak. Fiziksel faydayı şebeke hesabı üretti. AI'nın daha iyi sonuç bulduğunu söylemiyoruz. Canlı test:

```sh
python evaluation/conditional_agent.py --run-live --budget 4
```

Bu komut Azure kotası kullanır. Organizatörün vereceği hizmetin bağlantı ayrıntılarını o zaman kontrol edeceğiz.

## Bundan sonra

Demo kapsamındaki sonraki işler: **canlı Microsoft bağlantısını doğrulamak ve güncel İngilizce sunumu hazırlamak.** Mevcut sunum dosyaları eski sürüm; v4 sonucu için henüz güncellenmedi. Bilgisayarında açıp ekranların görünüşünü kontrol etmeyi sunum provasına dahil et; bu ortamda gerçek tarayıcı görüntü testi çalışmadı, ekran davranışları otomatik olarak sınandı.

Gerçek müşteriye kurulacak ürün için ayrıca tesis verisi ve işletmeci doğrulaması gerekir. Bunları hackathona girebilmenin zorunlu koşulu olarak sunmuyoruz.

ZIP açılmazsa tamamını kısa isimli bir klasöre çıkar; örneğin Masaüstünde ActionLab. Port meşgulse `python server.py --port 8766` çalıştır ve `http://127.0.0.1:8766` adresini aç.
