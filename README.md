# Before Running

Add a .env file for your telegram bot token

```bash
cp .template.env .env
```

paste TOKEN in `TELEGRAM_BOT_TOKEN`

## docker compose version<3.8

```bash
docker build -t wol-telegram-bot-service .
```

```bash
docker run --detach --name wol \
    --network host \
    --restart unless-stopped \
    --env-file .env \
    wol-telegram-bot-service

```

## docker compose version>3.8

```bash
docker compose build
docker compose up -d
```
