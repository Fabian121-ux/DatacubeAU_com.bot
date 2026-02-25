# Troubleshooting

## Bot not connected
- Open admin QR page and scan a fresh code.
- Check PM2 logs for datacube-bot.

## API auth token errors
- Confirm ADMIN_TOKEN/ADMIN_API_TOKEN is set.
- Reload PM2 with --update-env.

## AI responses failing
- Verify OPENROUTER_API_KEY.
- Check daily budget setting and model names.

## Cache not hitting
- Ensure cache_ttl_days > 0.
- Questions must be similar after normalization.
