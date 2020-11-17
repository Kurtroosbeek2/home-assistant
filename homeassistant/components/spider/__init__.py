"""Support for Spider Smart devices."""
import asyncio
import logging

from spiderpy.spiderapi import SpiderApi, UnauthorizedException
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
import homeassistant.helpers.config_validation as cv

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _spider_startup_wrapper(entry):
    """Startup wrapper for spider."""
    api = SpiderApi(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_SCAN_INTERVAL],
    )
    return api


async def async_setup(hass, config):
    """Set up a config entry."""
    hass.data[DOMAIN] = {}
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
            )
        )

    return True


async def async_setup_entry(hass, entry):
    """Set up Spider via config entry."""
    try:
        hass.data[DOMAIN][entry.entry_id] = await hass.async_add_executor_job(
            _spider_startup_wrapper, entry
        )
    except UnauthorizedException:
        _LOGGER.error("Can't connect to the Spider API")
        return False

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass, entry):
    """Unload Spider entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.entry_id)

    return True