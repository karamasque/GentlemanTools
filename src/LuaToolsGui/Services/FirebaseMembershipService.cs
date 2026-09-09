using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using LuaToolsGui.Models;

namespace LuaToolsGui.Services;

public class FirebaseMembershipService
{
    private readonly AuthService _auth;
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(20) };

    public UserMembership CurrentMembership { get; private set; } = new();
    public event Action<UserMembership>? MembershipChanged;

    public FirebaseMembershipService(AuthService auth)
    {
        _auth = auth;
        _auth.AuthStateChanged += async () => await OnAuthStateChangedAsync();
    }

    public async Task InitializeAsync()
    {
        await RefreshMembershipAsync();
    }

    private async Task OnAuthStateChangedAsync()
    {
        if (!_auth.IsSignedIn)
        {
            CurrentMembership = new UserMembership
            {
                DisplayName = "Misafir",
                TierName = "Free",
                IsPremium = false
            };
            MembershipChanged?.Invoke(CurrentMembership);
            return;
        }

        await RefreshMembershipAsync();
    }

    public async Task<UserMembership> RefreshMembershipAsync()
    {
        if (!_auth.IsSignedIn || string.IsNullOrEmpty(_auth.UserId))
        {
            CurrentMembership = new UserMembership
            {
                DisplayName = _auth.DisplayName ?? "Misafir",
                Email = _auth.Email ?? "",
                AvatarUrl = _auth.AvatarUrl,
                TierName = "Free",
                IsPremium = false
            };
            MembershipChanged?.Invoke(CurrentMembership);
            return CurrentMembership;
        }

        string uid = _auth.UserId!;

        // Default structure in case no Firestore doc exists yet
        var membership = new UserMembership
        {
            Uid = uid,
            Email = _auth.Email ?? "",
            DisplayName = !string.IsNullOrEmpty(_auth.DisplayName) ? _auth.DisplayName! : (_auth.Email?.Split('@')[0] ?? "Üye"),
            AvatarUrl = _auth.AvatarUrl,
            IsPremium = false,
            TierName = "Free"
        };

        if (!string.IsNullOrWhiteSpace(AppConfig.FirebaseProjectId))
        {
            try
            {
                string url = $"https://firestore.googleapis.com/v1/projects/{AppConfig.FirebaseProjectId}/databases/(default)/documents/users/{uid}";
                using var request = new HttpRequestMessage(HttpMethod.Get, url);
                using var response = await _http.SendAsync(request);
                if (response.IsSuccessStatusCode)
                {
                    string body = await response.Content.ReadAsStringAsync();
                    using var doc = JsonDocument.Parse(body);
                    if (doc.RootElement.TryGetProperty("fields", out var fields))
                    {
                        if (fields.TryGetProperty("isPremium", out var p) && p.TryGetProperty("booleanValue", out var bv))
                            membership.IsPremium = bv.GetBoolean();

                        if (fields.TryGetProperty("tier", out var t) && t.TryGetProperty("stringValue", out var sv))
                            membership.TierName = sv.GetString() ?? "Free";

                        if (fields.TryGetProperty("expiresAt", out var exp) && exp.TryGetProperty("timestampValue", out var tv))
                        {
                            if (DateTimeOffset.TryParse(tv.GetString(), out var expDate))
                                membership.ExpiresAt = expDate;
                        }

                        if (fields.TryGetProperty("displayName", out var dn) && dn.TryGetProperty("stringValue", out var dnv))
                            membership.DisplayName = dnv.GetString() ?? membership.DisplayName;
                    }
                }
            }
            catch { }
        }

        CurrentMembership = membership;
        MembershipChanged?.Invoke(CurrentMembership);
        return CurrentMembership;
    }

    public async Task<RedeemKeyResult> RedeemKeyAsync(string rawKey)
    {
        if (string.IsNullOrWhiteSpace(rawKey))
        {
            return new RedeemKeyResult { Success = false, Message = "Lütfen geçerli bir lisans anahtarı girin." };
        }

        if (!_auth.IsSignedIn || string.IsNullOrEmpty(_auth.UserId))
        {
            return new RedeemKeyResult { Success = false, Message = "Lisans anahtarını kullanmak için lütfen önce Discord ile giriş yapın." };
        }

        string cleanKey = rawKey.Trim().ToUpperInvariant();
        string uid = _auth.UserId!;

        // Firestore REST API Key lookup
        if (!string.IsNullOrWhiteSpace(AppConfig.FirebaseProjectId))
        {
            try
            {
                string keyUrl = $"https://firestore.googleapis.com/v1/projects/{AppConfig.FirebaseProjectId}/databases/(default)/documents/keys/{cleanKey}";
                using var request = new HttpRequestMessage(HttpMethod.Get, keyUrl);

                using var response = await _http.SendAsync(request);
                if (!response.IsSuccessStatusCode)
                {
                    return new RedeemKeyResult { Success = false, Message = "Lisans anahtarı geçersiz veya bulunamadı." };
                }

                string body = await response.Content.ReadAsStringAsync();
                using var doc = JsonDocument.Parse(body);
                var fields = doc.RootElement.GetProperty("fields");

                bool isUsed = fields.TryGetProperty("isUsed", out var u) && u.TryGetProperty("booleanValue", out var uv) && uv.GetBoolean();
                if (isUsed)
                {
                    return new RedeemKeyResult { Success = false, Message = "Bu lisans anahtarı daha önce kullanılmış." };
                }

                string tier = fields.TryGetProperty("tier", out var t) && t.TryGetProperty("stringValue", out var tv) ? tv.GetString() ?? "VIP" : "VIP";
                int days = fields.TryGetProperty("days", out var d) && d.TryGetProperty("integerValue", out var dv) && int.TryParse(dv.GetString(), out var dvInt) ? dvInt : 30;

                DateTimeOffset newExpiry = (CurrentMembership.IsActivePremium && CurrentMembership.ExpiresAt.HasValue && CurrentMembership.ExpiresAt.Value > DateTimeOffset.UtcNow)
                    ? CurrentMembership.ExpiresAt.Value.AddDays(days)
                    : DateTimeOffset.UtcNow.AddDays(days);

                if (tier.Equals("Lifetime", StringComparison.OrdinalIgnoreCase) || days >= 36500)
                {
                    newExpiry = DateTimeOffset.UtcNow.AddYears(100);
                }

                // Update user document
                await SaveUserMembershipToFirestoreAsync(uid, true, tier, newExpiry);

                // Mark key as used
                await MarkKeyAsUsedInFirestoreAsync(cleanKey, uid);

                await RefreshMembershipAsync();

                return new RedeemKeyResult
                {
                    Success = true,
                    Message = tier.Equals("Lifetime", StringComparison.OrdinalIgnoreCase)
                        ? "Tebrikler! Sınırsız (Lifetime) Gentleman VIP üyeliğiniz aktif edildi!"
                        : $"Tebrikler! {days} günlük Gentleman VIP üyeliğiniz aktif edildi!",
                    Tier = tier,
                    AddedDays = days,
                    NewExpiresAt = newExpiry
                };
            }
            catch (Exception ex)
            {
                return new RedeemKeyResult { Success = false, Message = $"Sunucu hatası: {ex.Message}" };
            }
        }

        return new RedeemKeyResult { Success = false, Message = "Firebase Project ID yapılandırılmamış." };
    }

    private async Task SaveUserMembershipToFirestoreAsync(string uid, bool isPremium, string tier, DateTimeOffset expiresAt)
    {
        string userUrl = $"https://firestore.googleapis.com/v1/projects/{AppConfig.FirebaseProjectId}/databases/(default)/documents/users/{uid}?updateMask.fieldPaths=isPremium&updateMask.fieldPaths=tier&updateMask.fieldPaths=expiresAt&updateMask.fieldPaths=email&updateMask.fieldPaths=displayName";
        
        var payload = new
        {
            fields = new Dictionary<string, object>
            {
                ["isPremium"] = new { booleanValue = isPremium },
                ["tier"] = new { stringValue = tier },
                ["expiresAt"] = new { timestampValue = expiresAt.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") },
                ["email"] = new { stringValue = _auth.Email ?? "" },
                ["displayName"] = new { stringValue = _auth.DisplayName ?? (_auth.Email?.Split('@')[0] ?? "Üye") }
            }
        };

        using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        using var request = new HttpRequestMessage(new HttpMethod("PATCH"), userUrl) { Content = content };
        await _http.SendAsync(request);
    }

    private async Task MarkKeyAsUsedInFirestoreAsync(string key, string uid)
    {
        string keyUrl = $"https://firestore.googleapis.com/v1/projects/{AppConfig.FirebaseProjectId}/databases/(default)/documents/keys/{key}?updateMask.fieldPaths=isUsed&updateMask.fieldPaths=usedByUid&updateMask.fieldPaths=usedAt";
        
        var payload = new
        {
            fields = new Dictionary<string, object>
            {
                ["isUsed"] = new { booleanValue = true },
                ["usedByUid"] = new { stringValue = uid },
                ["usedAt"] = new { timestampValue = DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") }
            }
        };

        using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        using var request = new HttpRequestMessage(new HttpMethod("PATCH"), keyUrl) { Content = content };
        await _http.SendAsync(request);
    }
}
