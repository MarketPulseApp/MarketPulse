import logging
import os

import discord
import httpx
from discord import app_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
API_URL = os.getenv("MARKETPULSE_API_URL", "http://192.168.1.134:8080")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Logged in as {client.user} (ID: {client.user.id})")


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
            r = await http.get("http://192.168.1.193:9090/api/v1/targets")
            data = r.json()
        targets = data["data"]["activeTargets"]
        lines = ["**Prometheus Targets**"]
        for t in targets:
            icon = "✅" if t["health"] == "up" else "❌"
            lines.append(f"{icon} {t['labels']['job']}: {t['health']}")
        await interaction.followup.send("\n".join(lines))
    except Exception as e:
        await interaction.followup.send(f"❌ Could not reach Prometheus: {e}")


if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN not set")
        exit(1)
    client.run(TOKEN)
