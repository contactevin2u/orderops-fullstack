import puppeteer from 'puppeteer'

async function main() {
  const invoiceId = process.env.INVOICE_ID || process.argv[2]
  if (!invoiceId) {
    console.error('Invoice ID is required. Pass via INVOICE_ID env or as an argument.')
    process.exit(1)
  }

  const browser = await puppeteer.launch({ headless: 'new' })
  const page = await browser.newPage()
  const url = `http://localhost:3000/invoice/${invoiceId}/print`
  await page.goto(url, { waitUntil: 'networkidle0' })
  await page.pdf({
    path: `invoice-${invoiceId}.pdf`,
    format: 'A4',
    printBackground: true,
    margin: { top: '20mm', right: '20mm', bottom: '20mm', left: '20mm' },
  })
  await browser.close()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
