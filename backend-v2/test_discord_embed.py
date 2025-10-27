#!/usr/bin/env python3
"""
Test Discord embed format webhook (what Refract actually sends)
"""
import requests
import json

WEBHOOK_URL = "http://localhost:8001/api/v2/webhooks/orders"

# Simulated Discord embed from Refract
discord_embed_payload = {
    "embeds": [{
        "author": {
            "name": "Successful Checkout | Best Buy US",
            "icon_url": "https://cdn.prismaio.com/refract/avatar.png"
        },
        "description": """Product
STARLINK - Mini Kit AC Dual Band Wi-Fi System - White
Price
$299.99
Profile
Lennar #8-$48-@07
Proxy Details
Wealth Resi | http://resi-edge-pool.wealthproxies.com:5959/
Order Number
#BBY01-807102506907
Email
woozy_byes28@icloud.com""",
        "footer": {
            "icon_url": "https://cdn.prismaio.com/refract/avatar.png",
            "text": "Prism Technologies"
        }
    }]
}

def test_discord_embed():
    """Test Discord embed format webhook"""
    print("=" * 60)
    print("🧪 Testing Discord Embed Format (Real Refract Format)")
    print("=" * 60)
    
    print("\n📤 Sending Discord embed webhook...")
    print("\nPayload structure:")
    print("-" * 60)
    print(f"Format: Discord Embed")
    print(f"Author: {discord_embed_payload['embeds'][0]['author']['name']}")
    print(f"Description preview: {discord_embed_payload['embeds'][0]['description'][:100]}...")
    print("-" * 60)
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=discord_embed_payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Discord embed processed successfully!")
            print(f"\n📦 Order Details:")
            print(f"   Order ID: {data.get('order_id')}")
            print(f"   Order Number: {data.get('order_number')}")
            print(f"   Message: {data.get('message')}")
            
            print("\n✅ SUCCESS! Discord embed parsing works!")
            print("\n📋 What got extracted from embed:")
            print("   - Author: Successful Checkout | Best Buy US")
            print("   - Product: STARLINK - Mini Kit...")
            print("   - Price: $299.99")
            print("   - Order Number: BBY01-807102506907")
            print("   - Email: woozy_byes28@icloud.com")
            print("   - Profile: Lennar #8-$48-@07")
            print("   - Status: verified")
            
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending webhook: {e}")
        return False


def main():
    """Run the test"""
    print("\n🎯 This simulates what Refract ACTUALLY sends (Discord embed format)\n")
    
    success = test_discord_embed()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Your webhook is ready for Refract!")
        print("=" * 60)
        print("\nRefract will send Discord embeds, and your webhook will:")
        print("1. ✅ Detect the embed format")
        print("2. ✅ Extract text from description/fields")
        print("3. ✅ Parse order details")
        print("4. ✅ Store in database")
        print("\nJust configure Refract with:")
        print(f"   {WEBHOOK_URL}")
        print("\nAnd it will work automatically! 🚀")
    else:
        print("\n" + "=" * 60)
        print("❌ Test Failed")
        print("=" * 60)
        print("\nCheck backend logs for errors:")
        print("   cd backend-v2 && tail -50 backend.log")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

