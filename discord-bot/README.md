# 🤖 GentlemanStation Discord VIP Botu

Bu bot, Discord sunucunuzdaki üyelerin VIP yetkilerini doğrudan Firebase Firestore ile senkronize eder. 

---

## 🚀 Özellikler

1. **`/vip-ver @kullanici [gun/lifetime]`**: Kullanıcıya Discord'da rol verir ve GentlemanStation masaüstü uygulamasında VIP'sini anında aktif eder.
2. **`/vip-al @kullanici`**: Kullanıcının VIP yetkisini ve rollerini kaldırır.
3. **`/vip-durum [@kullanici]`**: Kullanıcının kalan gün sayısını ve paketini gösterir.
4. **`/key-olustur [gun/lifetime] [adet]`**: Programda girilebilecek tek kullanımlık lisans anahtarı üretir.
5. **⚡ Otomatik Rol Takibi:** Sunucuda birine elle VIP rolü verdiğiniz anda bot bunu algılar ve Firebase'e otomatik kaydeder!

---

## 🛠️ Kurulum Adımları (3 Dakika)

### 1. Discord Developer Portal'dan Bot Oluşturun
1. [Discord Developer Portal](https://discord.com/developers/applications) adresine gidin.
2. **New Application** butonuna basıp bir isim verin (Örn: `GentlemanStation Bot`).
3. Soldaki menüden **Bot** sekmesine gelin.
4. **Reset Token** butonuna basarak **Bot Token**'ınızı kopyalayın.
5. Aynı sayfada aşağı kaydırıp **Privileged Gateway Intents** altındaki:
   * ✅ **Server Members Intent**
   * ✅ **Message Content Intent**  
   seçeneklerini **AÇIK (Enabled)** yapın ve kaydedin.

### 2. Botu Sunucunuza Ekleyin
1. Soldaki **OAuth2** -> **URL Generator** sekmesine gelin.
2. **Scopes:** `bot` ve `applications.commands` seçin.
3. **Bot Permissions:** `Administrator` (veya Rol Yönetimi + Mesaj Gönderme) seçin.
4. Altta oluşan linki tarayıcınızda açarak botu Discord sunucunuza davet edin.

### 3. Ayarları Yapın (`config.json`)
`config.json` dosyasını açın:
```json
{
  "bot_token": "BURAYA_BOT_TOKENINIZI_YAPISTIRIN",
  "firebase_project_id": "gentlemanstation",
  "roles": {
    "vip_role_id": "DISCORD_VIP_ROL_IDSI",
    "lifetime_role_id": "DISCORD_LIFETIME_ROL_IDSI"
  }
}
```
*(Discord'da rollerin ID'sini almak için Discord Ayarları -> Gelişmiş -> Geliştirici Modu'nu açıp role sağ tıklayıp "Rol Kimliğini Kopyala" diyebilirsiniz).*

---

## ▶️ Botu Başlatma
Klasördeki **`run_bot.bat`** dosyasına çift tıklayın! Bot otomatik olarak kütüphaneleri yükleyip çalışacaktır.
