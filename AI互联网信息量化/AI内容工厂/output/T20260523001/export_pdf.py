import asyncio, os
from playwright.async_api import async_playwright

HTML_PATH = r'C:\Users\lucas\Desktop\AI互联网信息量化\AI内容工厂\output\T20260523001\html\report.html'
PDF_PATH = r'C:\Users\lucas\Desktop\AI互联网信息量化\AI内容工厂\output\T20260523001\pdf\report.pdf'

os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)

async def html_to_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f'file:///{HTML_PATH}')
        await page.wait_for_load_state('networkidle')
        await page.pdf(
            path=PDF_PATH,
            format='A4',
            print_background=True,
            margin=dict(top='10mm', bottom='10mm', left='10mm', right='10mm')
        )
        await browser.close()

asyncio.run(html_to_pdf())

size = os.path.getsize(PDF_PATH)
print(f'report.pdf generated: {size} bytes')
assert size > 1000, 'PDF too small!'
print('PDF generation completed!')
