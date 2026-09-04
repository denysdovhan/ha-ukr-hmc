[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

<br>

![Ukrainian Hydrometeorological Center Logo](./custom_components/ukr_hmc/brand/logo@2x.png#gh-light-mode-only)
![Ukrainian Hydrometeorological Center Logo](./custom_components/ukr_hmc/brand/dark_logo@2x.png#gh-dark-mode-only)

<br>

# 🌦️ Ukrainian Hydrometeorological Center for Home Assistant

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

[**English**](./readme.md) | [Українською](./readme.uk.md)

> [!NOTE]
> An integration for weather, radiation, and hydrology data from the [Ukrainian Hydrometeorological Center][ukr-hmc].

> [!IMPORTANT]
> This is an independent community project and is not affiliated with the Ukrainian Hydrometeorological Center.

This integration brings data from [meteo.gov.ua][ukr-hmc] into [Home Assistant][home-assistant] as native weather and sensor entities.

## Sponsorship

Your generosity will help me maintain and develop more projects like this one.

- 💖 [Sponsor on GitHub][gh-sponsors-url]
- ☕️ [Buy Me A Coffee][buymeacoffee-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Installation

The quickest way to install this integration is via [HACS][hacs-url] by selecting the button below:

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

This integration is configured through the Home Assistant UI. Select the button below to add it:

[![Add Ukrainian Hydrometeorological Center][install-image]][install-url]

<details>
  <summary>If the button doesn't work, add the integration manually</summary>

1. Open **Settings** → **Devices & services**.
2. Select **Add integration** and search for **Ukrainian Hydrometeorological Center**.
3. Follow the setup steps.

</details>

## What it provides

![Creating entities](./media/create-entries.png)

This integration allows creating these entities:

| Source                       | Current data                                                                                   | Forecasts           |
| ---------------------------- | ---------------------------------------------------------------------------------------------- | ------------------- |
| Weather station              | Physical station measurements, including temperature, humidity, pressure, wind, and conditions | Daily and day/night |
| Weather location             | Forecast conditions for the selected map point; physical station measurements are not used     | Hourly and daily    |
| Radiation monitoring station | Direct µR/h and nSv/h readings with observation time                                           | —                   |
| Hydrology post               | Daily water measurements and the provider's hydrological situation                             | —                   |

The integration also exposes five provider-global attention flags as binary sensors. They indicate attention to a weather, hydrology, snow, radiation, or fire product. In addition, every physical weather station gets a regional meteorological warning binary sensor with the oblast, danger level, warning text, phenomenon code, and validity period published by UkrHMC.

### Weather

You can monitor weather conditions either by using a physical weather station or by selecting a location on the map. The integration provides both current conditions and forecasts.

The difference is in forecasts:

- **Weather stations** provide daily and day/night forecasts. Data is updated _every 3 hours_.
- **Weather locations** provide hourly and daily forecasts. Data is updated _every hour_.

Weather locations expose current precipitation. Physical stations also expose sunrise, sunset, provider diagnostic codes, and a compact detailed-forecast sensor. Its attributes preserve the published day/night temperature ranges, precipitation text, cloudiness, and wind-speed ranges.

#### Weather entities and sensors

| Entity                                       | Weather station | Weather location | Notes                                                                                                                                                |
| -------------------------------------------- | :-------------: | :--------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Weather                                      |       ✅        |        ✅        | Station: measured current conditions with daily and day/night forecasts. Location: modelled current-hour conditions with hourly and daily forecasts. |
| Condition                                    |       ✅        |        ✅        | Canonical Home Assistant condition.                                                                                                                  |
| Weather text                                 |       ✅        |        ✅        | Description published by UkrHMC.                                                                                                                     |
| Temperature                                  |       ✅        |        ✅        | Current station measurement or current-hour point forecast.                                                                                          |
| Humidity                                     |       ✅        |        ✅        | Relative humidity.                                                                                                                                   |
| Pressure                                     |       ✅        |        —         | Physical station measurement in mmHg.                                                                                                                |
| Wind speed                                   |       ✅        |        ✅        | Current speed in m/s.                                                                                                                                |
| Wind direction                               |       ✅        |        ✅        | Direction in degrees; locations also expose the provider compass value.                                                                              |
| Current precipitation                        |        —        |        ✅        | Direct point-forecast precipitation in mm.                                                                                                           |
| Precipitation next 1/3/6/12/24 hours         |        —        |        ✅        | Sum of complete hourly precipitation records in each horizon.                                                                                        |
| Next precipitation                           |        —        |        ✅        | Timestamp of the first upcoming hour with precipitation above 0 mm.                                                                                  |
| Minimum / maximum today and tomorrow         |        —        |        ✅        | Direct low/night and high/day values used by the provider's daily forecast.                                                                          |
| Maximum wind gust next 24 hours and its time |        —        |        ✅        | Largest published hourly gust and its forecast timestamp.                                                                                            |
| Data time                                    |       ✅        |        ✅        | Provider observation or forecast timestamp.                                                                                                          |
| Sunrise / sunset                             |       ✅        |        —         | Timestamp sensors.                                                                                                                                   |
| Phenomenon / indicator code                  |       ✅        |        —         | Provider service codes; disabled by default.                                                                                                         |
| Detailed forecast                            |       ✅        |        —         | Diagnostic attributes with day/night temperature ranges, precipitation text, cloudiness, wind ranges, sunrise, sunset, and provider code.            |
| Regional weather warning                     |       ✅        |        —         | Problem sensor active only during a current warning, with text, codes, timing, and active/future counts in attributes.                               |
| Regional weather warning level               |       ✅        |        —         | Enum sensor with `none`, `yellow`, `orange`, or `red`, suitable for dashboards and automations.                                                      |

Hourly forecasts are available only for a configured **weather location**. They come directly from the UkrHMC `dataDetailed` point-forecast product and may include temperature, condition, precipitation, pressure, humidity, dew point, wind speed, gust, and direction when the provider publishes them. Home Assistant exposes forecasts through the weather entity forecast service and forecast-capable dashboard cards, not as one sensor per hour.

| Weather station                                 | Weather location                                  |
| ----------------------------------------------- | ------------------------------------------------- |
| ![Weather Station](./media/weather-station.png) | ![Weather Location](./media/weather-location.png) |

### Radiation

You can monitor radiation levels by using a physical radiation monitoring station.

<img src="./media/radiation.png" alt="Radiation Monitoring Station" width="500">

### Hydrology

You can monitor hydrological in Ukrainian rivers by using a physical hydrology post: water level, water temperature, conditions, etc.

<img src="./media/hydrology.png" alt="Hydrology Post" width="500">

### Service diagnostics and global attention flags

The shared UkrHMC service device exposes:

| Entity                                                         | Meaning                                                                                                                   |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| API available                                                  | Connectivity binary sensor. It is on when the latest scheduled provider update succeeded and off after an update failure. |
| Last successful update                                         | Timestamp of the latest complete provider snapshot retained across temporary failures.                                    |
| Data stale                                                     | Problem sensor activated when the last successful complete update is older than 45 minutes.                               |
| Consecutive update failures                                    | Number of failed provider updates since the latest successful refresh.                                                    |
| Global weather, hydrology, snow, radiation, and fire attention | Direct provider-global flags. They are not regional warnings and contain no severity, text, or validity period.           |

The regional weather warning sensor is attached to each configured physical weather station. Its state is on while at least one warning for that station's oblast is active. Attributes include `region`, active `level`, `level_name`, `active_count`, `future_count`, `next_start`, `next_end`, the provider update time, and a `warnings` list with description, phenomenon code, level, raw period, start, end, and status. The companion enum sensor exposes the highest active level as `none`, `yellow`, `orange`, or `red`. Exact map locations do not receive these entities because the point-forecast response does not provide a reliable oblast identifier.

All data is polled through one shared coordinator every 15 minutes. The diagnostic update time is the moment Home Assistant successfully received the complete snapshot, not the observation time published by an individual station. Forecast summary sensors require complete provider hours for their selected horizon; they become unknown instead of treating missing precipitation as zero.

## Removal

1. Open **Settings** → **Devices & services**.
2. Select **Ukrainian Hydrometeorological Center**.
3. Open the **⋮** menu and select **Delete**.
4. Remove the integration from HACS and restart Home Assistant if you no longer want the custom component installed.

## Development

Want to contribute to the project?

Thank you! Read the [contributing guide](./contributing.md) for more information.

## Other integrations

- 💥 [Aerial Danger](https://github.com/denysdovhan/ha-aerial-danger) — detects aerial-threat messages for selected Ukrainian regions and localities.
- ☁️ [Check Weather](https://github.com/denysdovhan/ha-check-weather) — creates a binary sensor based on forecast conditions for the next few hours.
- 💨 [LUN Misto Air](https://github.com/denysdovhan/ha-lun-misto-air) — provides air quality and environmental data from LUN Misto monitoring stations.
- ⚡️ [Yasno Outages](https://github.com/denysdovhan/ha-yasno-outages) — provides planned electricity outage schedules, sensors, and calendars from Yasno.

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
