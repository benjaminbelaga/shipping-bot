"""
Discord Bot Main Application
Handles Discord connection, commands, and event loop
"""

import discord
from discord.ext import commands
from typing import Optional
import logging

from src.engine.engine import PricingEngine
from .config import config
from .formatter import PricingFormatter


# Setup logging
logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PricingBot(commands.Bot):
    """Discord bot for shipping price comparisons"""

    def __init__(self):
        # Discord intents (what events the bot can receive)
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.guilds = True

        # Initialize bot with slash command tree
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=None  # We'll use custom /help command
        )

        # Initialize pricing engine
        logger.info("📦 Loading pricing engine...")
        self.pricing_engine = PricingEngine()
        logger.info("✅ Pricing engine loaded")

        # Formatter for Discord embeds
        self.formatter = PricingFormatter()

        # Dev guild for testing (optional)
        self.dev_guild = discord.Object(id=config.dev_guild_id) if config.dev_guild_id else None

    async def setup_hook(self):
        """
        Setup hook called before bot connects to Discord
        Used to register slash commands
        """
        logger.info("🔧 Setting up slash commands...")

        # Import and register commands
        from . import commands as cmd_module
        cmd_module.setup_commands(self)

        # Sync commands to Discord
        if self.dev_guild:
            # Sync to dev guild only (faster, for testing)
            logger.info(f"📝 Syncing commands to dev guild {config.dev_guild_id}...")
            self.tree.copy_global_to(guild=self.dev_guild)
            await self.tree.sync(guild=self.dev_guild)
            logger.info("✅ Commands synced to dev guild")
        else:
            # Sync globally (slower, up to 1 hour propagation)
            logger.info("📝 Syncing commands globally...")
            await self.tree.sync()
            logger.info("✅ Commands synced globally")

    async def on_ready(self):
        """Event triggered when bot successfully connects to Discord"""
        logger.info("=" * 50)
        logger.info(f"✅ Bot connected as {self.user}")
        logger.info(f"📊 Servers: {len(self.guilds)}")
        logger.info(f"👥 Users: {sum(g.member_count for g in self.guilds)}")
        logger.info(f"🚚 Carriers: 4 (La Poste, Spring, FedEx, UPS)")
        logger.info(f"📦 Services: 6")
        logger.info("=" * 50)

        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="shipping prices 📦 | /price"
        )
        await self.change_presence(activity=activity)

    async def on_command_error(self, ctx, error):
        """Global error handler for traditional commands"""
        logger.error(f"Command error: {error}")
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        await ctx.send(f"❌ Error: {error}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Global error handler for slash commands"""
        logger.error(f"App command error: {error}")

        if isinstance(error, discord.app_commands.CommandInvokeError):
            error_message = str(error.original) if hasattr(error, 'original') else str(error)
        else:
            error_message = str(error)

        embed = self.formatter.create_error_embed(error_message)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


def run_bot():
    """
    Main entry point to run the Discord bot

    Usage:
        python -m src.bot.bot
    """
    # Validate configuration
    if not config.validate():
        logger.error("❌ Bot configuration invalid. Exiting.")
        return

    # Create and run bot
    logger.info("🚀 Starting Discord bot...")
    bot = PricingBot()

    try:
        bot.run(config.token)
    except discord.LoginFailure:
        logger.error("❌ Invalid bot token. Check DISCORD_BOT_TOKEN environment variable.")
    except KeyboardInterrupt:
        logger.info("⏹️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    run_bot()
