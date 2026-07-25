import asyncio
from py_solar_assistant import SolarAssistantClient, list_sites, get_device_metrics

async def main():
    # Replace with your actual API key
    api_key = "YOUR_API_KEY_HERE"
    
    async with SolarAssistantClient(api_key) as client:
        # List sites
        sites = await list_sites(client)
        print(f"Found {len(sites)} sites:")
        
        for s in sites:
            print(f"  ID: {s.id}, Name: {s.name}, Inverter: {s.inverter}")
        
        # Find site 19489
        site = next((s for s in sites if s.id == 19489), None)
        if not site:
            print("Site 19489 not found")
            return
        
        print(f"\nGetting metrics for site 19489: {site.name}")
        
        # Get metrics
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
    asyncio.run(main())
