#!/usr/bin/env python3
"""
Load Test Script for Webhook Queue
Tests system under high volume
"""
import asyncio
import aiohttp
import time
from datetime import datetime

WEBHOOK_URL = "http://localhost:8001/api/v2/webhooks/orders"
STATS_URL = "http://localhost:8001/api/v2/webhooks/queue/stats"


async def send_webhook(session, i):
    """Send a single webhook"""
    payload = {
        "embeds": [{
            "author": {"name": f"Test Order {i} | Load Test"},
            "description": f"""Product
Test Product {i}
Price
${99.99 + i * 0.01}
Order Number
LOAD-TEST-{datetime.utcnow().timestamp()}-{i}
Email
loadtest{i}@example.com
Profile
Load Test Profile {i % 10}
Proxy Details
Test Proxy
"""
        }]
    }
    
    start = time.time()
    try:
        async with session.post(WEBHOOK_URL, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            elapsed = (time.time() - start) * 1000
            return {
                "status": resp.status,
                "time_ms": elapsed,
                "success": resp.status == 200
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "status": 0,
            "time_ms": elapsed,
            "success": False,
            "error": str(e)
        }


async def get_queue_stats(session):
    """Get current queue statistics"""
    try:
        async with session.get(STATS_URL) as resp:
            if resp.status == 200:
                return await resp.json()
    except:
        pass
    return None


async def run_load_test(num_webhooks: int, batch_size: int = 50):
    """
    Run load test
    
    Args:
        num_webhooks: Total number of webhooks to send
        batch_size: How many to send concurrently
    """
    print("=" * 70)
    print(f"🚀 WEBHOOK QUEUE LOAD TEST")
    print("=" * 70)
    print(f"\n📊 Test Configuration:")
    print(f"   Total webhooks: {num_webhooks}")
    print(f"   Batch size: {batch_size}")
    print(f"   Target: {WEBHOOK_URL}")
    print()
    
    # Get initial stats
    async with aiohttp.ClientSession() as session:
        initial_stats = await get_queue_stats(session)
        if initial_stats:
            print(f"📈 Initial Stats:")
            print(f"   Queue size: {initial_stats.get('queue_size', 0)}")
            print(f"   Total received: {initial_stats.get('total_received', 0)}")
            print(f"   Total processed: {initial_stats.get('total_processed', 0)}")
            print()
    
    # Run test
    print(f"⚡ Sending {num_webhooks} webhooks...")
    start_time = time.time()
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        # Send in batches to avoid overwhelming the system
        for batch_start in range(0, num_webhooks, batch_size):
            batch_end = min(batch_start + batch_size, num_webhooks)
            batch_num = (batch_start // batch_size) + 1
            total_batches = (num_webhooks + batch_size - 1) // batch_size
            
            print(f"   Batch {batch_num}/{total_batches}: Sending webhooks {batch_start+1}-{batch_end}...", end=" ", flush=True)
            
            batch_tasks = [
                send_webhook(session, i)
                for i in range(batch_start, batch_end)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
            
            # Quick stats
            batch_success = sum(1 for r in batch_results if r['success'])
            batch_avg_time = sum(r['time_ms'] for r in batch_results) / len(batch_results)
            print(f"✅ {batch_success}/{len(batch_results)} ({batch_avg_time:.0f}ms avg)")
            
            # Small delay between batches
            if batch_end < num_webhooks:
                await asyncio.sleep(0.1)
    
    total_time = time.time() - start_time
    
    # Calculate results
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    avg_response_time = sum(r['time_ms'] for r in results) / len(results)
    min_response_time = min(r['time_ms'] for r in results)
    max_response_time = max(r['time_ms'] for r in results)
    
    # Print results
    print()
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print(f"\n⏱️  Performance:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Webhooks/second: {num_webhooks/total_time:.1f}")
    print(f"   Avg response time: {avg_response_time:.1f}ms")
    print(f"   Min response time: {min_response_time:.1f}ms")
    print(f"   Max response time: {max_response_time:.1f}ms")
    
    print(f"\n✅ Success Rate:")
    print(f"   Successful: {successful}/{num_webhooks} ({successful/num_webhooks*100:.1f}%)")
    print(f"   Failed: {failed}/{num_webhooks} ({failed/num_webhooks*100:.1f}%)")
    
    # Get final stats
    print(f"\n⏳ Waiting 3 seconds for processing...")
    await asyncio.sleep(3)
    
    async with aiohttp.ClientSession() as session:
        final_stats = await get_queue_stats(session)
        if final_stats:
            print(f"\n📈 Final Queue Stats:")
            print(f"   Queue size: {final_stats.get('queue_size', 0)}")
            print(f"   Queue peak: {final_stats.get('queue_size_peak', 0)}")
            print(f"   Total received: {final_stats.get('total_received', 0)}")
            print(f"   Total processed: {final_stats.get('total_processed', 0)}")
            print(f"   Total failed: {final_stats.get('total_failed', 0)}")
            print(f"   Success rate: {final_stats.get('success_rate', 0):.1f}%")
            print(f"   Avg processing time: {final_stats.get('avg_processing_time_ms', 0):.1f}ms")
            print(f"   Dead letter queue: {final_stats.get('dead_letter_queue_size', 0)}")
    
    # Verdict
    print()
    print("=" * 70)
    if successful == num_webhooks and avg_response_time < 200:
        print("🎉 EXCELLENT! All webhooks received quickly!")
    elif successful >= num_webhooks * 0.99:
        print("✅ GREAT! 99%+ success rate!")
    elif successful >= num_webhooks * 0.95:
        print("👍 GOOD! 95%+ success rate")
    else:
        print("⚠️  NEEDS ATTENTION! Success rate below 95%")
    print("=" * 70)
    print()


async def main():
    """Main function with test options"""
    import sys
    
    if len(sys.argv) > 1:
        num_webhooks = int(sys.argv[1])
    else:
        print("How many webhooks to send?")
        print("  1. Light test (50 webhooks)")
        print("  2. Medium test (200 webhooks)")
        print("  3. Heavy test (500 webhooks)")
        print("  4. Extreme test (1000 webhooks)")
        print("  5. Custom amount")
        print()
        choice = input("Choose [1-5]: ").strip()
        
        if choice == "1":
            num_webhooks = 50
        elif choice == "2":
            num_webhooks = 200
        elif choice == "3":
            num_webhooks = 500
        elif choice == "4":
            num_webhooks = 1000
        elif choice == "5":
            num_webhooks = int(input("Enter number of webhooks: "))
        else:
            print("Invalid choice, using default (50)")
            num_webhooks = 50
    
    await run_load_test(num_webhooks, batch_size=50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")

