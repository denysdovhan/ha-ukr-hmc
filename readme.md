[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

# 🌦️ Ukrainian Hydrometeorological Center for Home Assistant

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![HACS][hacs-image]][hacs-url]

> [!NOTE]
> This custom integration provides weather observations and forecasts from the
> [Ukrainian Hydrometeorological Center][ukr-hmc].

> [!IMPORTANT]
> This community project is not affiliated with the Ukrainian
> Hydrometeorological Center. Always follow official warnings and guidance.

The integration creates a weather entity and sensors for the selected physical
weather station. Choose a station from the list or provide a location to use
the nearest station. Forecasts expose only values supplied by the provider.

## Features

- Native Home Assistant weather entity with daily and twice-daily forecasts.
- Native sensors for condition text, temperature, humidity, pressure, wind
  speed, wind direction, and observation time.
- Multiple physical stations under one integration entry.
- Station selection from the provider list or by nearest map location.
- Shared provider updates every 30 minutes, regardless of station count.

The provider supplies temperature ranges and descriptive precipitation,
cloudiness, and wind-range text that Home Assistant's native forecast schema
cannot represent. These values stay in the internal API model and are not
published as custom attributes or inferred values.

## Installation

Install the integration through [HACS][hacs-url]:

[![Add Ukrainian Hydrometeorological Center to HACS][hacs-install-image]][hacs-install-url]

<details>
  <summary>If the button does not work, add the repository manually</summary>

1. Open **HACS** → **Integrations** → **⋮** → **Custom repositories**.
2. Add `https://github.com/denysdovhan/ha-ukr-hmc` as an **Integration**.
3. Find and install **Ukrainian Hydrometeorological Center**.

</details>

## Configuration

Add the integration through the Home Assistant UI:

[![Add Ukrainian Hydrometeorological Center][install-image]][install-url]

<details>
  <summary>If the button does not work, add the integration manually</summary>

1. Open **Settings** → **Devices & services**.
2. Select **Add integration**.
3. Search for **Ukrainian Hydrometeorological Center** and follow the setup.

</details>

## Removal

1. Open **Settings** → **Devices & services**.
2. Select **Ukrainian Hydrometeorological Center**.
3. Open the **⋮** menu and select **Delete**.
4. Remove the integration from HACS and restart Home Assistant if you no longer
   want the custom component installed.

This integration does not provide custom actions, automation triggers, or
automation conditions.

## Development

See the [contributing guide](./contributing.md) to run Home Assistant locally.

## License

MIT © [Denys Dovhan][denysdovhan]

[gh-release-url]: https://github.com/denysdovhan/ha-ukr-hmc/releases/latest
[gh-release-image]: https://img.shields.io/github/v/release/denysdovhan/ha-ukr-hmc?style=flat-square
[gh-downloads-url]: https://github.com/denysdovhan/ha-ukr-hmc/releases
[gh-downloads-image]: https://img.shields.io/github/downloads/denysdovhan/ha-ukr-hmc/total?style=flat-square
[hacs-url]: https://github.com/hacs/integration
[hacs-image]: https://img.shields.io/badge/hacs-custom-orange.svg?style=flat-square
[hacs-install-image]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-install-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=denysdovhan&repository=ha-ukr-hmc&category=integration
[install-image]: https://my.home-assistant.io/badges/config_flow_start.svg
[install-url]: https://my.home-assistant.io/redirect/config_flow_start/?domain=ukr_hmc
[ukr-hmc]: https://www.meteo.gov.ua/
[denysdovhan]: https://github.com/denysdovhan
