import asyncio
import logging
import os

import discord
import httpx
from aiohttp import web
from discord import app_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
API_URL = os.getenv("MARKETPULSE_API_URL", "http://192.168.1.134:8080")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://192.168.1.193:9090")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def health_check(request):
    """Basic health check endpoint."""
    return web.json_response({"status": "ok", "service": "marketpulse-bot"})


async def metrics(request):
    """Basic Prometheus metrics exposition."""
    return web.Response(
        text="# HELP bot_up Whether the bot is running.\\n# TYPE bot_up gauge\\nbot_up 1\\n"
    )


async def start_http_server():
    """Start the aiohttp server for health and metrics."""
    app = web.Application()
    app.add_routes([web.get("/health", health_check), web.get("/metrics", metrics)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    logger.info("Bot HTTP server running on port 8081")


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
    asyncio.create_task(start_http_server())

    # Start live paper trading engine
    from logic.paper_trader import PaperTrader

    paper_trader = PaperTrader()
    asyncio.create_task(paper_trader.start())


@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency: {round(client.latency * 1000)}ms")


@tree.command(name="health", description="Check MarketPulse service health")
async def health(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f"{API_URL}/health/full")
            data = r.json()
        status = data.get("status", "unknown")
        checks = data.get("checks", {})
        lines = [f"**MarketPulse Health: {status.upper()}**"]
        for svc, state in checks.items():
            icon = "✅" if state in ("ok", "green") else "❌"
            lines.append(f"{icon} {svc}: {state}")
        await interaction.followup.send("\n".join(lines))
    except Exception as e:
        await interaction.followup.send(f"❌ Could not reach API: {e}")


@tree.command(name="status", description="Show Prometheus target status")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f"{PROMETHEUS_URL}/api/v1/targets")
            data = r.json()
        targets = data["data"]["activeTargets"]
        lines = ["**Prometheus Targets**"]
        for t in targets:
            icon = "✅" if t["health"] == "up" else "❌"
            lines.append(f"{icon} {t['labels']['job']}: {t['health']}")
        await interaction.followup.send("\n".join(lines))
    except Exception as e:
        await interaction.followup.send(f"❌ Could not reach Prometheus: {e}")


@tree.command(name="access", description="Generate a 1-time homelab access token")
async def access(interaction: discord.Interaction):
    # allowed_id = os.getenv("ALLOWED_DISCORD_ID")
    # if not allowed_id or str(interaction.user.id) != allowed_id:
    #     await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
    #     return

    cf_account = os.getenv("CF_ACCOUNT_ID")
    cf_kv = os.getenv("CF_KV_NAMESPACE_ID")
    cf_token = os.getenv("CF_API_TOKEN")

    if not all([cf_account, cf_kv, cf_token]):
        await interaction.response.send_message(
            "❌ Cloudflare integration not configured.", ephemeral=True
        )
        return

    import uuid

    token = str(uuid.uuid4())

    # Store token in Cloudflare KV (valid for 5 minutes = 300 seconds)
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/storage/kv/namespaces/{cf_kv}/values/{token}"
    headers = {"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=5) as http:
            res = await http.put(
                url, headers=headers, json={"status": "active"}, params={"expiration_ttl": 300}
            )
            res.raise_for_status()

        access_url = (
            f"https://{os.getenv('CF_ACCESS_DOMAIN', 'secure.yourdomain.com')}/?token={token}"
        )
        await interaction.response.send_message(
            f"✅ Here is your 1-time access link (expires in 5 mins):\n{access_url}", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to generate token: {e}", ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN not set")
        exit(1)
    client.run(TOKEN)
