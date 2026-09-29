# Demo kontrolu ve calistirma

1. Eski sunucuyu kapat. Bu ZIP'i yeni bir klasore cikar.
2. Azure icin kullandigin `.env` dosyasini eski klasorden bu klasore kopyala.
3. Yeni klasorde `INSTALL_IRISH_EXTENSION.bat` dosyasini calistir. Bu, yeni fiziksel hesaplarin ihtiyac duydugu paketleri kurar.
4. `CHECK_DEMO.bat` dosyasini calistir. Azure yapilandirilmissa en fazla bir kaydi inceleyen canli audit dener; kota kullanabilir. Sonuc `DEMO_CHECK_RESULT.json` dosyasina yazilir.
5. `START_LOCAL.bat` ile baslat ve http://127.0.0.1:8765 adresini ac.

Git Bash kullaniyorsan: `bash START_LOCAL.sh`.

`OPEN_DEMO.html` kayitli/offline surumdur. Canli AI ve yeni fiziksel hesap icin yerel sunucu gerekir.

## Audit mesajlari

- `completed`: Audit kendi bitis kosuluna ulasti. Gercek incelenen kayit sayisi ayrica gosterilir; butun kosullarin gectigi anlamina gelmez.
- `Partial audit`: Bazi kayitlar incelendi, sonraki AI adimi tamamlanamadi. Mevcut sayisal kontroller korunur. Eksik kontroller basarili sayilmaz.
- HTTP 401: API anahtarini kontrol et.
- HTTP 403: Kaynak erisimini/izinlerini kontrol et.
- HTTP 404: Endpoint ve Azure deployment adini kontrol et.
- HTTP 429: Biraz bekleyip tekrar dene; surerse Azure kotasini kontrol et.
- HTTP 400: Deployment'in v1 Chat Completions ve function calling destegini kontrol et.

Kural ve AI audit'ini ayni maksimum kayit butcesiyle calistir. Iki sonuc karsilastirma tablosunda korunur; JSON ve okunabilir rapora eklenir.

Yeni alti saatlik deney tek senaryodan daha uzun surebilir. Kayitli ornegi acmak yeni hesap yapmaz; ekranda `SAVED EXAMPLE` yazar.

Kayitli sabit talep orneginde 12/12 aralik karsilastirilabilir. Kayitli degisken talep orneginde ise 0/12 aralik karsilastirilabilir: `Blocked` gorunmesi bu ornegin mevcut model sonucudur. Benzer sekilde `No flexible load delivered` kosulunun teklifi gecersiz kilmasi beklenir; bu iki durum Azure baglanti hatasi degildir.

Bu duzeltme ortaminda Azure anahtari bulunmadigi icin canli Azure erisimi test edilmedi. Kendi bilgisayarindaki canli kontrolun sonucu `CHECK_DEMO.bat` ile gorulur.
