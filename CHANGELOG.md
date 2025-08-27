# Changelog

## Unreleased
- fix image optimizer 400 errors by whitelisting sizes and bypassing optimizer for POD thumbnails
- ensure middleware excludes Next.js static/image routes
- add POD viewer page that supports images and PDFs
- improve driver commissions page with success messaging and tests
- proxy /static/uploads to API and normalize POD URLs so proof-of-delivery files render
