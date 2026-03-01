#!/usr/bin/env python3
"""
GENTURIX - Script para capturar screenshots para las tiendas
Ejecutar: python3 capture_screenshots.py

Requisitos: pip install playwright && playwright install chromium
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


async def login(page, user_type):
    """Login con las credenciales especificadas"""
    creds = CREDENTIALS[user_type]
    await page.goto(f"{BASE_URL}/login", timeout=60000)
    await asyncio.sleep(2)
    try:
        await page.wait_for_selector('input[type="email"]', timeout=10000)
    except:
        pass
    await page.fill('input[type="email"]', creds["email"])
    await page.fill('input[type="password"]', creds["password"])
    await page.click('button[type="submit"]')
    await asyncio.sleep(5)


async def capture_playstore(browser):
    """Capturar screenshots para Google Play Store"""
    print("\n📱 Capturando screenshots para Play Store (1080x1920)...")
    
    context = await browser.new_context(
        viewport=RESOLUTIONS["playstore"],
        device_scale_factor=1
    )
    page = await context.new_page()
    output = f"{OUTPUT_DIR}/playstore"
    os.makedirs(output, exist_ok=True)
    
    # 1. Login Screen
    await page.goto(f"{BASE_URL}/login", timeout=60000)
    await asyncio.sleep(2)
    await page.screenshot(path=f"{output}/01-login.png")
    print("  ✅ 01-login.png")
    
    # 2. Emergency (Resident)
    await login(page, "resident")
    await page.screenshot(path=f"{output}/02-emergencia.png")
    print("  ✅ 02-emergencia.png")
    
    # 3. Dashboard (Admin)
    await login(page, "admin")
    await page.screenshot(path=f"{output}/03-dashboard.png")
    print("  ✅ 03-dashboard.png")
    
    # 4. Users Management
    await page.goto(f"{BASE_URL}/admin/users", timeout=60000)
    await asyncio.sleep(3)
    await page.screenshot(path=f"{output}/04-usuarios.png")
    print("  ✅ 04-usuarios.png")
    
    # 5. Guard Panel
    await login(page, "guard")
    await page.screenshot(path=f"{output}/05-guardia.png")
    print("  ✅ 05-guardia.png")
    
    await context.close()
    print("✅ Play Store screenshots completados!")


async def capture_appstore(browser):
    """Capturar screenshots para Apple App Store"""
    print("\n🍎 Capturando screenshots para App Store (1290x2796)...")
    
    context = await browser.new_context(
        viewport=RESOLUTIONS["appstore"],
        device_scale_factor=1
    )
    page = await context.new_page()
    output = f"{OUTPUT_DIR}/appstore"
    os.makedirs(output, exist_ok=True)
    
    # 1. Login Screen
    await page.goto(f"{BASE_URL}/login", timeout=60000)
    await asyncio.sleep(2)
    await page.screenshot(path=f"{output}/01-login.png")
    print("  ✅ 01-login.png")
    
    # 2. Emergency (Resident)
    await login(page, "resident")
    await page.screenshot(path=f"{output}/02-emergencia.png")
    print("  ✅ 02-emergencia.png")
    
    # 3. Dashboard (Admin)
    await login(page, "admin")
    await page.screenshot(path=f"{output}/03-dashboard.png")
    print("  ✅ 03-dashboard.png")
    
    # 4. Users Management
    await page.goto(f"{BASE_URL}/admin/users", timeout=60000)
    await asyncio.sleep(3)
    await page.screenshot(path=f"{output}/04-usuarios.png")
    print("  ✅ 04-usuarios.png")
    
    # 5. Guard Panel
    await login(page, "guard")
    await page.screenshot(path=f"{output}/05-seguridad.png")
    print("  ✅ 05-seguridad.png")
    
    await context.close()
    print("✅ App Store screenshots completados!")


async def main():
    print("🚀 GENTURIX Screenshot Capture Tool")
    print(f"📍 URL: {BASE_URL}")
    print(f"📁 Output: {OUTPUT_DIR}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        await capture_playstore(browser)
        await capture_appstore(browser)
        
        await browser.close()
    
    print("\n🎉 ¡Todos los screenshots han sido capturados!")
    print(f"📁 Revisa: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
