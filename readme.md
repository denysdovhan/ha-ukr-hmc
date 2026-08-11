[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

![Ukrainian Hydrometeorological Center Logo](./custom_components/ukr_hmc/brand/logo@2x.png#gh-light-mode-only)
![Ukrainian Hydrometeorological Center Logo](./custom_components/ukr_hmc/brand/dark_logo@2x.png#gh-dark-mode-only)

# 🌦️ Ukrainian Hydrometeorological Center for Home Assistant

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

[**English**](./readme.md) | [Українською](./readme.uk.md)

> [!NOTE]
> An integration for weather, radiation, and hydrology data from the
> [Ukrainian Hydrometeorological Center][ukr-hmc].

> [!IMPORTANT]
> This is an independent community project and is not affiliated with the
> Ukrainian Hydrometeorological Center. Data may differ from the official
> website. Always follow official warnings and guidance.

This integration brings data from [meteo.gov.ua][ukr-hmc] into
[Home Assistant][home-assistant] as native weather and sensor entities.

## What it provides

- **Weather stations** — measured conditions with daily, day, and night
  forecasts published for a physical station.
- **Weather locations** — current-hour conditions plus hourly and daily
  forecasts for an exact point on the map.
- **Radiation monitoring stations** — exposure dose rate, dose rate, and
  observation time as published by the provider.
- **Hydrology posts** — water level, water-level altitude, daily change, water
  temperature, hydrological situation, and observation time.
- **Multiple sources** — add several weather, radiation, and hydrology sources
  under one integration entry.

Configured data is refreshed every 15 minutes. The integration requests only
the provider products needed by your selected sources.

## Sponsorship

Your generosity will help me maintain and develop more projects like this one.

- 💖 [Sponsor on GitHub][gh-sponsors-url]
- ☕️ [Buy Me A Coffee][buymeacoffee-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Installation

The quickest way to install this integration is via [HACS][hacs-url] by
selecting the button below:

[![Add to HACS via My Home Assistant][hacs-install-image]][hacs-install-url]

<details>
  <summary>If the button doesn't work, add the repository manually</summary>

1. Open **HACS** → **Integrations** → **⋮** → **Custom repositories**.
2. Select **Add**.
3. Paste `https://github.com/denysdovhan/ha-ukr-hmc` as the repository URL.
4. Choose **Integration** as the category.
5. Find and install **Ukrainian Hydrometeorological Center**.

</details>

## Usage

This integration is configured through the Home Assistant UI. Select the button
below to add it:

[![Add Ukrainian Hydrometeorological Center][install-image]][install-url]

<details>
  <summary>If the button doesn't work, add the integration manually</summary>

1. Open **Settings** → **Devices & services**.
2. Select **Add integration** and search for **Ukrainian Hydrometeorological
   Center**.
3. Follow the setup steps.

</details>

Choose the first data source during setup. To add more sources later, open the
integration page and select the weather station, weather location, radiation
monitoring station, or hydrology post you need.

| Source                       | Current data                                                                                   | Forecasts           |
| ---------------------------- | ---------------------------------------------------------------------------------------------- | ------------------- |
| Weather station              | Physical station measurements, including temperature, humidity, pressure, wind, and conditions | Daily and day/night |
| Weather location             | Forecast conditions for the selected map point; physical station measurements are not used     | Hourly and daily    |
| Radiation monitoring station | Direct µR/h and nSv/h readings with observation time                                           | —                   |
| Hydrology post               | Daily water measurements and the provider's hydrological situation                             | —                   |

For weather locations, the current entity uses the provider's record for the
current hour. The daily forecast follows the meteo.gov.ua presentation: 03:00
supplies the low temperature, while 15:00 supplies the high temperature and
condition. Incomplete days are omitted.

Radiation readings and hydrological situations are shown as published. The
integration does not classify safety, derive warnings, or replace official
guidance.

The integration does not provide custom actions, automation triggers, or
automation conditions. Use its native entities in standard Home Assistant
automations.

## Removal

1. Open **Settings** → **Devices & services**.
2. Select **Ukrainian Hydrometeorological Center**.
3. Open the **⋮** menu and select **Delete**.
4. Remove the integration from HACS and restart Home Assistant if you no longer
   want the custom component installed.

## Development

Want to contribute to the project?

Thank you! Read the [contributing guide](./contributing.md) for more information.

## License

MIT © [Denys Dovhan][denysdovhan]

<!-- Badges -->

[gh-release-url]: https://github.com/denysdovhan/ha-ukr-hmc/releases/latest
[gh-release-image]: https://img.shields.io/github/v/release/denysdovhan/ha-ukr-hmc?style=flat-square
[gh-downloads-url]: https://github.com/denysdovhan/ha-ukr-hmc/releases
[gh-downloads-image]: https://img.shields.io/github/downloads/denysdovhan/ha-ukr-hmc/total?style=flat-square
[hacs-url]: https://github.com/hacs/integration
[hacs-image]: https://img.shields.io/badge/hacs-custom-orange.svg?style=flat-square
[gh-sponsors-url]: https://github.com/sponsors/denysdovhan
[gh-sponsors-image]: https://img.shields.io/github/sponsors/denysdovhan?style=flat-square
[buymeacoffee-url]: https://buymeacoffee.com/denysdovhan
[buymeacoffee-image]: https://img.shields.io/badge/support-buymeacoffee-222222.svg?style=flat-square
[twitter-url]: https://x.com/denysdovhan
[twitter-image]: https://img.shields.io/badge/follow-%40denysdovhan-000000.svg?style=flat-square

<!-- References -->

[ukr-hmc]: https://www.meteo.gov.ua/
[home-assistant]: https://www.home-assistant.io/
[denysdovhan]: https://github.com/denysdovhan
[hacs-install-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=denysdovhan&repository=ha-ukr-hmc&category=integration
[hacs-install-image]: https://my.home-assistant.io/badges/hacs_repository.svg
[install-image]: https://my.home-assistant.io/badges/config_flow_start.svg
[install-url]: https://my.home-assistant.io/redirect/config_flow_start/?domain=ukr_hmc
