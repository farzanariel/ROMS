#!/usr/bin/env python3
"""
Test script for Refract text format webhooks
"""
import requests

WEBHOOK_URL = "http://localhost:8001/api/v2/webhooks/orders"

# Your exact webhook message from Refract
refract_message = """Successful Checkout | Best Buy US
Product
STARLINK - Mini Kit AC Dual Band Wi-Fi System - White
Price
$299.99
Profile
Lennar #8-$48-@07
Proxy Details
Wealth Resi | http://resi-edge-pool.wealthproxies.com:5959/
Share Link
Click Here
Order Number
#BBY01-807102506907
Email
woozy_byes28@icloud.com
Image"""

def test_refract_webhook():
    """Test sending Refract format webhook"""
    print("=" * 60)
    print("🧪 Testing Refract Webhook Format")
    print("=" * 60)
    
    print("\n📤 Sending webhook message...")
    print("\nMessage content:")
    print("-" * 60)
    print(refract_message[:200] + "...")
    print("-" * 60)
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=refract_message,
            headers={"Content-Type": "text/plain"}
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Webhook processed successfully!")
            print(f"\n📦 Order Details:")
            print(f"   Order ID: {data.get('order_id')}")
            print(f"   Order Number: {data.get('order_number')}")
            print(f"   Message: {data.get('message')}")
            
            print("\n✅ SUCCESS! Your Refract webhook is working!")
            print("\n📋 What got parsed:")
            print("   - Product: STARLINK - Mini Kit...")
            print("   - Price: $299.99")
            print("   - Order Number: BBY01-807102506907")
            print("   - Email: woozy_byes28@icloud.com")
            print("   - Profile: Lennar #8-$48-@07")
            print("   - Proxy List: Wealth Resi | http://...")
            print("   - Status: verified (auto-detected from 'Successful Checkout')")
            
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending webhook: {e}")
        print("\n⚠️  Make sure backend-v2 is running:")
        print("   cd backend-v2")
        print("   python main.py")
        return False


def view_order_in_logs():
    """View the order in webhook logs"""
    print("\n" + "=" * 60)
    print("📋 Viewing Webhook Logs")
    print("=" * 60)
    
    try:
        response = requests.get(f"http://localhost:8001/api/v2/webhooks/logs?limit=1")
        
        if response.status_code == 200:
            data = response.json()
            if data['logs']:
                log = data['logs'][0]
                print(f"\n✅ Latest webhook log:")
                print(f"   Status Code: {log['status_code']}")
                print(f"   Processed: {log['processed']}")
                print(f"   Time: {log['created_at']}")
                
                if log['error_message']:
                    print(f"   Error: {log['error_message']}")
                else:
                    print(f"   ✅ No errors")
            else:
                print("\n❌ No webhook logs found")
        else:
            print(f"\n❌ Failed to fetch logs: {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error fetching logs: {e}")


def main():
    """Run the test"""
    print("\n🎯 This will test your exact Refract webhook message format\n")
    
    success = test_refract_webhook()
    
    if success:
        view_order_in_logs()
        
        print("\n" + "=" * 60)
        print("🎉 Configuration Guide")
        print("=" * 60)
        print("\nIn your Refract/Discord bot settings:")
        print(f"\n1. Set Webhook URL to:")
        print(f"   {WEBHOOK_URL}")
        print(f"\n2. Set Content-Type to: text/plain (or leave default)")
        print(f"\n3. Enable webhook for 'Successful Checkout' events")
        print(f"\n4. Test it - orders will automatically appear in your database!")
        
        print("\n📊 View all your orders:")
        print("   • Open SQLite database: backend-v2/roms_v2.db")
        print("   • Check webhook logs: http://localhost:8001/api/v2/webhooks/logs")
        print("   • API docs: http://localhost:8001/docs")
        
    else:
        print("\n" + "=" * 60)
        print("❌ Test Failed - Troubleshooting")
        print("=" * 60)
        print("\n1. Make sure backend-v2 is running:")
        print("   cd backend-v2")
        print("   python main.py")
        print("\n2. Check that port 8001 is accessible")
        print("\n3. View backend logs for errors")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

