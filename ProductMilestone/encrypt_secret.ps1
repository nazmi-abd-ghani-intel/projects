# Encrypt databricks_secret.txt to databricks_secret.txt.enc
$key = Read-Host "Enter 16-char encryption key"  # e.g. MySecretKey12345
if ($key.Length -ne 16) {
    Write-Host "Key must be exactly 16 characters (128-bit)."
    exit 1
}
$plain = Get-Content "databricks_secret.txt" -Raw
$secure = $plain | ConvertTo-SecureString -AsPlainText -Force
$enc = ConvertFrom-SecureString -SecureString $secure -SecureKey ([Text.Encoding]::UTF8.GetBytes($key))
Set-Content "databricks_secret.txt.enc" $enc
Write-Host "Encrypted secret written to databricks_secret.txt.enc"
