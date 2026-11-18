# 🎓 SAÜ SABİS Not Takip Botu

Sakarya Üniversitesi SABİS sistemindeki ders ve değerlendirme notlarını belirli aralıklarla kontrol eden, yeni bir not girildiğinde veya mevcut bir not değiştiğinde Telegram üzerinden bildirim gönderen Python tabanlı bir otomasyon.

Bot, GitHub Actions üzerinde çalışır. Bilgisayarınızın açık veya botun çalışması için sürekli internete bağlı olması gerekmez. Her kullanıcı kendi SABİS bilgilerini GitHub Secrets alanında, not geçmişini ise kendisine ait ayrı bir **private GitHub deposunda** saklar.

> Bu proje Sakarya Üniversitesi'nin resmî uygulaması değildir ve üniversite tarafından geliştirilmemiştir. Kişisel kullanım ve yazılım geliştirme/öğrenme amacıyla hazırlanmıştır.

## ✨ Özellikler

- **Otomatik SABİS girişi:** Öğrenci numarası ve şifreyle SABİS'e giriş yapar.
- **Ders bazlı not okuma:** SABİS'in `/Ders` sayfasındaki ders kartlarını ve değerlendirme tablolarını okur.
- **Not değişikliği tespiti:** Her dersin değerlendirme türü ve not değerlerini önceki kayıtla karşılaştırır.
- **Telegram bildirimi:** Yeni ders kaydı veya not değişikliği olduğunda ilgili dersin adı, kodu ve değişen değerlendirmeler için bildirim gönderir.
- **Boş not takibi:** Henüz not girilmemiş değerlendirmeleri de kaydeder. Böylece boş bir not alanına sonradan not girilmesi tespit edilebilir.
- **Tekrarlanan değerlendirmeleri ayırt etme:** Aynı tür ve ağırlıktaki birden fazla değerlendirmeyi sıra numarasıyla birbirinden ayırır.
- **Özel not geçmişi:** Notların anlık görüntüsü kullanıcının private deposunda JSON biçiminde saklanır; herkese açık kod deposuna gönderilmez.
- **Zamanlanmış ve manuel çalıştırma:** Varsayılan olarak 15 dakikada bir çalışır; GitHub Actions üzerinden elle de başlatılabilir.

## ⚙️ Nasıl çalışır?

Proje, herkese açık kod deposu ile kullanıcıya özel not deposunu birbirinden ayırır:

```text
PUBLIC REPOSITORY
aktenberkan/obs-takip
        |
        | GitHub Actions (15 dakikada bir)
        v
SABİS'e giriş yap
        |
        v
Ders kartlarını ve notları oku
        |
        v
Önceki kayıtla karşılaştır
        |
        +---- Değişiklik yok ----> Yeni snapshot oluştur, bildirim gönderme
        |
        +---- Değişiklik var ----> Telegram bildirimi gönder
        |                              |
        v                              v
Kullanıcının PRIVATE REPOSITORY <-----+
obs-takip-private-data
        |
        +-- son_durum.txt (JSON biçimindeki kişisel not snapshot'ı)
```

1. GitHub Actions, herkese açık kod deposundaki workflow'u başlatır.
2. Workflow, kullanıcının PAT (Personal Access Token) bilgisiyle private not deposunu çalışma ortamına alır.
3. Önceki `son_durum.txt` kaydı varsa botun erişebileceği çalışma klasörüne kopyalar.
4. Python/Selenium botu SABİS'e giriş yapar ve derslerin değerlendirme tablolarını okur.
5. Yeni verileri önceki snapshot ile karşılaştırır.
6. Değişiklik varsa Telegram bildirimi gönderir. Telegram gönderimi başarılı olduktan sonra yeni snapshot oluşturulur.
7. Workflow, snapshot'ı private depoya commit edip push eder. Public kod deposuna kişisel not verisi gönderilmez.

## 🧰 Kullanılan teknolojiler

- **Python** – veri okuma, karşılaştırma ve otomasyon mantığı
- **Selenium** – SABİS web arayüzüyle etkileşim
- **Requests** – Telegram Bot API üzerinden bildirim gönderme
- **GitHub Actions** – bulut üzerinde zamanlanmış çalıştırma
- **GitHub Secrets** – kullanıcı bilgileri ve token'ları güvenli değişken olarak saklama
- **Private GitHub repository** – kişisel not geçmişini saklama

## 🚀 Kurulum

Projeyi kendi hesabınızda kullanmak için aşağıdaki adımları izleyin.

### 1. Public projeyi fork edin

Bu depoyu kendi GitHub hesabınıza **Fork** edin. Aşağıdaki kurulumun geri kalanı fork ettiğiniz depo üzerinde yapılacaktır.

Fork sonrasında GitHub Actions'ı etkinleştirdiğinizden emin olun. Gerekirse deponuzdaki **Actions** sekmesinden workflow'ların çalışmasına izin verin.

### 2. Kendinize ait private state deposu oluşturun

GitHub hesabınızda yeni bir repository oluşturun. Örneğin:

- **Repository name:** `obs-takip-private-data`
- **Visibility:** `Private`
- Depoyu başlangıçta bir `README.md` dosyası ekleyerek oluşturabilirsiniz.

Bu depo yalnızca sizin not geçmişinizi saklamak içindir. Başka kullanıcılarla ortak kullanmayın. Her kullanıcının kendi private state deposu olmalıdır.

### 3. Fine-grained Personal Access Token oluşturun

GitHub'da **Settings → Developer settings → Personal access tokens → Fine-grained tokens** sayfasına gidip yeni bir token oluşturun.

Önerilen en düşük izinler:

| Ayar | Değer |
|---|---|
| Token name | Örneğin `obs-takip-state-access` |
| Resource owner | Kendi GitHub hesabınız |
| Repository access | `Only select repositories` |
| Selected repository | Yalnızca `obs-takip-private-data` |
| Repository permissions → Contents | `Read and write` |
| Repository permissions → Metadata | `Read-only` |

Token oluşturulduğunda GitHub'ın gösterdiği **gerçek token değerini** güvenli bir yere kopyalayın. Token'ın adı, token'ın kendisi değildir. GitHub gerçek değeri daha sonra tekrar göstermez; kaybederseniz yeni token oluşturmanız gerekir.

Token'ı kimseyle paylaşmayın ve kod dosyalarına yazmayın.

### 4. Telegram botu oluşturun

1. Telegram'da [@BotFather](https://t.me/BotFather) hesabını açın.
2. `/newbot` komutuyla yeni bot oluşturun.
3. BotFather'ın verdiği bot token'ını kaydedin.
4. Oluşturduğunuz botu Telegram'da açıp **Start** düğmesine basın.
5. Telegram kullanıcı/sohbet kimliğinizi (`chat_id`) öğrenin. Bunun için [@userinfobot](https://t.me/userinfobot) gibi bir bot kullanabilirsiniz.

`TG_TOKEN` bot token'ıdır; `TG_CHAT_ID` ise bildirimin gönderileceği sohbetin kimliğidir. Bunları public depoya veya kaynak koda yazmayın.

### 5. GitHub Actions Secrets değerlerini ekleyin

Fork ettiğiniz **public kod deposunda** şu yolu açın:

**Settings → Secrets and variables → Actions → New repository secret**

Aşağıdaki altı secret'ı oluşturun:

| Secret adı | Değer |
|---|---|
| `OKUL_NO` | SABİS öğrenci numaranız |
| `OKUL_SIFRE` | SABİS şifreniz |
| `TG_TOKEN` | BotFather'ın verdiği gerçek Telegram bot token'ı |
| `TG_CHAT_ID` | Telegram sohbet/kullanıcı kimliğiniz |
| `STATE_REPO` | Private deponun `owner/repository` biçimindeki adresi. Örn. `aktenberkan/obs-takip-private-data` |
| `STATE_REPO_TOKEN` | 3. adımda oluşturduğunuz Fine-grained PAT'in **gerçek token değeri** |

**Önemli:** `STATE_REPO_TOKEN` alanına token'ın ismini değil, GitHub'ın oluştururken gösterdiği uzun token değerini yapıştırın. Token'ı README, Python dosyası, workflow veya herhangi bir public commit içine koymayın.

### 6. Workflow'u çalıştırın

Fork ettiğiniz depoda:

1. **Actions** sekmesine girin.
2. `OBS Not Kontrol Botu` workflow'unu seçin.
3. **Run workflow** düğmesine basarak ilk çalıştırmayı manuel başlatın.
4. Çalıştırma ayrıntılarında adımların başarılı tamamlandığını kontrol edin.

İlk başarılı çalıştırmada bot mevcut ders/not durumunu başlangıç kaydı olarak saklar. Bu ilk kayıt sırasında mevcut notlar için toplu Telegram bildirimi gönderilmez. Sonraki çalıştırmalarda yeni veya değişen notlar tespit edilirse bildirim gönderilir.

## ⏱️ Otomatik çalışma sıklığı

Workflow dosyasındaki zamanlama:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'
  workflow_dispatch:
```

`*/15 * * * *` ifadesi workflow'un her saat `00`, `15`, `30` ve `45` dakikalarında tetiklenmesini ister. Ayrıca `workflow_dispatch` sayesinde Actions ekranından manuel çalıştırma yapılabilir.

GitHub zamanlanmış çalıştırmaları yoğunluk nedeniyle geciktirebilir; bu nedenle tam 15 dakikada bir çalışma garantisi yoktur. `schedule` tetikleyicisi varsayılan dal üzerinden çalışır. Public depolarda 60 gün boyunca depo etkinliği olmazsa zamanlanmış workflow otomatik devre dışı bırakılabilir. Ayrıntılar için [GitHub Actions schedule dokümantasyonuna](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) bakın.

Çalıştırma geçmişi: **Repository → Actions → OBS Not Kontrol Botu**.

## 📲 Telegram bildirimi nasıl görünür?

Bir dersin değerlendirme notu değiştiğinde bildirim, değişen ders ve değerlendirme bilgilerini içerir. Örnek:

```text
🎓 OBS NOT TAKİP BİLDİRİMİ

🚨 SABİS NOT GÜNCELLEMESİ
📚 Ders: Örnek Ders
🔖 Kod: ABC123
📝 Değişen notlar:
• Vize: — → 85
```

Buradaki ders ve not değerleri yalnızca örnektir.

## 🗂️ Not geçmişi ve ilk çalıştırma

Botun kullandığı `son_durum.txt` dosyasının uzantısı `.txt` olsa da içeriği JSON biçimindedir. Snapshot, `obs-grade-snapshot-v2` format kimliğiyle birlikte ders kodlarını, ders adlarını ve değerlendirme/not değerlerini saklar.

- Boş not alanları da kaydedilir; boş değerden nota geçiş değişiklik olarak algılanır.
- Aynı değerlendirme türü ve ağırlığı bir derste birden fazla kez bulunuyorsa satırlar sıra numarasıyla ayrıştırılır.
- İlk çalıştırmada veya eski MD5/uyumsuz formatta bir kayıt bulunduğunda yeni başlangıç snapshot'ı oluşturulur ve eski notlar için toplu bildirim gönderilmez.
- Botun bir çalıştırmada ders kartlarını hiç okuyamaması hata olarak değerlendirilir; boş bir snapshot ile önceki kayıtların üzerine yazılmaz.
- Telegram bildirimi başarısız olursa yeni snapshot kaydedilmez. Böylece sonraki çalıştırmada değişiklik yeniden denenebilir.

## 🔐 Güvenlik ve gizlilik

- SABİS öğrenci numaranızı ve şifrenizi yalnızca kendi GitHub Actions Secrets alanınızda saklayın.
- Telegram bot token'ınızı ve PAT'inizi kimseyle paylaşmayın.
- Her kullanıcı kendi private state deposunu ve kendi PAT'ini oluşturmalıdır.
- `son_durum.txt` kişisel ders/not bilgileri içerdiğinden public depoda tutulmamalı veya commit edilmemelidir.
- Token sızdığından şüpheleniyorsanız GitHub üzerinden iptal edip yenisini oluşturun. SABİS şifrenizin sızdığını düşünüyorsanız şifrenizi değiştirin.
- `son_durum.txt` daha önce public depoya commit edildiyse dosyayı yalnızca silmek eski commitlerdeki kopyaları kaldırmaz. Gerekirse Git geçmişinin temizlenmesi gerekir.

## 🛠️ Sorun giderme

| Belirti | Kontrol edilmesi gerekenler |
|---|---|
| `Bad credentials` | `STATE_REPO_TOKEN` içine token adı değil gerçek PAT değerinin girildiğini, token'ın süresinin dolmadığını ve doğru private depoya erişim izni olduğunu kontrol edin. |
| `Repository not found` / private repo checkout hatası | `STATE_REPO` değerinin `owner/repository` biçiminde olduğunu, depo adının doğru yazıldığını ve PAT'in o depoya erişebildiğini kontrol edin. |
| `KeyError` veya eksik environment variable | `OKUL_NO`, `OKUL_SIFRE`, `TG_TOKEN` ve `TG_CHAT_ID` secret'larının eksiksiz tanımlandığını kontrol edin. |
| Telegram mesajı gönderilemiyor | Bot token'ını, `TG_CHAT_ID` değerini ve botla Telegram'da sohbeti başlatmış olduğunuzu kontrol edin. |
| Ders kartları okunamadı | SABİS girişinin tamamlandığını, `/Ders` sayfasının açıldığını ve sayfanın HTML/CSS yapısının değişmediğini kontrol edin. |
| Private depoya push yapılamıyor | PAT için `Contents: Read and write` iznini, token süresini ve private deponun varsayılan dalındaki yazma/koruma ayarlarını kontrol edin. |
| Workflow otomatik çalışmıyor | Workflow dosyasının varsayılan dalda olduğunu, Actions'ın etkin olduğunu ve zamanlanmış workflow'un devre dışı bırakılmadığını kontrol edin. |

Hata ayrıntılarını **Actions → ilgili workflow çalıştırması → başarısız adımın logları** bölümünden görebilirsiniz. Logları paylaşırken öğrenci numarası, şifre, Telegram token'ı ve PAT gibi gizli bilgileri mutlaka kaldırın.

## 📁 Temel dosyalar

```text
obs-takip/
├── .github/
│   └── workflows/
│       └── main.yml       # Zamanlanmış GitHub Actions workflow'u
├── grade_tracker.py       # SABİS girişi, notları okuma ve karşılaştırma
├── requirements.txt       # Python bağımlılıkları
├── .gitignore             # Yerel/geçici dosyalar
└── README.md              # Proje ve kurulum dokümantasyonu
```

Kişisel `son_durum.txt` dosyası çalışma sırasında oluşturulur ve workflow tarafından kullanıcının private state deposuna aktarılır. Bu dosyanın public kaynak deposuna commit edilmemesi gerekir.

## ⚖️ Sorumluluk ve kullanım notu

Bu araç SABİS arayüzünün mevcut HTML yapısına ve erişilebilirliğine bağlıdır. SABİS'te yapılacak arayüz veya giriş sistemi değişiklikleri botun güncellenmesini gerektirebilir. Kontrol sıklığını gereksiz yere artırmayın; varsayılan 15 dakikalık aralığı korumanız önerilir. Sistemin kullanım koşullarına ve kurum politikalarına uygun hareket etmek kullanıcının sorumluluğundadır.

---

⭐ Projeyi faydalı bulduysanız depoya yıldız bırakabilirsiniz.
