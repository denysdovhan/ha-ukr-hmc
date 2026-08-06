[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

# 🌦️ Ukrainian Hydrometeorological Center for Home Assistant

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![HACS][hacs-image]][hacs-url]

> [!NOTE]
> This custom integration provides weather observations, forecasts, and
> radiation measurements, and daily hydrology observations from the
> [Ukrainian Hydrometeorological Center][ukr-hmc].

> [!IMPORTANT]
> This community project is not affiliated with the Ukrainian
> Hydrometeorological Center. Always follow official warnings and guidance.

The integration creates weather entities and sensors for selected physical
stations or map locations, radiation sensors for monitoring stations, and water
level sensors for hydrology posts.

## Features

- Physical station mode with current observations plus direct daily and
  twice-daily station forecasts.
- Location mode with current conditions from the current forecast
  hour, plus hourly and daily forecasts for the exact point.
- Native station sensors for canonical condition, provider weather text,
  temperature, humidity, pressure, wind speed, wind direction, and data time.
- Native location sensors for canonical condition, provider weather text,
  temperature, humidity, wind speed, compass and numeric wind direction, and data
  time. Location pressure remains available in hourly forecasts, not as a current
  sensor.
- Radiation monitoring with the provider's direct exposure dose rate in µR/h,
  dose rate in nSv/h, and observation time.
- Hydrology monitoring with water level, water level above sea level, daily
  change, water temperature, hydrological situation, and observation time.
- Multiple weather, radiation, and hydrology sources under one integration
  entry.
- One shared coordinator updates provider data every 15 minutes and requests
  only the products needed by configured sources.

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

When adding data, choose one of four types:

- **Physical station** — select a UkrHMC station and receive its current
  observation plus daily and twice-daily station forecasts.
- **Location on map** — place a point on the map and receive current values
  from the current forecast hour, plus hourly and daily forecasts for the exact
  location. Physical-station observations are not used.
- **Radiation monitoring station** — select a UkrHMC station and receive its
  direct exposure dose rate in µR/h, dose rate in nSv/h, and observation time.
  Only stations with current data appear in the selector.
- **Hydrology post** — select a river monitoring post and receive its daily
  water level, water level above sea level, change, temperature, published
  hydrological situation, and observation time. Only posts with current data
  appear in the selector.

Location daily forecasts follow the meteo.gov.ua presentation: the 03:00
forecast supplies the low temperature, while the 15:00 forecast supplies the
high temperature and condition. Days without both published hours are omitted.

Radiation values are displayed as published. The integration does not derive
safe, normal, or dangerous conditions and does not replace official warnings
and guidance.

The hydrological situation sensor exposes the provider's five map classes,
including floodplain flooding and dangerous high or low levels. It does not
derive a flood warning and does not replace official hydrological warnings.

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
