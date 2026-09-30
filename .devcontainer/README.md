# Trying the Jyotish platform in a codespace

1. Wait for the setup to finish; it takes a few minutes the first time. Two terminals then start the API and the web app.
2. The app opens in a new tab on port 3000. If it doesn't, open the **Ports** tab and click the globe next to "Jyotish app".
3. Try these pages:
   - `/my`: the consumer app, in English or Hindi.
   - `/workbench`: the professional chart, dashas, yogas, readings, timeline and report.
   - `/panchanga`, `/match` and `/rectify`.
4. Enter any birth date, time and place. Place search works offline from GeoNames; coordinates also work.

The planetary data is NASA JPL DE421, which covers 1900 to 2053. The address is private to your GitHub account unless you change the port's visibility.

Stop the codespace when you're done, from github.com/codespaces, so it doesn't use your free hours.
