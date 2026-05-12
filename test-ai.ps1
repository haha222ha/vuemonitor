$body = '{"email":"test@xhs365.cn","password":"Test123456"}'
$resp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $body
$token = $resp.access_token
$headers = @{ Authorization = "Bearer $token" }
$analyzeBody = '{"product_id":"1b513399-de93-485a-b6cb-6e96937938a8","analysis_type":"basic_analysis","provider":"deepseek"}'
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ai/analyze" -Method POST -ContentType "application/json" -Headers $headers -Body $analyzeBody -TimeoutSec 60
    $result | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $reader.ReadToEnd()
}
