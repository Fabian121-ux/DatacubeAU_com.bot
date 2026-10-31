$body = Get-Content -Raw "bot_core/examples/dm_webhook.json"
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8080/webhooks/waha" `
  -ContentType "application/json" `
  -Body $body
