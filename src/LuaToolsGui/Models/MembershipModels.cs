using System;
using System.Text.Json.Serialization;

namespace LuaToolsGui.Models;

public enum MembershipTier
{
    Free,
    VIP,
    Diamond,
    Lifetime
}

public class UserMembership
{
    [JsonPropertyName("uid")]
    public string Uid { get; set; } = string.Empty;

    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;

    [JsonPropertyName("displayName")]
    public string DisplayName { get; set; } = string.Empty;

    [JsonPropertyName("avatarUrl")]
    public string? AvatarUrl { get; set; }

    [JsonPropertyName("isPremium")]
    public bool IsPremium { get; set; }

    [JsonPropertyName("tier")]
    public string TierName { get; set; } = "Free";

    [JsonPropertyName("expiresAt")]
    public DateTimeOffset? ExpiresAt { get; set; }

    [JsonPropertyName("createdAt")]
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    [JsonIgnore]
    public bool IsLifetime => IsPremium && (TierName.Equals("Lifetime", StringComparison.OrdinalIgnoreCase) || ExpiresAt == null || ExpiresAt > DateTimeOffset.UtcNow.AddYears(50));

    [JsonIgnore]
    public bool IsActivePremium => IsPremium && (IsLifetime || (ExpiresAt.HasValue && ExpiresAt.Value > DateTimeOffset.UtcNow));

    [JsonIgnore]
    public int DaysRemaining
    {
        get
        {
            if (!IsActivePremium) return 0;
            if (IsLifetime) return 9999;
            return Math.Max(0, (int)Math.Ceiling((ExpiresAt!.Value - DateTimeOffset.UtcNow).TotalDays));
        }
    }

    [JsonIgnore]
    public string StatusText
    {
        get
        {
            if (!IsActivePremium) return "Standart Üye";
            if (IsLifetime) return "💎 Gentleman Lifetime VIP";
            return $"💎 Gentleman VIP ({DaysRemaining} gün kaldı)";
        }
    }
}

public class RedeemKeyResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public string? Tier { get; set; }
    public int AddedDays { get; set; }
    public DateTimeOffset? NewExpiresAt { get; set; }
}

public class FirebaseAuthResult
{
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
    public string? IdToken { get; set; }
    public string? RefreshToken { get; set; }
    public string? LocalId { get; set; }
    public string? Email { get; set; }
    public string? DisplayName { get; set; }
    public long ExpiresIn { get; set; }
}
