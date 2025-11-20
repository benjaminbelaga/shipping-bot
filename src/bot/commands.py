"""
Discord Slash Commands
Implements /price, /carriers, and /help commands
"""

import discord
from discord import app_commands
import re
import logging
from typing import Optional, TYPE_CHECKING
from decimal import Decimal

if TYPE_CHECKING:
    from .bot import PricingBot

logger = logging.getLogger(__name__)


def setup_commands(bot: 'PricingBot'):
    """
    Register all slash commands to the bot

    Args:
        bot: PricingBot instance
    """

    @bot.tree.command(
        name="price",
        description="Get shipping quotes for a destination"
    )
    @app_commands.describe(
        weight="Weight (e.g., '2kg', '5', '10.5kg')",
        destination="Destination country (e.g., 'Japan', 'DE', 'Allemagne')",
        carriers="(Optional) Filter carriers (e.g., 'fedex,spring')"
    )
    async def price(
        interaction: discord.Interaction,
        weight: str,
        destination: str,
        carriers: Optional[str] = None
    ):
        """
        /price command handler

        Examples:
            /price 2kg Japan
            /price 5 Germany carriers:fedex
            /price 10.5kg US
        """
        # Defer response (gives us 15 minutes instead of 3 seconds)
        await interaction.response.defer()

        try:
            # Parse weight
            weight_kg = parse_weight(weight)
            if weight_kg is None:
                await interaction.followup.send(
                    embed=bot.formatter.create_error_embed(
                        f"❌ Invalid weight format: `{weight}`\n"
                        f"Use formats like: `2kg`, `5`, `10.5kg`"
                    )
                )
                return

            # Validate weight range
            if weight_kg <= 0:
                await interaction.followup.send(
                    embed=bot.formatter.create_error_embed("❌ Weight must be positive")
                )
                return

            if weight_kg > 70:
                await interaction.followup.send(
                    embed=bot.formatter.create_error_embed(
                        "❌ Weight exceeds maximum (70kg)\n"
                        "Most carriers limit parcels to 70kg."
                    )
                )
                return

            # Parse carrier filter (optional)
            carrier_filter = None
            if carriers:
                carrier_filter = [c.strip().upper() for c in carriers.split(',')]

            # Query pricing engine (CSV data - UPS WWE, FedEx, Spring, La Poste)
            offers = bot.pricing_engine.price(destination, weight_kg, debug=False)

            # Resolve country name for display
            country_iso2 = bot.pricing_engine.resolver.resolve(destination)
            country_name = destination
            if country_iso2:
                resolved_name = bot.pricing_engine.resolver.get_name(country_iso2)
                if resolved_name:
                    country_name = f"{resolved_name} ({country_iso2})"

            # Add UPS API real-time rates (if available)
            try:
                from src.integrations.ups_api import UPSAPIClient
                from src.engine.engine import PriceOffer

                ups_client = UPSAPIClient()
                ups_api_rates = ups_client.get_shipping_rates(
                    weight_kg=weight_kg,
                    destination_country=country_iso2
                )

                # Convert UPS API results to PriceOffer format
                for rate in ups_api_rates:
                    # Determine carrier name based on API type
                    carrier_name = "UPS (Real-time)" if rate['api_type'] == 'WWE' else "UPS Standard"

                    ups_offer = PriceOffer(
                        carrier_code="UPS_API",
                        carrier_name=carrier_name,
                        service_code=rate['service_code'],
                        service_label=rate['service_name'],
                        freight=rate['price'],
                        surcharges=Decimal('0'),  # API returns total price
                        total=rate['price'],
                        currency=rate['currency'],
                        scope_code=f"UPS_API_{rate['api_type']}",
                        band_details=f"API Quote - {rate.get('delivery_days', 'N/A')} days"
                    )
                    offers.append(ups_offer)

                logger.info(f"✅ Added {len(ups_api_rates)} UPS API real-time rates")
            except Exception as e:
                logger.warning(f"⚠️ UPS API unavailable: {e}")
                # Continue without API rates

            # Sort all offers by price
            offers.sort(key=lambda o: float(o.total))

            # Rename UPS WWE carriers to distinguish from UPS API
            for offer in offers:
                if offer.carrier_code == "UPS" and not offer.carrier_code.startswith("UPS_API"):
                    offer.carrier_name = "UPS WWE"

            # Filter by carriers if specified
            if carrier_filter:
                offers = [
                    o for o in offers
                    if o.carrier_code.upper() in carrier_filter or
                       any(cf in o.carrier_name.upper() for cf in carrier_filter)
                ]

            # Create and send embed
            embed = bot.formatter.create_offers_embed(
                offers,
                weight_kg,
                destination,
                country_name
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=bot.formatter.create_error_embed(f"❌ Error: {str(e)}")
            )
            raise  # Re-raise for logging

    @bot.tree.command(
        name="carriers",
        description="List all available shipping carriers"
    )
    async def carriers(interaction: discord.Interaction):
        """
        /carriers command handler

        Shows all available carriers with service counts
        """
        # Defer response
        await interaction.response.defer()

        try:
            # Get carrier info from pricing engine
            carriers_info = []
            for carrier_id, carrier in bot.pricing_engine.loader.carriers.items():
                # Count services for this carrier
                services_count = sum(
                    1 for s in bot.pricing_engine.loader.services.values()
                    if s.carrier_id == carrier_id
                )

                carriers_info.append({
                    "code": carrier.code,
                    "name": carrier.name,
                    "services": services_count
                })

            # Sort by name
            carriers_info.sort(key=lambda c: c['name'])

            # Create and send embed
            embed = bot.formatter.create_carriers_embed(carriers_info)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=bot.formatter.create_error_embed(f"❌ Error: {str(e)}")
            )
            raise

    @bot.tree.command(
        name="help",
        description="Show bot usage guide"
    )
    async def help_command(interaction: discord.Interaction):
        """
        /help command handler

        Shows bot documentation and examples
        """
        embed = bot.formatter.create_help_embed()
        await interaction.response.send_message(embed=embed)


def parse_weight(weight_str: str) -> Optional[float]:
    """
    Parse weight string to float in kg

    Supports:
        - "2kg" → 2.0
        - "2" → 2.0
        - "2.5kg" → 2.5
        - "10.5" → 10.5

    Args:
        weight_str: Weight string from user

    Returns:
        Weight in kg, or None if invalid
    """
    # Remove spaces
    weight_str = weight_str.strip().lower()

    # Extract number (with optional 'kg' suffix)
    match = re.match(r'^(\d+\.?\d*)\s*(kg)?$', weight_str)

    if not match:
        return None

    try:
        weight_kg = float(match.group(1))
        return weight_kg
    except ValueError:
        return None
