"""
Discord Bot Configuration
Loads bot token and settings from environment variables
"""

import os
from typing import Optional


class BotConfig:
    """Configuration for Discord bot"""

    def __init__(self):
        # Discord bot token (from environment or .env file)
        self.token: Optional[str] = os.getenv("DISCORD_BOT_TOKEN")

        # Bot command prefix (for legacy commands, slash commands don't need this)
        self.command_prefix: str = "!"

        # Guild ID for development (restricts commands to test server)
        # Set to None for production (global commands)
        self.dev_guild_id: Optional[int] = self._parse_int(os.getenv("DISCORD_DEV_GUILD_ID"))

        # Embed color (hex color for Discord embeds)
        self.embed_color: int = 0x3498db  # Blue

        # Maximum offers to display per query
        self.max_offers: int = 10

        # Enable debug logging
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        """Parse string to int, return None if invalid"""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def validate(self) -> bool:
        """Validate that required config values are set"""
        if not self.token:
            print("❌ ERROR: DISCORD_BOT_TOKEN environment variable not set")
            print("   Set it with: export DISCORD_BOT_TOKEN='your-token-here'")
            return False
        return True


# Global config instance
config = BotConfig()
