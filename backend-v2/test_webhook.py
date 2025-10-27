#!/usr/bin/env python3
"""
Quick test script for webhook functionality
Run this to verify your webhook is working correctly
"""
import requests
import json
from datetime import datetime

# Configuration
WEBHOOK_URL = "http://localhost:8001/api/v2/webhooks/orders"
TEST_URL = "http://localhost:8001/api/v2/webhooks/test"
LOGS_URL = "http://localhost:8001/api/v2/webhooks/logs"

def test_webhook_connectivity():
    """Test if webhook endpoint is accessible"""
    print("🔍 Testing webhook connectivity...")
    try:
        response = requests.get(TEST_URL)
        if response.status_code == 200:
            print("✅ Webhook endpoint is accessible")
            data = response.json()
            print(f"   Status: {data['status']}")
            print(f"   Signature required: {data['signature_required']}")
            return True
        else:
            print(f"❌ Webhook returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to webhook: {e}")
        print("   Make sure backend-v2 is running: python main.py")
        return False


def test_create_order():
    """Test creating an order via webhook"""
    print("\n📦 Testing order creation...")
    
    test_order = {
        "order_number": f"TEST-{int(datetime.now().timestamp())}",
        "product": "Test Nike Shoes",
        "price": 99.99,
        "quantity": 2,
        "email": "testcustomer@example.com",
        "customer_name": "John Test",
        "status": "pending"
    }
    
    print(f"   Sending order: {test_order['order_number']}")
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=test_order,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Order created successfully")
            print(f"   Order ID: {data['order_id']}")
            print(f"   Order Number: {data['order_number']}")
            print(f"   Message: {data['message']}")
            return True
        else:
            print(f"❌ Failed to create order: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating order: {e}")
        return False


def test_update_order():
    """Test updating an existing order"""
    print("\n🔄 Testing order update...")
    
    # First create an order
    order_number = f"UPDATE-TEST-{int(datetime.now().timestamp())}"
    
    initial_order = {
        "order_number": order_number,
        "product": "Initial Product",
        "price": 50.00,
        "status": "pending"
    }
    
    print(f"   Creating initial order: {order_number}")
    response1 = requests.post(WEBHOOK_URL, json=initial_order)
    
    if response1.status_code != 200:
        print("❌ Failed to create initial order")
        return False
    
    # Now update it
    updated_order = {
        "order_number": order_number,
        "product": "Updated Product",
        "price": 75.00,
        "status": "shipped",
        "tracking_number": "1Z999AA10123456784"
    }
    
    print(f"   Updating order with tracking...")
    response2 = requests.post(WEBHOOK_URL, json=updated_order)
    
    if response2.status_code == 200:
        data = response2.json()
        print("✅ Order updated successfully")
        print(f"   Order ID: {data['order_id']}")
        return True
    else:
        print(f"❌ Failed to update order: {response2.status_code}")
        return False


def test_alternative_field_names():
    """Test that alternative field names are mapped correctly"""
    print("\n🔀 Testing alternative field name mappings...")
    
    # Use alternative field names
    order_with_alternatives = {
        "order_number": f"ALT-{int(datetime.now().timestamp())}",
        "product_name": "Product via product_name field",  # Alternative to 'product'
        "unit_price": 39.99,  # Alternative to 'price'
        "qty": 3,  # Alternative to 'quantity'
        "customer_email": "alt@example.com",  # Alternative to 'email'
        "order_status": "verified"  # Alternative to 'status'
    }
    
    print("   Testing: product_name, unit_price, qty, customer_email, order_status")
    
    try:
        response = requests.post(WEBHOOK_URL, json=order_with_alternatives)
        
        if response.status_code == 200:
            print("✅ Alternative field names mapped correctly")
            return True
        else:
            print(f"❌ Failed with alternative names: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def view_webhook_logs():
    """View recent webhook logs"""
    print("\n📋 Viewing recent webhook logs...")
    
    try:
        response = requests.get(f"{LOGS_URL}?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} webhook logs")
            
            for i, log in enumerate(data['logs'][:5], 1):
                status_emoji = "✅" if log['processed'] else "⏳"
                print(f"\n   {i}. {status_emoji} {log['endpoint']}")
                print(f"      Status: {log['status_code']}")
                print(f"      Processed: {log['processed']}")
                print(f"      Time: {log['created_at']}")
                if log['error_message']:
                    print(f"      Error: {log['error_message']}")
            
            return True
        else:
            print(f"❌ Failed to fetch logs: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 ROMS V2 Webhook Test Suite")
    print("=" * 60)
    
    tests = [
        ("Connectivity", test_webhook_connectivity),
        ("Create Order", test_create_order),
        ("Update Order", test_update_order),
        ("Alternative Fields", test_alternative_field_names),
        ("View Logs", view_webhook_logs),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, success in results:
        emoji = "✅" if success else "❌"
        print(f"{emoji} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your webhook system is ready!")
        print("\n📚 Next steps:")
        print("   1. Configure your external software with the webhook URL:")
        print(f"      {WEBHOOK_URL}")
        print("   2. View API docs: http://localhost:8001/docs")
        print("   3. Read the full guide: WEBHOOK_SETUP_GUIDE.md")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

