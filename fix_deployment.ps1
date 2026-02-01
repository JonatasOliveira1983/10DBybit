# Fix Cloud Run Startup Probe - V5.2.4.8
# Run this in your terminal to fix the crash loop

Write-Host "Applying V5.2.4.8 Infrastructure Fix..." -ForegroundColor Cyan

# Update Cloud Run Service with extended startup probe
gcloud run services update bybit10d `
  --region=europe-west1 `
  --startup-probe-initial-delay-seconds=40 `
  --startup-probe-period-seconds=10 `
  --startup-probe-failure-threshold=3 `
  --startup-probe-timeout-seconds=10 `
  --project=projeto-teste-firestore-3b00e

Write-Host "Fix Applied! Please wait for the new revision to deploy." -ForegroundColor Green
