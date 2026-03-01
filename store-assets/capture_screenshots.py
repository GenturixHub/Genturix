#!/usr/bin/env python3
"""
GENTURIX - Script para capturar screenshots para las tiendas
Ejecutar: python3 capture_screenshots.py
"""

import asyncio
from playwright.async_api import async_playwright
import os

BASE_URL = os.environ.get("APP_URL", "https://genturix-scroll-fix.preview.emergentagent.com")
OUTPUT_DIR = "/app/store-assets/screenshots"

CREDENTIALS = {
    "resident": {"email": "test-resident@genturix.com", "password": "Admin123!"},
    "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
    "guard": {"email": "guarda1@genturix.com", "password": "Guard123!"},
}

RESOLUTIONS = {
    "playstore": {"width": 1080, "height": 1920},
    "appstore": {"width": 1290, "height": 2796},
}


async def capture_with_login(browser, resolution, user_type, output_path, filename):
    """Capturar screenshot con login fresco en contexto nuevo"""
    context = await browser.new_context(viewport=resolution, device_scale_factor=1)
    page = await context.new_page()
    
    creds = CREDENTIALS[user_type]
    
    await page.goto(f"{BASE_URL}/login", timeout=60000)
    await asyncio.sleep(2)
    
    await page.fill('input[type="email"]', creds["email"])
    await page.fill('input[type="password"]', creds["password"])
    await page.click('button[type="submit"]')
    await asyncio.sleep(5)
    
    await page.screenshot(path=f"{output_path}/{filename}")
    print(f"  ✅ {filename}")
    
    await context.close()


async def capture_page(browser, resolution, user_type, url_path, output_path, filename):
    """Capturar screenshot de una página específica"""
    context = await browser.new_context(viewport=resolution, device_scale_factor=1)
    page = await context.new_page()
    
    # Login first
    creds = CREDENTIALS[user_type]
    await page.goto(f"{BASE_URL}/login", timeout=60000)
    await asyncio.sleep(2)
    await page.fill('input[type="email"]', creds["email"])
    await page.fill('input[type="password"]', creds["password"])
    await page.click('button[type="submit"]')
    await asyncio.sleep(4)
    
    # Navigate to target page
    await page.goto(f"{BASE_URL}{url_path}", timeout=60000)
    await asyncio.sleep(3)
    
    await page.screenshot(path=f"{output_path}/{filename}")
    print(f"  ✅ {filename}")
    
    await context.close()


async def capture_login_screen(browser, resolution, output_path, filename):
    """Capturar pantalla de login"""
    context = await browser.new_context(viewport=resolution, device_scale_factor=1)
    page = await context.new_page()
    
    await page.goto(f"{BASE_URL}/login", timeout=60000)
    await asyncio.sleep(2)
    
    await page.screenshot(path=f"{output_path}/{filename}")
    print(f"  ✅ {filename}")
    
    await context.close()


async def main():
    print("🚀 GENTURIX Screenshot Capture Tool")
    print(f"📍 URL: {BASE_URL}")
    print(f"📁 Output: {OUTPUT_DIR}")
    
    os.makedirs(f"{OUTPUT_DIR}/playstore", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/appstore", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # PLAY STORE (1080x1920)
        print("\n📱 Capturando screenshots para Play Store (1080x1920)...")
        ps_res = RESOLUTIONS["playstore"]
        ps_out = f"{OUTPUT_DIR}/playstore"
        
        await capture_login_screen(browser, ps_res, ps_out, "01-login.png")
        await capture_with_login(browser, ps_res, "resident", ps_out, "02-emergencia.png")
        await capture_with_login(browser, ps_res, "admin", ps_out, "03-dashboard.png")
        await capture_page(browser, ps_res, "admin", "/admin/users", ps_out, "04-usuarios.png")
        await capture_with_login(browser, ps_res, "guard", ps_out, "05-guardia.png")
        
        print("✅ Play Store screenshots completados!")
        
        # APP STORE (1290x2796)
        print("\n🍎 Capturando screenshots para App Store (1290x2796)...")
        as_res = RESOLUTIONS["appstore"]
        as_out = f"{OUTPUT_DIR}/appstore"
        
        await capture_login_screen(browser, as_res, as_out, "01-login.png")
        await capture_with_login(browser, as_res, "resident", as_out, "02-emergencia.png")
        await capture_with_login(browser, as_res, "admin", as_out, "03-dashboard.png")
        await capture_page(browser, as_res, "admin", "/admin/users", as_out, "04-usuarios.png")
        await capture_with_login(browser, as_res, "guard", as_out, "05-seguridad.png")
        
        print("✅ App Store screenshots completados!")
        
        await browser.close()
    
    print("\n🎉 ¡Todos los screenshots han sido capturados!")
    print(f"📁 Revisa: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
