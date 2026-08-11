[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

![Логотип Українського гідрометеорологічного центру](./custom_components/ukr_hmc/brand/logo@2x.png#gh-light-mode-only)
![Логотип Українського гідрометеорологічного центру](./custom_components/ukr_hmc/brand/dark_logo@2x.png#gh-dark-mode-only)

<br>

# 🌦️ Український гідрометеорологічний центр для Home Assistant

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

[English](./readme.md) | [**Українською**](./readme.uk.md)

> [!NOTE]
> Інтеграція для погодних, радіаційних і гідрологічних даних від [Українського гідрометеорологічного центру][ukr-hmc].

> [!IMPORTANT]
> Це незалежний спільнотний проєкт, не пов’язаний з Українським гідрометеорологічним центром.

Ця інтеграція додає дані з [meteo.gov.ua][ukr-hmc] до [Home Assistant][home-assistant] як нативні сутності погоди та сенсори.

## Спонсорство

Ваша підтримка допоможе мені розвивати й підтримувати більше таких проєктів.

- 💖 [Стати спонсором на GitHub][gh-sponsors-url]
- ☕️ [Підтримати на Buy Me A Coffee][buymeacoffee-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Встановлення

Найпростіше встановити інтеграцію через [HACS][hacs-url]. Натисніть кнопку нижче:

[![Додати до HACS через My Home Assistant][hacs-install-image]][hacs-install-url]

<details>
  <summary>Якщо кнопка не працює, додайте репозиторій вручну</summary>

1. Відкрийте **HACS** → **Інтеграції** → **⋮** → **Користувацькі репозиторії**.
2. Натисніть **Додати**.
3. Вставте `https://github.com/denysdovhan/ha-ukr-hmc` як URL-адресу репозиторію.
4. Виберіть **Інтеграція** як категорію.
5. Знайдіть і встановіть **Український гідрометеорологічний центр**.

</details>

## Використання

Інтеграція налаштовується через інтерфейс Home Assistant. Натисніть кнопку нижче, щоб додати її:

[![Додати Український гідрометеорологічний центр][install-image]][install-url]

<details>
  <summary>Якщо кнопка не працює, додайте інтеграцію вручну</summary>

1. Відкрийте **Налаштування** → **Пристрої та служби**.
2. Натисніть **Додати інтеграцію** та знайдіть **Український гідрометеорологічний центр**.
3. Виконайте кроки налаштування.

</details>

## Що надає інтеграція

![Створення сутностей](./media/create-entries.png)

Інтеграція дозволяє створювати такі сутності:

| Джерело                | Поточні дані                                                                            | Прогнози              |
| ---------------------- | --------------------------------------------------------------------------------------- | --------------------- |
| Метеорологічна станція | Вимірювання фізичної станції: температура, вологість, тиск, вітер і погодні умови       | Добовий і на день/ніч |
| Погода для місця       | Прогнозовані умови для точки на карті; вимірювання фізичних станцій не використовуються | Погодинний і добовий  |
| Радіологічна станція   | Безпосередні значення у мкР/год і нЗв/год та час спостереження                          | —                     |
| Гідрологічний пост     | Щоденні вимірювання води та гідрологічна ситуація від постачальника                     | —                     |

Для погоди за місцем поточна сутність використовує запис постачальника за поточну годину. Добовий прогноз відповідає поданню meteo.gov.ua: запис на 03:00 надає мінімальну температуру, а запис на 15:00 — максимальну температуру та стан погоди. Неповні дні пропускаються.

Радіаційні вимірювання та гідрологічні ситуації відображаються так, як їх опублікував постачальник. Інтеграція не визначає рівень безпеки, не створює попереджень і не замінює офіційних рекомендацій.

### Погода

Ви можете стежити за погодними умовами за допомогою фізичної метеорологічної станції або вибравши місце на карті. Інтеграція надає і поточні погодні умови, і прогнози.

Види прогнозів відрізняються:

- **Метеорологічні станції** надають добові прогнози та прогнози на день/ніч. Дані оновлюються _кожні 3 години_.
- **Погода для місць** надає погодинні та добові прогнози. Дані оновлюються _щогодини_.

| Метеорологічна станція                                 | Погода для місця                                  |
| ------------------------------------------------------ | ------------------------------------------------- |
| ![Метеорологічна станція](./media/weather-station.png) | ![Погода для місця](./media/weather-location.png) |

### Радіація

Ви можете стежити за рівнем радіації за допомогою фізичної радіологічної станції.

<img src="./media/radiation.png" alt="Радіологічна станція" width="500">

### Гідрологія

Ви можете стежити за гідрологічними даними українських річок за допомогою фізичного гідрологічного поста: рівнем води, температурою води, гідрологічною ситуацією тощо.

<img src="./media/hydrology.png" alt="Гідрологічний пост" width="500">

## Видалення

1. Відкрийте **Налаштування** → **Пристрої та служби**.
2. Виберіть **Український гідрометеорологічний центр**.
3. Відкрийте меню **⋮** і натисніть **Видалити**.
4. Видаліть інтеграцію з HACS і перезапустіть Home Assistant, якщо користувацький компонент більше не потрібен.

## Розробка

Хочете долучитися до проєкту?

Дякую! Докладніше читайте в [настановах для учасників](./contributing.md).

## Ліцензія

MIT © [Денис Довгань][denysdovhan]

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
