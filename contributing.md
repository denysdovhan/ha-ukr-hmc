# Contributing

If you plan to contribute, please fork the repository and open a pull request.

## How to add a translation

Translations should be reviewed by a native speaker.

1. Copy `custom_components/ukr_hmc/translations/en.json` and name it with the
   appropriate language code.
2. Translate the values without changing the keys.
3. Open a pull request and ask a native speaker to review it.

## How to run locally

1. Clone and enter the repository:

   ```sh
   git clone https://github.com/denysdovhan/ha-ukr-hmc.git
   cd ha-ukr-hmc
   ```

2. Run the setup and development scripts:

   ```sh
   scripts/setup
   scripts/develop
   ```

Home Assistant is available at <http://localhost:8123>. Edit files in
`custom_components/ukr_hmc` and restart Home Assistant to test changes.
