"""
Discord Message Formatter
Formats pricing engine results as Discord embeds
"""

from typing import List
import discord
from src.engine.engine import PriceOffer
from .config import config


class PricingFormatter:
    """Formats pricing results for Discord"""

    @staticmethod
    def create_offers_embed(
        offers: List[PriceOffer],
        weight_kg: float,
        destination: str,
        country_name: str
    ) -> discord.Embed:
        """
        Create Discord embed for pricing offers

        Args:
            offers: List of price offers from engine
            weight_kg: Weight in kg
            destination: Destination query string
            country_name: Resolved country name

        Returns:
            Discord embed with formatted offers
        """

        if not offers:
            embed = discord.Embed(
                title="❌ No Offers Found",
                description=f"No carriers available for **{weight_kg}kg** to **{country_name}** ({destination})",
                color=discord.Color.red()
            )
            return embed

        # Check if destination is USA for Trump tariff warning
        is_usa = "US" in country_name.upper() or "ÉTATS-UNIS" in country_name.upper() or "USA" in country_name.upper()
        has_suspended = any(offer.is_suspended for offer in offers)

        # Create embed with results
        embed = discord.Embed(
            title=f"📦 Shipping Quotes: {weight_kg}kg → {country_name}",
            description=f"Found **{len(offers)}** offer(s) - Sorted by price (cheapest first)",
            color=config.embed_color
        )

        # Add Trump tariff warning if USA destination with suspended services
        if is_usa and has_suspended:
            embed.add_field(
                name="⚠️ Important Notice - USA Tariffs",
                value=(
                    "**Some UPS services are currently suspended for USA destinations** due to the trade policy changes "
                    "implemented under the Trump administration's tariff regulations. These restrictions affect certain "
                    "shipment categories and customs procedures.\n\n"
                    "**Available alternatives:** We recommend using FedEx, La Poste, or Spring services for USA shipments, "
                    "which remain fully operational and often provide competitive rates.\n\n"
                    "❗ Suspended services are marked with ⛔ below."
                ),
                inline=False
            )

        # Add each offer as a field (use inline=True for 2-column layout)
        for i, offer in enumerate(offers[:config.max_offers], 1):
            # Medal emojis for top 3
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")

            # Add suspension emoji if service is suspended
            if offer.is_suspended:
                medal = "⛔"

            # Format price components with better alignment
            freight_str = f"{float(offer.freight):.2f}"
            surcharges_str = f"{float(offer.surcharges):+.2f}" if offer.surcharges != 0 else ""
            total_str = f"**{float(offer.total):.2f} {offer.currency}**"

            # Build field value with cleaner formatting
            value_parts = [
                f"💰 **Total:** {total_str}",
                f"📄 Freight: `{freight_str} {offer.currency}`",
            ]

            if surcharges_str:
                emoji = "💸" if offer.surcharges < 0 else "➕"
                value_parts.append(f"{emoji} Surcharges: `{surcharges_str} {offer.currency}`")

            value_parts.append(f"🏷️ Service: `{offer.service_code}`")

            # Add warning if suspended
            if offer.is_suspended and offer.warning:
                value_parts.append(f"⚠️ *{offer.warning}*")

            field_name = f"{medal} {offer.carrier_name}"
            field_value = "\n".join(value_parts)

            # Use inline=True for compact 2-column layout (max 2 per row on desktop)
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=True  # Changed from False to enable column layout
            )

        # Add footer with metadata
        embed.set_footer(
            text=f"Query: {destination} | Weight: {weight_kg}kg | Pricing Engine v0.4.0 (with UPS API)"
        )

        return embed

    @staticmethod
    def create_error_embed(error_message: str) -> discord.Embed:
        """Create error embed"""
        embed = discord.Embed(
            title="❌ Error",
            description=error_message,
            color=discord.Color.red()
        )
        return embed

    @staticmethod
    def create_carriers_embed(carriers_info: List[dict]) -> discord.Embed:
        """
        Create embed listing available carriers

        Args:
            carriers_info: List of dicts with carrier info
                           [{"code": "FEDEX", "name": "FedEx", "services": 1}, ...]

        Returns:
            Discord embed with carriers list
        """
        embed = discord.Embed(
            title="🚚 Available Carriers",
            description=f"Total: **{len(carriers_info)}** carriers",
            color=config.embed_color
        )

        for carrier in carriers_info:
            services_text = f"{carrier['services']} service(s)"
            embed.add_field(
                name=f"**{carrier['name']}** (`{carrier['code']}`)",
                value=services_text,
                inline=True
            )

        embed.set_footer(text="Use /price command to get quotes from these carriers")

        return embed

    @staticmethod
    def create_help_embed() -> discord.Embed:
        """Create help embed"""
        embed = discord.Embed(
            title="📘 Pricing Bot Help",
            description="Compare shipping prices from multiple carriers instantly!",
            color=config.embed_color
        )

        embed.add_field(
            name="/price <weight> <destination> [carriers]",
            value=(
                "Get shipping quotes for a destination\n"
                "**Examples:**\n"
                "• `/price 2kg Japan`\n"
                "• `/price 5kg Germany carriers:fedex,spring`\n"
                "• `/price 10 australia` (kg assumed if no unit)"
            ),
            inline=False
        )

        embed.add_field(
            name="/carriers",
            value="List all available shipping carriers",
            inline=False
        )

        embed.add_field(
            name="/help",
            value="Show this help message",
            inline=False
        )

        embed.add_field(
            name="📌 Supported Countries",
            value=(
                "**200+ countries** supported including:\n"
                "🇺🇸 USA, 🇬🇧 UK, 🇩🇪 Germany, 🇫🇷 France, 🇯🇵 Japan, 🇦🇺 Australia\n"
                "Use country names (Japan, Allemagne) or ISO codes (JP, DE)"
            ),
            inline=False
        )

        embed.set_footer(text="Powered by Unified Pricing Engine v0.3.0")

        return embed
