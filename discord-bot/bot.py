import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import sys
import secrets
import string
from datetime import datetime, timedelta, timezone
from itertools import cycle
import requests

# Enable immediate stdout flushing
sys.stdout.reconfigure(line_buffering=True)

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    data = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    bot_token = os.environ.get("DISCORD_BOT_TOKEN") or data.get("bot_token") or ""
    firebase_id = os.environ.get("FIREBASE_PROJECT_ID") or data.get("firebase_project_id") or "gentlemanstation"
    vip_role_id = os.environ.get("VIP_ROLE_ID") or data.get("roles", {}).get("vip_role_id") or "1547368688150126682"
    lifetime_role_id = os.environ.get("LIFETIME_ROLE_ID") or data.get("roles", {}).get("lifetime_role_id") or "1547368688150126682"
    admin_role_id = os.environ.get("ADMIN_ROLE_ID") or data.get("admin_role_id") or ""
    guild_id = os.environ.get("GUILD_ID") or data.get("guild_id") or ""

    return {
        "bot_token": bot_token,
        "firebase_project_id": firebase_id,
        "roles": {
            "vip_role_id": vip_role_id,
            "lifetime_role_id": lifetime_role_id
        },
        "admin_role_id": admin_role_id,
        "guild_id": guild_id
    }

config = load_config()
PROJECT_ID = config.get("firebase_project_id", "gentlemanstation")


# ── Firebase REST Helpers ───────────────────────────────────────────

def set_user_vip(uid: str, display_name: str, tier: str, days: int = 30, is_lifetime: bool = False):
    """Save VIP status to Firestore users/{uid}"""
    now = datetime.now(timezone.utc)
    if is_lifetime or str(tier).lower() == "lifetime":
        expires_at = now + timedelta(days=36500) # ~100 years
        tier_name = "Lifetime"
    else:
        expires_at = now + timedelta(days=days)
        tier_name = tier if tier else "VIP"

    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users/{uid}"
    
    payload = {
        "fields": {
            "isPremium": {"booleanValue": True},
            "tier": {"stringValue": tier_name},
            "expiresAt": {"timestampValue": expires_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
            "displayName": {"stringValue": display_name}
        }
    }
    
    resp = requests.patch(url, json=payload, timeout=10)
    print(f"[FIREBASE] set_user_vip: user={display_name} (ID: {uid}) -> HTTP {resp.status_code}", flush=True)
    return resp.status_code in [200, 201], expires_at, tier_name

def revoke_user_vip(uid: str):
    """Remove VIP status from Firestore users/{uid}"""
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users/{uid}"
    payload = {
        "fields": {
            "isPremium": {"booleanValue": False},
            "tier": {"stringValue": "Free"}
        }
    }
    resp = requests.patch(url, json=payload, timeout=10)
    print(f"[FIREBASE] revoke_user_vip: ID={uid} -> HTTP {resp.status_code}", flush=True)
    return resp.status_code in [200, 201]

def get_user_vip(uid: str):
    """Fetch user status from Firestore users/{uid}"""
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users/{uid}"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        fields = data.get("fields", {})
        is_premium = fields.get("isPremium", {}).get("booleanValue", False)
        tier = fields.get("tier", {}).get("stringValue", "Free")
        exp_str = fields.get("expiresAt", {}).get("timestampValue", None)
        return is_premium, tier, exp_str
    return False, "Free", None

def create_license_key(tier: str, days: int):
    """Generate and save license key to keys/{key_code}"""
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    key_code = f"GS-{tier.upper()}-{random_part[:4]}-{random_part[4:]}"
    
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/keys/{key_code}"
    payload = {
        "fields": {
            "tier": {"stringValue": tier},
            "days": {"integerValue": str(days)},
            "isUsed": {"booleanValue": False},
            "createdAt": {"timestampValue": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
        }
    }
    resp = requests.patch(url, json=payload, timeout=10)
    if resp.status_code in [200, 201]:
        return key_code
    return None

def redeem_license_key(key_code: str, uid: str, display_name: str):
    """Validate and redeem license key for a user"""
    key_code = key_code.strip().upper()
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/keys/{key_code}"
    
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return False, "Geçersiz veya bulunamayan lisans anahtarı!"
    
    data = resp.json()
    fields = data.get("fields", {})
    is_used = fields.get("isUsed", {}).get("booleanValue", False)
    if is_used:
        return False, "Bu lisans anahtarı daha önce kullanılmış!"
    
    tier = fields.get("tier", {}).get("stringValue", "VIP")
    days_str = fields.get("days", {}).get("integerValue", "30")
    try:
        days = int(days_str)
    except ValueError:
        days = 30

    is_lifetime = (tier.lower() == "lifetime" or days >= 36500 or days == 0)
    
    # Mark as used in Firestore
    patch_payload = {
        "fields": {
            "tier": {"stringValue": tier},
            "days": {"integerValue": str(days)},
            "isUsed": {"booleanValue": True},
            "usedBy": {"stringValue": str(uid)},
            "usedByName": {"stringValue": display_name},
            "usedAt": {"timestampValue": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
        }
    }
    patch_resp = requests.patch(url, json=patch_payload, timeout=10)
    if patch_resp.status_code not in [200, 201]:
        return False, "Lisans güncellenirken sunucu hatası oluştu!"

    # Activate user VIP status
    ok, expires_at, final_tier = set_user_vip(str(uid), display_name, tier, days, is_lifetime)
    if not ok:
        return False, "Kullanıcı VIP kaydı oluşturulamadı!"

    return True, {
        "tier": final_tier,
        "days": days,
        "is_lifetime": is_lifetime,
        "expires_at": expires_at
    }


# ── Lisans Key Modal & Buton Arayüzü ─────────────────────────────────

class KeyRedeemModal(discord.ui.Modal, title="🔑 Lisans Anahtarı Kullan"):
    key_input = discord.ui.TextInput(
        label="Lisans Anahtarınızı Girin (Key)",
        placeholder="Örn: GS-VIP-XXXX-XXXX",
        required=True,
        min_length=6,
        max_length=40
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        key_val = self.key_input.value.strip()

        success, res = redeem_license_key(key_val, str(interaction.user.id), interaction.user.display_name)
        
        if not success:
            await interaction.followup.send(f"❌ **Hata:** {res}", ephemeral=True)
            return

        tier = res["tier"]
        days = res["days"]
        is_life = res["is_lifetime"]
        expires_at = res["expires_at"]

        # Sunucuda ilgili rolü ver
        cfg = load_config()
        vip_role_id = cfg.get("roles", {}).get("lifetime_role_id" if is_life else "vip_role_id")
        if interaction.guild and vip_role_id and str(vip_role_id).isdigit():
            role = interaction.guild.get_role(int(vip_role_id))
            if role:
                try:
                    await interaction.user.add_roles(role)
                except Exception as e:
                    print(f"Modal rol verme hatası: {e}")

        # SADECE ÖZELDEN (DM) detaylı tebrik mesajı gönder
        try:
            dm_embed = discord.Embed(
                title="👑 Lisansınız Başarıyla Aktif Edildi!",
                description=f"Merhaba **{interaction.user.display_name}**,\n**GentlemanStation** lisans anahtarınız hesabınıza başarıyla tanımlandı.",
                color=0xFBBF24 if is_life else 0x38BDF8,
                timestamp=datetime.now(timezone.utc)
            )
            dm_embed.add_field(name="👑 Paket", value="`👑 Lifetime Altın VIP`" if is_life else f"`💎 {tier}`", inline=True)
            dm_embed.add_field(name="⏳ Süre", value="`Süresiz (Ömür Boyu)`" if is_life else f"`{days} Gün`", inline=True)
            dm_embed.add_field(name="📅 Bitiş Tarihi", value="`Süresiz`" if is_life else f"`{expires_at.strftime('%d.%m.%Y %H:%M')}`", inline=False)
            dm_embed.set_footer(text="GentlemanStation VIP Suite", icon_url=bot.user.display_avatar.url if bot.user else None)
            await interaction.user.send(embed=dm_embed)
        except Exception:
            pass

        # Kullanıcıya sadece kendisinin gördüğü (ephemeral) onay mesajı
        await interaction.followup.send(
            f"🎉 **Tebrikler {interaction.user.mention}!**\n"
            f"**{tier}** paketiniz başarıyla aktif edildi ve rolünüz tanımlandı! 🎩\n"
            f"*(Detaylı bilgi özel mesaj (DM) olarak iletildi)*",
            ephemeral=True
        )

class KeyPanelButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lisans Anahtarı Kullan", style=discord.ButtonStyle.success, emoji="🔑", custom_id="gs_key_redeem_btn_v1")
    async def redeem_button_clicked(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KeyRedeemModal())


# ── Discord Bot Setup ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class GentlemanBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        self.add_view(KeyPanelButtonView())

bot = GentlemanBot()


# ── Otomatik Dönen Durum Mesajları ──────────────────────────────────

STATUS_MESSAGES = cycle([
    "Zapay Yekalı Steam 🤖😂",
    "Gabe Newell ile tavla oynuyor 🎲",
    "Gözler GentlemanStation VIP'lerde 👀🎩",
    "Manifestleri 300 km/s ile indiriyor 🏎️💨",
    "Yapay Zeka değil, Zapay Yeka 🧠🍷",
    "Steam Cüzdan Kodları yükleniyor... %99 💸",
    "👑 GentlemanStation VIP Suite",
    "!key-paneli | GentlemanStation 🎩"
])

@tasks.loop(seconds=15)
async def rotate_status():
    msg = next(STATUS_MESSAGES)
    try:
        await bot.change_presence(activity=discord.CustomActivity(name=msg))
    except Exception:
        pass


# ── Özelden (DM) VIP Bitiş Hatırlatıcısı ─────────────────────────────

notified_reminders = set()

@tasks.loop(hours=6)
async def check_vip_expirations():
    """Kullanıcıların VIP bitiş tarihini kontrol eder ve sadece ÖZELDEN (DM) bildirir."""
    await bot.wait_until_ready()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    for g in bot.guilds:
        for member in g.members:
            if member.bot:
                continue

            try:
                is_premium, tier, exp_str = get_user_vip(str(member.id))
                if not is_premium or tier.lower() == "lifetime" or not exp_str:
                    continue

                try:
                    exp_date = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                except Exception:
                    continue

                remaining = exp_date - now
                days_left = remaining.days

                if 0 <= days_left <= 3:
                    notify_key = f"{member.id}_{today_str}_{days_left}"
                    if notify_key not in notified_reminders:
                        notified_reminders.add(notify_key)
                        try:
                            embed = discord.Embed(
                                title="⏳ GentlemanStation VIP Süreniz Dolmak Üzere!",
                                description=(
                                    f"Merhaba **{member.display_name}**,\n\n"
                                    f"**GentlemanStation** `{tier}` üyeliğinizin sona ermesine **{max(days_left, 1)} gün** kaldı!\n\n"
                                    f"📅 **Bitiş Tarihi:** `{exp_date.strftime('%d.%m.%Y %H:%M')}`\n"
                                    f"Kesintisiz erişim ve VIP ayrıcalıklarına devam etmek için lisansınızı yenileyebilirsiniz. 🎩"
                                ),
                                color=0xF59E0B,
                                timestamp=now
                            )
                            embed.set_footer(text="GentlemanStation VIP Bildirim Sistemi", icon_url=bot.user.display_avatar.url if bot.user else None)
                            await member.send(embed=embed)
                            print(f"[DM BİLDİRİM] {member.display_name} kullanıcısına {days_left} gün kala DM hatırlatması iletildi.")
                        except Exception as e:
                            print(f"[DM UYARI] {member.display_name} kullanıcısına DM atılamadı: {e}")
            except Exception:
                pass


# ── Prefix Commands (!key-paneli, !vip-ver vb.) ─────────────────────

@bot.command(name="key-paneli", aliases=["keypanel", "lisans-paneli", "panel"])
async def prefix_key_paneli(ctx):
    """Kanala butonlu lisans aktivasyon paneli gönderir."""
    embed = discord.Embed(
        title="🎩 GentlemanStation Lisans Aktivasyon Paneli",
        description=(
            "Satın aldığınız veya edindiğiniz **GentlemanStation VIP** lisans anahtarını (Key)\n"
            "kullanmak ve anında VIP rolünüzü almak için aşağıdaki butona tıklayın!\n\n"
            "✨ *Butona tıkladığınızda açılan pencereye lisans kodunuzu girmeniz yeterlidir.*"
        ),
        color=0xFBBF24,
        timestamp=datetime.now(timezone.utc)
    )
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.set_footer(text="GentlemanStation VIP Suite • 7/24 Aktif", icon_url=bot.user.display_avatar.url)
    
    embed.add_field(name="🛡️ Otomatik Teslimat", value="Key girdiğiniz anda rolünüz ve süreniz anında tanımlanır.", inline=False)

    await ctx.send(embed=embed, view=KeyPanelButtonView())

@bot.command(name="vip-ver", aliases=["vipver"])
@commands.has_permissions(administrator=True)
async def prefix_vip_ver(ctx, kullanici: discord.Member, sure_gun: str = "30", paket: str = "VIP"):
    is_lifetime = sure_gun.strip().lower() in ["lifetime", "sınırsız", "sinirsiz", "omurboyu", "ömürboyu", "unlimited", "0", "altin", "altın"]
    days = 30
    if not is_lifetime:
        try:
            days = int(sure_gun)
        except ValueError:
            await ctx.send("❌ Hata: Gün sayısı sayısal olmalıdır (örn: 30) veya 'lifetime' yazmalısınız.")
            return

    tier_name = "Lifetime" if is_lifetime else paket.upper()
    success, expires_at, final_tier = set_user_vip(str(kullanici.id), kullanici.display_name, tier_name, days, is_lifetime)

    if success:
        cfg = load_config()
        vip_role_id = cfg.get("roles", {}).get("lifetime_role_id" if is_lifetime else "vip_role_id")
        if vip_role_id and str(vip_role_id).isdigit():
            role = ctx.guild.get_role(int(vip_role_id))
            if role:
                try:
                    await kullanici.add_roles(role)
                except Exception as e:
                    print(f"Rol verme hatasi: {e}")

        # Özelden DM Bildirimi
        try:
            dm_embed = discord.Embed(
                title="👑 VIP Üyeliğiniz Tanımlandı!",
                description=f"Merhaba **{kullanici.display_name}**,\nSunucu yöneticisi tarafından GentlemanStation VIP üyeliğiniz aktif edildi! 🎩",
                color=0xFBBF24 if is_lifetime else 0x38BDF8,
                timestamp=datetime.now(timezone.utc)
            )
            dm_embed.add_field(name="👑 Paket", value="`👑 Lifetime Altın VIP`" if is_lifetime else f"`💎 {final_tier}`", inline=True)
            dm_embed.add_field(name="⏳ Süre", value="`Süresiz (Ömür Boyu)`" if is_lifetime else f"`{days} Gün`", inline=True)
            dm_embed.add_field(name="📅 Bitiş Tarihi", value="`Süresiz`" if is_lifetime else f"`{expires_at.strftime('%d.%m.%Y %H:%M')}`", inline=False)
            await kullanici.send(embed=dm_embed)
        except Exception:
            pass

        embed = discord.Embed(
            title="👑 Lifetime Altın VIP Tanımlandı!" if is_lifetime else "💎 VIP Üyelik Başarıyla Tanımlandı!",
            description=f"**{kullanici.mention}** kullanıcısına GentlemanStation VIP üyeliği verildi.",
            color=0xFBBF24 if is_lifetime else 0x38BDF8,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=kullanici.display_avatar.url)
        embed.add_field(name="👑 Paket", value="`👑 SÜRESİZ ALTIN VIP`" if is_lifetime else f"`💎 {final_tier}`", inline=True)
        embed.add_field(name="⏳ Süre", value="`Süresiz (Ömür Boyu)`" if is_lifetime else f"`{days} Gün`", inline=True)
        embed.add_field(name="📅 Bitiş", value="`Süresiz / Ömür Boyu`" if is_lifetime else f"`{expires_at.strftime('%d.%m.%Y %H:%M')}`", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Firebase sunucusuna kaydedilirken hata oluştu.")

@bot.command(name="vip-durum", aliases=["vipdurum"])
async def prefix_vip_durum(ctx, kullanici: discord.Member = None):
    target = kullanici or ctx.author
    is_premium, tier, exp_str = get_user_vip(str(target.id))
    
    embed = discord.Embed(
        title=f"👤 Üyelik Durumu: {target.display_name}",
        color=0x38BDF8 if is_premium else 0x64748B,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    if is_premium:
        is_life = tier.lower() == "lifetime" or exp_str is None
        embed.add_field(name="Durum", value="💎 **VIP AKTİF**", inline=True)
        embed.add_field(name="Paket", value=f"`{tier}`", inline=True)
        embed.add_field(name="Bitiş", value="`Süresiz (Ömür Boyu)`" if is_life else f"`{exp_str[:10]}`", inline=False)
    else:
        embed.add_field(name="Durum", value="🆓 **Standart Üye**", inline=True)
        embed.add_field(name="Bilgi", value="Henüz aktif bir VIP üyeliği bulunmuyor.", inline=False)
    await ctx.send(embed=embed)


# ── Slash Commands ──────────────────────────────────────────────────

@bot.tree.command(name="key-paneli", description="Kanala butonlu lisans aktivasyon paneli gönderir.")
async def slash_key_paneli(interaction: discord.Interaction):
    # Only allow administrators or guild managers
    if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Bu komutu sadece sunucu yöneticileri kullanabilir.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎩 GentlemanStation Lisans Aktivasyon Paneli",
        description=(
            "Satın aldığınız veya edindiğiniz **GentlemanStation VIP** lisans anahtarını (Key)\n"
            "kullanmak ve anında VIP rolünüzü almak için aşağıdaki butona tıklayın!\n\n"
            "✨ *Butona tıkladığınızda açılan pencereye lisans kodunuzu girmeniz yeterlidir.*"
        ),
        color=0xFBBF24,
        timestamp=datetime.now(timezone.utc)
    )
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.set_footer(text="GentlemanStation VIP Suite • 7/24 Aktif", icon_url=bot.user.display_avatar.url)

    embed.add_field(name="🛡️ Otomatik Teslimat", value="Key girdiğiniz anda rolünüz ve süreniz anında tanımlanır.", inline=False)

    await interaction.response.send_message(embed=embed, view=KeyPanelButtonView())

@bot.tree.command(name="vip-ver", description="Kullanıcıya GentlemanStation VIP üyeliği tanımlar.")
@app_commands.describe(
    kullanici="VIP verilecek Discord üyesi",
    sure_gun="Kaç gün VIP verilecek? (Örn: 30, 90) veya Sınırsız Altın VIP için 'lifetime' yazın",
    paket="Paket türü (Varsayılan: VIP)"
)
async def vip_ver(interaction: discord.Interaction, kullanici: discord.Member, sure_gun: str, paket: str = "VIP"):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Bu komutu sadece yöneticiler kullanabilir.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    
    is_lifetime = sure_gun.strip().lower() in ["lifetime", "sınırsız", "sinirsiz", "omurboyu", "ömürboyu", "unlimited", "0", "altin", "altın"]
    days = 30
    if not is_lifetime:
        try:
            days = int(sure_gun)
        except ValueError:
            await interaction.followup.send("❌ Hata: Gün sayısı sayısal bir değer olmalıdır (örn: 30) veya 'lifetime' yazmalısınız.")
            return

    tier_name = "Lifetime" if is_lifetime else paket.upper()
    success, expires_at, final_tier = set_user_vip(str(kullanici.id), kullanici.display_name, tier_name, days, is_lifetime)

    if success:
        cfg = load_config()
        vip_role_id = cfg.get("roles", {}).get("lifetime_role_id" if is_lifetime else "vip_role_id")
        if vip_role_id and str(vip_role_id).isdigit():
            role = interaction.guild.get_role(int(vip_role_id))
            if role:
                try:
                    await kullanici.add_roles(role)
                except Exception:
                    pass

        # Özelden DM Bildirimi
        try:
            dm_embed = discord.Embed(
                title="👑 VIP Üyeliğiniz Tanımlandı!",
                description=f"Merhaba **{kullanici.display_name}**,\nSunucu yöneticisi tarafından GentlemanStation VIP üyeliğiniz aktif edildi! 🎩",
                color=0xFBBF24 if is_lifetime else 0x38BDF8,
                timestamp=datetime.now(timezone.utc)
            )
            dm_embed.add_field(name="👑 Paket", value="`👑 Lifetime Altın VIP`" if is_lifetime else f"`💎 {final_tier}`", inline=True)
            dm_embed.add_field(name="⏳ Süre", value="`Süresiz (Ömür Boyu)`" if is_lifetime else f"`{days} Gün`", inline=True)
            dm_embed.add_field(name="📅 Bitiş Tarihi", value="`Süresiz`" if is_lifetime else f"`{expires_at.strftime('%d.%m.%Y %H:%M')}`", inline=False)
            await kullanici.send(embed=dm_embed)
        except Exception:
            pass

        embed = discord.Embed(
            title="👑 Lifetime Altın VIP Başarıyla Tanımlandı!" if is_lifetime else "💎 VIP Üyelik Başarıyla Tanımlandı!",
            description=f"**{kullanici.mention}** kullanıcısına GentlemanStation VIP üyeliği verildi.",
            color=0xFBBF24 if is_lifetime else 0x38BDF8,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=kullanici.display_avatar.url)
        embed.add_field(name="👑 Paket", value="`👑 SÜRESİZ ALTIN VIP`" if is_lifetime else f"`💎 {final_tier}`", inline=True)
        embed.add_field(name="⏳ Süre", value="`Süresiz (Ömür Boyu)`" if is_lifetime else f"`{days} Gün`", inline=True)
        embed.add_field(name="📅 Bitiş Tarihi", value="`Ömür Boyu`" if is_lifetime else f"`{expires_at.strftime('%d.%m.%Y %H:%M')}`", inline=False)
        embed.set_footer(text="GentlemanStation VIP Sistemi", icon_url=bot.user.display_avatar.url if bot.user else None)
        
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Firebase sunucusuna bağlanırken hata oluştu.")

@bot.tree.command(name="vip-al", description="Kullanıcının GentlemanStation VIP üyeliğini iptal eder.")
@app_commands.describe(kullanici="VIP üyeliği iptal edilecek üye")
async def vip_al(interaction: discord.Interaction, kullanici: discord.Member):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Bu komutu sadece yöneticiler kullanabilir.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    
    success = revoke_user_vip(str(kullanici.id))
    if success:
        cfg = load_config()
        for r_key in ["vip_role_id", "lifetime_role_id"]:
            rid = cfg.get("roles", {}).get(r_key)
            if rid and str(rid).isdigit():
                role = interaction.guild.get_role(int(rid))
                if role and role in kullanici.roles:
                    try:
                        await kullanici.remove_roles(role)
                    except Exception:
                        pass

        # Özelden DM Bildirimi
        try:
            dm_embed = discord.Embed(
                title="🚫 VIP Üyeliğiniz Sona Erdi",
                description=f"Merhaba **{kullanici.display_name}**,\nGentlemanStation VIP üyeliğiniz ve ayrıcalıklarınız kaldırılmıştır.",
                color=0xEF4444,
                timestamp=datetime.now(timezone.utc)
            )
            await kullanici.send(embed=dm_embed)
        except Exception:
            pass

        embed = discord.Embed(
            title="🚫 VIP Üyelik İptal Edildi",
            description=f"**{kullanici.mention}** kullanıcısının VIP yetkisi ve üyelik ayrıcalıkları kaldırıldı.",
            color=0xEF4444,
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Firebase güncellemesi başarısız oldu.")

@bot.tree.command(name="vip-durum", description="Bir kullanıcının (veya kendinizin) VIP durumunu görüntüler.")
@app_commands.describe(kullanici="Durumu sorgulanacak üye (boş bırakılırsa kendiniz)")
async def vip_durum(interaction: discord.Interaction, kullanici: discord.Member = None):
    target = kullanici or interaction.user
    await interaction.response.defer(ephemeral=False)
    
    is_premium, tier, exp_str = get_user_vip(str(target.id))
    is_life = is_premium and (tier.lower() == "lifetime" or exp_str is None)
    
    embed = discord.Embed(
        title=f"👤 Üyelik Durumu: {target.display_name}",
        color=0xFBBF24 if is_life else (0x38BDF8 if is_premium else 0x64748B),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    if is_premium:
        embed.add_field(name="Durum", value="👑 **SÜRESİZ ALTIN VIP**" if is_life else "💎 **VIP AKTİF**", inline=True)
        embed.add_field(name="Paket", value=f"`{tier}`", inline=True)
        embed.add_field(name="Bitiş", value="`Süresiz (Ömür Boyu)`" if is_life else f"`{exp_str[:10]}`", inline=False)
    else:
        embed.add_field(name="Durum", value="🆓 **Standart Üye**", inline=True)
        embed.add_field(name="Bilgi", value="Henüz aktif bir VIP üyeliği bulunmuyor.", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="key-olustur", description="Programda veya butonda kullanılabilecek lisans anahtarı (Key) üretir.")
@app_commands.describe(
    sure_gun="Kaç günlük anahtar? (Örn: 30) veya 'lifetime'",
    adet="Kaç adet anahtar üretilsin? (Varsayılan: 1)",
    paket="Paket adı (Varsayılan: VIP)"
)
async def key_olustur(interaction: discord.Interaction, sure_gun: str, adet: int = 1, paket: str = "VIP"):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Bu komutu sadece yöneticiler kullanabilir.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    is_lifetime = sure_gun.strip().lower() in ["lifetime", "sınırsız", "sinirsiz", "omurboyu", "ömürboyu", "unlimited", "0", "altin", "altın"]
    days = 30
    if not is_lifetime:
        try:
            days = int(sure_gun)
        except ValueError:
            await interaction.followup.send("❌ Hata: Gün sayısı bir sayı olmalıdır.")
            return

    tier_name = "Lifetime" if is_lifetime else paket.upper()
    keys = []
    
    for _ in range(min(adet, 20)):
        k = create_license_key(tier_name, 36500 if is_lifetime else days)
        if k:
            keys.append(k)

    if keys:
        keys_formatted = "\n".join([f"`{k}`" for k in keys])
        embed = discord.Embed(
            title="🔑 Lisans Anahtarları Oluşturuldu",
            description=f"Aşağıdaki anahtarlar programda veya `/key-paneli` butonunda kullanılabilir:\n\n{keys_formatted}",
            color=0xFBBF24 if is_lifetime else 0x10B981,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Paket", value="`👑 Lifetime Altın VIP`" if is_lifetime else f"`{tier_name}`", inline=True)
        embed.add_field(name="Süre", value="`Süresiz (Ömür Boyu)`" if is_lifetime else f"`{days} Gün`", inline=True)
        embed.set_footer(text="Bu mesaj sadece size görünür.")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Anahtar oluşturulurken hata oluştu.")


# ── Message Event ───────────────────────────────────────────────────

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)


# ── Role Event Listener (Otomatik Rol Senkronizasyonu) ──────────────

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Discord sunucusunda birine elle VIP rolü verildiğinde Firebase'e otomatik yazar."""
    cfg = load_config()
    vip_role_id = cfg.get("roles", {}).get("vip_role_id")
    lifetime_role_id = cfg.get("roles", {}).get("lifetime_role_id")

    added_roles = set(after.roles) - set(before.roles)
    removed_roles = set(before.roles) - set(after.roles)

    # Rol eklendiyse
    for role in added_roles:
        is_gold_role = (str(role.id) == str(lifetime_role_id) and str(lifetime_role_id) != str(vip_role_id)) or \
                       any(kw in role.name.lower() for kw in ["lifetime", "sınırsız", "omurboyu", "ömür", "gold", "altın"])
        
        if is_gold_role:
            set_user_vip(str(after.id), after.display_name, "Lifetime", 36500, is_lifetime=True)
            print(f"[+] {after.display_name} kullanıcısına Lifetime Altın VIP rolü verildi -> Firebase güncellendi.")
        elif str(role.id) == str(vip_role_id) or "vip" in role.name.lower():
            set_user_vip(str(after.id), after.display_name, "VIP", 30, is_lifetime=False)
            print(f"[+] {after.display_name} kullanıcısına 30 Günlük VIP rolü verildi -> Firebase güncellendi.")

    # Rol kaldırıldıysa
    for role in removed_roles:
        if str(role.id) in [str(vip_role_id), str(lifetime_role_id)] or "vip" in role.name.lower() or "gold" in role.name.lower():
            has_other_vip = any(
                (str(r.id) in [str(vip_role_id), str(lifetime_role_id)]) or "vip" in r.name.lower() or "gold" in r.name.lower()
                for r in after.roles
            )
            if not has_other_vip:
                revoke_user_vip(str(after.id))
                print(f"[-] {after.display_name} kullanıcısının VIP rolü alındı -> Firebase iptal edildi.")


# ── Bot Başlangıç Olayı (on_ready) ───────────────────────────────────

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"[*] GentlemanStation Discord Bot Aktif: {bot.user}")
    print(f"[*] Bağlı Sunucu Sayısı: {len(bot.guilds)}")

    # Her sunucuya slash komutlarını zorla senkronize et
    for g in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=g)
            await bot.tree.sync(guild=g)
            print(f"[+] Slash komutlar ANINDA senkronize edildi: {g.name} ({g.id})")
        except Exception as e:
            print(f"[-] Slash senkronizasyon hatası ({g.id}): {e}")

    try:
        await bot.tree.sync() # Global sync
        print("[+] Global slash komutlar senkronize edildi.")
    except Exception as e:
        print(f"[-] Global sync hatası: {e}")

    # Görevleri Başlat
    if not rotate_status.is_running():
        rotate_status.start()
    if not check_vip_expirations.is_running():
        check_vip_expirations.start()

    print("=" * 50)


# ── Entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from keep_alive import keep_alive
        keep_alive()
        print("[+] Web sunucusu 7/24 uyanık tutma servisi başlatıldı.")
    except Exception as e:
        print(f"[!] Keep-alive web servisi başlatılamadı: {e}")

    cfg = load_config()
    token = os.environ.get("DISCORD_BOT_TOKEN") or cfg.get("bot_token", "").strip()
    if not token or token == "DISCORD_BOT_TOKENINIZI_BURAYA_YAZIN":
        print("=" * 60)
        print("HATA: config.json dosyasında veya DISCORD_BOT_TOKEN çevresel değişkeninde 'bot_token' belirtilmemiş!")
        print("Lütfen Discord Developer Portal'dan aldığınız Bot Token'ı config.json'a yazın.")
        print("=" * 60)
    else:
        bot.run(token)
