#!/usr/bin/env python3
"""
Real-time webhook monitor
Watch incoming webhooks as they arrive
"""
import requests
import time
import json
from datetime import datetime

STATS_URL = "http://localhost:8001/api/v2/webhooks/queue/stats"
LOGS_URL = "http://localhost:8001/api/v2/webhooks/logs"
ORDERS_URL = "http://localhost:8001/api/v2/orders"

def clear_screen():
    print("\033[2J\033[H", end="")

def get_stats():
    try:
        resp = requests.get(STATS_URL, timeout=2)
        if resp.ok:
            return resp.json()
    except:
        pass
    return None

def get_recent_logs(limit=5):
    try:
        resp = requests.get(f"{LOGS_URL}?limit={limit}", timeout=2)
        if resp.ok:
            return resp.json()
    except:
        pass
    return None

def get_recent_orders(limit=3):
    try:
        resp = requests.get(f"{ORDERS_URL}?page=1&page_size={limit}", timeout=2)
        if resp.ok:
            return resp.json()
    except:
        pass
    return None

def format_status(status_code):
    if status_code in [200, 202]:
        return f"✅ {status_code}"
    elif status_code == 400:
        return f"⚠️  {status_code}"
    else:
        return f"❌ {status_code}"

def main():
    print("=" * 80)
    print("🔍 REAL-TIME WEBHOOK MONITOR")
    print("=" * 80)
    print("\nWatching for incoming webhooks... (Press Ctrl+C to stop)\n")
    
    last_total = 0
    
    try:
        while True:
            clear_screen()
            
            print("=" * 80)
            print("🔍 REAL-TIME WEBHOOK MONITOR")
            print("=" * 80)
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Get stats
            stats = get_stats()
            if stats:
                # Check for new webhooks
                current_total = stats.get('total_received', 0)
                if current_total > last_total:
                    print(f"🎉 NEW WEBHOOK RECEIVED! (Total: {current_total})")
                    print()
                
                last_total = current_total
                
                print("📊 QUEUE STATISTICS")
                print("-" * 80)
                print(f"Status:           {stats.get('status', 'unknown').upper()}")
                print(f"Queue Size:       {stats.get('queue_size', 0)} messages")
                print(f"Total Received:   {stats.get('total_received', 0)}")
                print(f"Total Processed:  {stats.get('total_processed', 0)}")
                print(f"Total Failed:     {stats.get('total_failed', 0)}")
                print(f"Success Rate:     {stats.get('success_rate', 0):.1f}%")
                print(f"Workers:          {stats.get('workers_running', 0)}/{stats.get('workers_total', 0)}")
                print(f"Avg Process Time: {stats.get('avg_processing_time_ms', 0):.0f}ms")
                print()
            
            # Get recent logs
            logs = get_recent_logs(5)
            if logs and logs.get('logs'):
                print("📝 RECENT WEBHOOKS (Last 5)")
                print("-" * 80)
                for log in logs['logs']:
                    timestamp = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00'))
                    print(f"{format_status(log['status_code'])} | {timestamp.strftime('%H:%M:%S')} | {log['endpoint']}")
                    if log.get('error_message'):
                        print(f"      Error: {log['error_message'][:60]}...")
                print()
            
            # Get recent orders
            orders = get_recent_orders(3)
            if orders and orders.get('orders'):
                print("📦 RECENT ORDERS (Last 3)")
                print("-" * 80)
                for order in orders['orders']:
                    created = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                    status = order.get('status', 'N/A')
                    print(f"Order: {order['order_number']}")
                    print(f"  Product: {order.get('product', 'N/A')}")
                    print(f"  Price: ${order.get('price', 0):.2f}")
                    print(f"  Email: {order.get('email', 'N/A')}")
                    print(f"  Status: {status if status else 'Not Set'}")
                    print(f"  Time: {created.strftime('%H:%M:%S')}")
                    print()
            
            print("=" * 80)
            print("Refreshing in 2 seconds... (Press Ctrl+C to stop)")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped by user")
        
        # Show final stats
        print("\n📊 FINAL STATISTICS")
        print("-" * 80)
        stats = get_stats()
        if stats:
            print(f"Total Received:  {stats.get('total_received', 0)}")
            print(f"Total Processed: {stats.get('total_processed', 0)}")
            print(f"Total Failed:    {stats.get('total_failed', 0)}")
            print(f"Success Rate:    {stats.get('success_rate', 0):.1f}%")
        print()

if __name__ == "__main__":
    main()

