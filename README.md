# UCL Simülasyon Otomatik Paylaşım

Her Şampiyonlar Ligi maç günü sabah 09:30'da (İstanbul) o günün maçları için simülasyon videosu üretir ve YouTube Shorts, Instagram Reels, TikTok ve X'e İngilizce açıklamayla paylaşır.

- Video: 1080×1920, 30 fps, MP4 (H.264 + AAC), ses seviyesi sosyal medya standardına göre ayarlı (-14 LUFS).
- Seçim: Günde en fazla `max_videos_per_day` maç. Önce `priority_teams` içindeki takımların maçları, sonra en güçlü eşleşmeler.
- Açıklamalarda maç sonucu yazmaz; videonun merakı korunur. Her açıklamada "simülasyon, gerçek sonuç değil" notu var.
- Bir platform hata verirse diğerleri yine paylaşılır. Hatalar Actions sayfasında görünür.

## Klasörler

| Yol | İçerik |
|---|---|
| `sim/index.html` | Simülasyon sayfası (tarayıcıda da açılır) |
| `render.js` | Bir maçı tarayıcısız, kare kare MP4'e çevirir |
| `autopost/` | Günlük akış, açıklamalar, platform yükleyicileri |
| `data/fixtures.json` | 4.–8. hafta fikstürü (tarih ve saatlerle) |
| `config.json` | Kanal adı, günlük video sayısı, öncelikli takımlar, açık platformlar |
| `tools/` | Hesapları bir kez bağlamak için yardımcı betikler |
| `docs/callback.html` | Instagram ve TikTok girişinden dönen kodu gösteren sayfa |
| `.github/workflows/daily.yml` | Günlük zamanlayıcı |

## Kurulum

### 1. GitHub deposu

1. GitHub'da **herkese açık (public)** yeni bir depo oluştur, örneğin `ucl-autopost`. Instagram videoyu herkese açık bir adresten indirdiği için depo public olmalı. Şifreler ve anahtarlar "Secrets" bölümünde gizli kalır.
2. Bu klasördeki her şeyi depoya yükle.
3. **Settings → Pages**: Branch `main`, klasör `/docs` seç. Birkaç dakika sonra `https://KULLANICI.github.io/ucl-autopost/callback.html` açılır. Instagram ve TikTok uygulamalarında yönlendirme adresi (redirect URI) olarak bunu kullanacaksın.
4. **Settings → Secrets and variables → Actions** bölümüne aşağıdaki anahtarları tek tek ekleyeceksin.
5. Instagram ve TikTok anahtarları zamanla yenilenir; yenisinin otomatik kaydedilmesi için bir anahtar daha gerekiyor:
   GitHub → Settings → Developer settings → Fine-grained tokens → yalnızca bu depo, **Secrets: Read and write** izni.
   Çıkan değeri `GH_PAT` adıyla secret olarak ekle.

Yardımcı betikleri kendi bilgisayarında çalıştırmak için Python 3 ve `pip install requests` yeterli.

### 2. YouTube

1. [Google Cloud Console](https://console.cloud.google.com/) → yeni proje → **YouTube Data API v3**'ü etkinleştir.
2. **OAuth consent screen**: External. Kendi e-postanı test kullanıcısı olarak ekle, sonra **Publish app** ile "In production" durumuna al. "Testing" durumunda kalırsa bağlantı 7 günde bir kopar. Uygulamanın doğrulanmamış olması kişisel kullanımda sorun değil; girişte uyarı çıkar, "Devam" dersin.
3. **Credentials → Create credentials → OAuth client ID → Desktop app**. Client ID ve Client Secret'ı al.
4. `python tools/youtube_auth.py CLIENT_ID CLIENT_SECRET` komutunu çalıştır. Tarayıcıda kanalınla giriş yap.
5. Çıkan `YT_CLIENT_ID`, `YT_CLIENT_SECRET` ve `YT_REFRESH_TOKEN` değerlerini secret olarak ekle.

Google, denetimden geçmemiş API projelerinden yüklenen videoları gizli (private) tutabiliyor. İlk paylaşımdan sonra rapordaki YouTube satırına bak:
- "(uploaded as private …)" yazıyorsa Google'ın [API denetim formunu](https://support.google.com/youtube/contact/yt_api_form) doldurman gerekiyor.
- Bu süreçte videoları YouTube Studio'dan elle herkese açık yapabilirsin.

### 3. Instagram

1. Instagram hesabını **Profesyonel** hesaba çevir (İçerik üreticisi ya da İşletme).
2. [Meta for Developers](https://developers.facebook.com/) → Create app → **Instagram** ürünü → "API setup with Instagram login".
3. Bu üç bilgiyi al:
   - Instagram App ID
   - Instagram App Secret
   - Redirect URI: GitHub Pages adresin, yani `https://KULLANICI.github.io/ucl-autopost/callback.html`
4. Uygulamanın rollerinde kendi Instagram hesabını tester olarak ekle ve davet bildirimini Instagram'da kabul et. Kendi hesabına paylaşım için uygulama incelemesi gerekmez.
5. `python tools/instagram_auth.py APP_ID APP_SECRET REDIRECT_URI` komutunu çalıştır. Verilen adresi aç, izin ver, sayfadaki kodu yapıştır.
6. Çıkan `IG_ACCESS_TOKEN` değerini secret olarak ekle. Bu anahtar 60 gün geçerli; her paylaşımda otomatik yenilenir.

### 4. TikTok

1. [TikTok for Developers](https://developers.tiktok.com/) → Manage apps → Create app.
2. Ürün olarak **Login Kit** ve **Content Posting API**'yi ekle. Direct Post'u aç.
3. Kapsamlar `user.info.basic` ve `video.publish`. Redirect URI olarak yine GitHub Pages adresini gir.
4. `python tools/tiktok_auth.py CLIENT_KEY CLIENT_SECRET REDIRECT_URI` komutunu çalıştır.
5. Çıkan `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` ve `TIKTOK_REFRESH_TOKEN` değerlerini secret olarak ekle.

Önemli: TikTok, denetimden (audit) geçmemiş uygulamaların paylaşımlarını **yalnızca sana görünür** (private) yapar. Herkese açık paylaşım için uygulama sayfasından denetim başvurusu yapman gerekir. Onaylanınca kod kendiliğinden herkese açık paylaşmaya başlar.

### 5. X (Twitter)

1. [X Developer Console](https://console.x.com/) → proje ve uygulama oluştur.
2. User authentication settings: **Read and write**.
3. **Keys and tokens** bölümünden dört değeri al: API Key, API Key Secret, Access Token, Access Token Secret. Yazma izni verdikten sonra Access Token'ı yeniden üret.
4. Secret olarak ekle: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`.
5. X API artık kullandıkça öde modeliyle çalışıyor ve yeni geliştiricilere ücretsiz kullanım yok. Konsoldan bir miktar kredi yükle. 2026 başındaki fiyatlarla bir paylaşım yaklaşık 0,015 dolar, ama fiyatlar değişebilir.

### 6. Deneme

1. GitHub → **Actions → Daily UCL simulations → Run workflow**.
2. İlk çalıştırmada "Render only" kutusu işaretli kalsın. Bu durumda video üretilir ama paylaşılmaz.
3. Bitince sayfanın altındaki **Artifacts** bölümünden videoları ve açıklamaları indirip kontrol et.
4. Sonra kutunun işaretini kaldır, `limit` alanına 1 yaz ve gerçek paylaşımı dene.
5. Her şey yolundaysa başka bir şey yapmana gerek yok: zamanlayıcı her gün 09:30'da kendisi çalışır, maç olmayan günlerde hiçbir şey yapmaz.

Bir platformu kapatmak için `config.json` içinde `"platforms"` altındaki değeri `false` yap.

## Ayarlar (`config.json`)

| Ayar | Anlamı |
|---|---|
| `handle` | Videonun altındaki kanal adı |
| `max_videos_per_day` | Günde en fazla kaç maç (4.–8. haftalarda her gün 9 maç var) |
| `priority_teams` | Her zaman paylaşılacak takımlar |
| `duration_seconds` | Maç süresi (gol kutlamalarıyla video ~10–15 sn daha uzun olur) |
| `music` | `hype` (heyecanlı), `epic` (marş havası) veya `none` |
| `post_gap_minutes` | İki maçın paylaşımı arasındaki bekleme |

## Sınırlar

- **Güç puanları:** Sayfaya gömülü güç puanları ilk 3 haftanın sonuçlarıyla hesaplı. Yeni haftaların sonuçlarıyla güncellemek için `sim/index.html` yenilenmeli.
- **Platform kuralları:** Her platform otomatik ve tekrar eden içeriğe karşı kendi kurallarını uygular. Açıklamalar her maçta farklı, ama çok sayıda benzer video erişimi düşürebilir.
- **Kulüp adları:** Topların üstünde logo değil kısa ad ve renkler var. Gerçek logo eklemek marka şikâyeti riski taşır.
- **Paylaşım saati:** Paylaşımlar GitHub'ın zamanlayıcısına bağlı. GitHub yoğun saatlerde birkaç dakika ile bir saat arası gecikebilir.
