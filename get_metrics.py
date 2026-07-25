import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, r'c:\Users\oleks\Desktop\solar_assistant\.venv\Lib\site-packages')

from py_solar_assistant import SolarAssistantClient, list_sites, get_device_metrics

async def get_site_metrics():
    # You'll need to provide your API key
    api_key = input("Enter your Solar Assistant API key: ")
    
    async with SolarAssistantClient(api_key) as client:
        # List sites to find site 19489
        sites = await list_sites(client)
        print(f"Found {len(sites)} sites")
        
        site = None
        for s in sites:
            print(f"Site ID: {s.id}, Name: {s.name}, Inverter: {s.inverter}")
            if s.id == 19489:
                site = s
                break
        
        if not site:
            print("Site 19489 not found")
            return
        
        print(f"\nGetting metrics for site: {site.name}")
        
        # Get metrics for the site
        try:
            metrics = await get_device_metrics(
                site.host or "",
                token=site.token or "",
                scheme="https",
                site_id=site.id,
                site_key=site.site_key or ""
            )
            
            print(f"\nFound {len(metrics)} metrics:")
            for m in metrics:
                print(f"  {m.topic}: {m.name} ({m.unit})")
                
        except Exception as e:
            print(f"Error getting metrics: {e}")

if __name__ == "__main__":
    asyncio.run(get_site_metrics())
