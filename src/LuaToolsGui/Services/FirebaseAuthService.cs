using System;
using System.IO;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using LuaToolsGui.Models;

namespace LuaToolsGui.Services;

public class FirebaseAuthService
{
    private static readonly string SessionFile = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "GentlemanStation", "firebase_auth.dat");

    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(25) };
    private readonly SemaphoreSlim _lock = new(1, 1);

    private string? _idToken;
    private string? _refreshToken;
    private DateTimeOffset _expiresAt;

    public string? Uid { get; private set; }
    public string? Email { get; private set; }
    public string? DisplayName { get; private set; }
    public string? PhotoUrl { get; private set; }

    public bool IsSignedIn => !string.IsNullOrEmpty(_idToken) && !string.IsNullOrEmpty(Uid);
    public string? CurrentIdToken => _idToken;

    public event Action? AuthStateChanged;

    public async Task InitializeAsync()
    {
        try
        {
            if (!File.Exists(SessionFile)) return;

            byte[] protectedBytes = await File.ReadAllBytesAsync(SessionFile);
            byte[] rawBytes = ProtectedData.Unprotect(protectedBytes, null, DataProtectionScope.CurrentUser);
            string json = Encoding.UTF8.GetString(rawBytes);

            var stored = JsonSerializer.Deserialize<StoredSession>(json);
            if (stored == null || string.IsNullOrEmpty(stored.RefreshToken)) return;

            _idToken = stored.IdToken;
            _refreshToken = stored.RefreshToken;
            _expiresAt = stored.ExpiresAt;
            Uid = stored.Uid;
            Email = stored.Email;
            DisplayName = stored.DisplayName;
            PhotoUrl = stored.PhotoUrl;

            if (_expiresAt > DateTimeOffset.UtcNow.AddMinutes(5))
            {
                AuthStateChanged?.Invoke();
                return;
            }

            // Token is close to expiring, refresh it
            await RefreshTokenAsync();
        }
        catch
        {
            ClearSession();
        }
    }

    public async Task<FirebaseAuthResult> SignUpWithEmailAsync(string email, string password, string displayName)
    {
        if (string.IsNullOrWhiteSpace(AppConfig.FirebaseAuthApiKey))
        {
            return new FirebaseAuthResult { Success = false, ErrorMessage = "Firebase API Key yapılandırılmamış." };
        }

        try
        {
            string url = $"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={AppConfig.FirebaseAuthApiKey}";
            var payload = new
            {
                email = email.Trim(),
                password,
                returnSecureToken = true
            };

            using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            using var response = await _http.PostAsync(url, content);
            string responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                return ParseFirebaseError(responseBody);
            }

            using var doc = JsonDocument.Parse(responseBody);
            var root = doc.RootElement;

            _idToken = root.GetProperty("idToken").GetString();
            _refreshToken = root.GetProperty("refreshToken").GetString();
            Uid = root.GetProperty("localId").GetString();
            Email = root.GetProperty("email").GetString();
            string expiresInStr = root.GetProperty("expiresIn").GetString() ?? "3600";
            long expiresIn = long.TryParse(expiresInStr, out var exp) ? exp : 3600;
            _expiresAt = DateTimeOffset.UtcNow.AddSeconds(expiresIn);
            DisplayName = displayName.Trim();

            // Set Display Name in Firebase
            if (!string.IsNullOrWhiteSpace(displayName))
            {
                await UpdateProfileAsync(displayName, null);
            }

            await SaveSessionAsync();
            AuthStateChanged?.Invoke();

            return new FirebaseAuthResult
            {
                Success = true,
                IdToken = _idToken,
                RefreshToken = _refreshToken,
                LocalId = Uid,
                Email = Email,
                DisplayName = DisplayName,
                ExpiresIn = expiresIn
            };
        }
        catch (Exception ex)
        {
            return new FirebaseAuthResult { Success = false, ErrorMessage = $"Bağlantı hatası: {ex.Message}" };
        }
    }

    public async Task<FirebaseAuthResult> SignInWithEmailAsync(string email, string password)
    {
        if (string.IsNullOrWhiteSpace(AppConfig.FirebaseAuthApiKey))
        {
            return new FirebaseAuthResult { Success = false, ErrorMessage = "Firebase API Key yapılandırılmamış." };
        }

        try
        {
            string url = $"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={AppConfig.FirebaseAuthApiKey}";
            var payload = new
            {
                email = email.Trim(),
                password,
                returnSecureToken = true
            };

            using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            using var response = await _http.PostAsync(url, content);
            string responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                return ParseFirebaseError(responseBody);
            }

            using var doc = JsonDocument.Parse(responseBody);
            var root = doc.RootElement;

            _idToken = root.GetProperty("idToken").GetString();
            _refreshToken = root.GetProperty("refreshToken").GetString();
            Uid = root.GetProperty("localId").GetString();
            Email = root.GetProperty("email").GetString();
            DisplayName = root.TryGetProperty("displayName", out var dn) ? dn.GetString() : null;
            string expiresInStr = root.GetProperty("expiresIn").GetString() ?? "3600";
            long expiresIn = long.TryParse(expiresInStr, out var exp) ? exp : 3600;
            _expiresAt = DateTimeOffset.UtcNow.AddSeconds(expiresIn);

            await SaveSessionAsync();
            AuthStateChanged?.Invoke();

            return new FirebaseAuthResult
            {
                Success = true,
                IdToken = _idToken,
                RefreshToken = _refreshToken,
                LocalId = Uid,
                Email = Email,
                DisplayName = DisplayName,
                ExpiresIn = expiresIn
            };
        }
        catch (Exception ex)
        {
            return new FirebaseAuthResult { Success = false, ErrorMessage = $"Bağlantı hatası: {ex.Message}" };
        }
    }

    public async Task<bool> SendPasswordResetEmailAsync(string email)
    {
        if (string.IsNullOrWhiteSpace(AppConfig.FirebaseAuthApiKey)) return false;

        try
        {
            string url = $"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={AppConfig.FirebaseAuthApiKey}";
            var payload = new
            {
                requestType = "PASSWORD_RESET",
                email = email.Trim()
            };

            using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            using var response = await _http.PostAsync(url, content);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<bool> UpdateProfileAsync(string? displayName, string? photoUrl)
    {
        if (string.IsNullOrEmpty(_idToken) || string.IsNullOrWhiteSpace(AppConfig.FirebaseAuthApiKey)) return false;

        try
        {
            string url = $"https://identitytoolkit.googleapis.com/v1/accounts:update?key={AppConfig.FirebaseAuthApiKey}";
            var payload = new
            {
                idToken = _idToken,
                displayName,
                photoUrl,
                returnSecureToken = true
            };

            using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            using var response = await _http.PostAsync(url, content);

            if (response.IsSuccessStatusCode)
            {
                if (!string.IsNullOrEmpty(displayName)) DisplayName = displayName;
                if (!string.IsNullOrEmpty(photoUrl)) PhotoUrl = photoUrl;
                await SaveSessionAsync();
                AuthStateChanged?.Invoke();
                return true;
            }
        }
        catch { }

        return false;
    }

    public async Task<string?> GetValidTokenAsync()
    {
        await _lock.WaitAsync();
        try
        {
            if (string.IsNullOrEmpty(_refreshToken)) return null;

            if (_expiresAt > DateTimeOffset.UtcNow.AddMinutes(2) && !string.IsNullOrEmpty(_idToken))
            {
                return _idToken;
            }

            bool refreshed = await RefreshTokenInternalAsync();
            return refreshed ? _idToken : null;
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task<bool> RefreshTokenAsync()
    {
        await _lock.WaitAsync();
        try
        {
            return await RefreshTokenInternalAsync();
        }
        finally
        {
            _lock.Release();
        }
    }

    private async Task<bool> RefreshTokenInternalAsync()
    {
        if (string.IsNullOrEmpty(_refreshToken) || string.IsNullOrWhiteSpace(AppConfig.FirebaseAuthApiKey)) return false;

        try
        {
            string url = $"https://securetoken.googleapis.com/v1/token?key={AppConfig.FirebaseAuthApiKey}";
            var form = new FormUrlEncodedContent(new[]
            {
                new KeyValuePair<string, string>("grant_type", "refresh_token"),
                new KeyValuePair<string, string>("refresh_token", _refreshToken)
            });

            using var response = await _http.PostAsync(url, form);
            string body = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                ClearSession();
                AuthStateChanged?.Invoke();
                return false;
            }

            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;

            _idToken = root.GetProperty("id_token").GetString();
            _refreshToken = root.GetProperty("refresh_token").GetString();
            Uid = root.GetProperty("user_id").GetString();
            string expSec = root.GetProperty("expires_in").GetString() ?? "3600";
            long expSeconds = long.TryParse(expSec, out var s) ? s : 3600;
            _expiresAt = DateTimeOffset.UtcNow.AddSeconds(expSeconds);

            await SaveSessionAsync();
            AuthStateChanged?.Invoke();
            return true;
        }
        catch
        {
            return false;
        }
    }

    public void SignOut()
    {
        ClearSession();
        AuthStateChanged?.Invoke();
    }

    private void ClearSession()
    {
        _idToken = null;
        _refreshToken = null;
        _expiresAt = DateTimeOffset.MinValue;
        Uid = null;
        Email = null;
        DisplayName = null;
        PhotoUrl = null;

        try
        {
            if (File.Exists(SessionFile)) File.Delete(SessionFile);
        }
        catch { }
    }

    private async Task SaveSessionAsync()
    {
        try
        {
            string dir = Path.GetDirectoryName(SessionFile)!;
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);

            var session = new StoredSession
            {
                IdToken = _idToken,
                RefreshToken = _refreshToken,
                ExpiresAt = _expiresAt,
                Uid = Uid,
                Email = Email,
                DisplayName = DisplayName,
                PhotoUrl = PhotoUrl
            };

            string json = JsonSerializer.Serialize(session);
            byte[] rawBytes = Encoding.UTF8.GetBytes(json);
            byte[] protectedBytes = ProtectedData.Protect(rawBytes, null, DataProtectionScope.CurrentUser);
            await File.WriteAllBytesAsync(SessionFile, protectedBytes);
        }
        catch { }
    }

    private static FirebaseAuthResult ParseFirebaseError(string responseBody)
    {
        string message = "İşlem gerçekleştirilemedi.";
        try
        {
            using var doc = JsonDocument.Parse(responseBody);
            if (doc.RootElement.TryGetProperty("error", out var err) && err.TryGetProperty("message", out var msg))
            {
                string rawMsg = msg.GetString() ?? "";
                message = rawMsg switch
                {
                    "EMAIL_EXISTS" => "Bu e-posta adresi ile zaten kayıtlı bir hesap var.",
                    "OPERATION_NOT_ALLOWED" => "E-posta/şifre ile giriş Firebase üzerinde etkinleştirilmemiş.",
                    "TOO_MANY_ATTEMPTS_TRY_LATER" => "Çok fazla başarısız deneme yapıldı. Lütfen daha sonra tekrar deneyin.",
                    "EMAIL_NOT_FOUND" => "Bu e-posta adresine ait bir hesap bulunamadı.",
                    "INVALID_PASSWORD" => "Hatalı şifre girdiniz.",
                    "USER_DISABLED" => "Bu kullanıcı hesabı devre dışı bırakılmış.",
                    "WEAK_PASSWORD : Password should be at least 6 characters" => "Şifreniz en az 6 karakter olmalıdır.",
                    _ => $"Hata: {rawMsg}"
                };
            }
        }
        catch { }

        return new FirebaseAuthResult { Success = false, ErrorMessage = message };
    }

    private sealed class StoredSession
    {
        public string? IdToken { get; set; }
        public string? RefreshToken { get; set; }
        public DateTimeOffset ExpiresAt { get; set; }
        public string? Uid { get; set; }
        public string? Email { get; set; }
        public string? DisplayName { get; set; }
        public string? PhotoUrl { get; set; }
    }
}
