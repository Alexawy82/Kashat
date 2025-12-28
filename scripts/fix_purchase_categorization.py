#!/usr/bin/env python3
"""
Fix Purchase Categorization Script

This script fixes the weak "purchase" categorization by re-running
enhanced AI categorization on all transactions.
"""

import sys
import os
import json
import requests
from datetime import datetime

# If running the backend locally
API_BASE = "http://localhost:8000/api"

def fix_purchase_categorization():
    """Fix transactions that are generically categorized as 'purchase'"""
    
    print("🔧 FIXING WEAK 'PURCHASE' CATEGORIZATION")
    print("=" * 50)
    
    try:
        # Step 1: Get current stats
        print("\n📊 Getting current categorization stats...")
        response = requests.get(f"{API_BASE}/ai-enhanced/enhancement-stats")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total transactions: {stats['total_transactions']}")
            print(f"   Enhanced: {stats['enhanced_transactions']} ({stats['enhancement_rate']}%)")
            print(f"   Weak 'purchase' categorization: {stats['weak_categorization']['purchase_only_count']} ({stats['weak_categorization']['percentage']}%)")
            print(f"   Using enhanced AI: {stats['enhanced_ai_coverage']['using_enhanced_ai']} ({stats['enhanced_ai_coverage']['percentage']}%)")
            
            if stats['recommendations']:
                print(f"\n💡 Recommendations:")
                for rec in stats['recommendations']:
                    print(f"   - {rec}")
        else:
            print(f"   ❌ Failed to get stats: {response.status_code}")
        
        # Step 2: Fix purchase categories
        print(f"\n🔧 Fixing generic 'purchase' categorizations...")
        response = requests.post(f"{API_BASE}/ai-enhanced/fix-purchase-categories")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Found {result['transactions_found']} transactions with 'purchase' categorization")
            print(f"   ✅ Fixed {result['transactions_fixed']} transactions with better categories")
            print(f"   📝 {result['message']}")
        else:
            print(f"   ❌ Failed to fix purchase categories: {response.status_code}")
            return False
        
        # Step 3: Re-enhance all transactions (optional, for comprehensive fix)
        print(f"\n🚀 Starting comprehensive re-enhancement...")
        response = requests.get(f"{API_BASE}/ai-enhanced/reenhance-all")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result['message']}")
            print(f"   ⏱️  {result['estimated_duration']}")
        else:
            print(f"   ❌ Failed to start re-enhancement: {response.status_code}")
        
        print(f"\n🎉 CATEGORIZATION FIX COMPLETED!")
        print(f"   Your transactions should now have much better categorization")
        print(f"   Refresh your UI to see the improvements")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to API at {API_BASE}")
        print(f"   Make sure your backend is running!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_single_transaction():
    """Test enhanced categorization on a specific transaction"""
    
    print(f"\n🧪 TESTING ENHANCED CATEGORIZATION")
    print("=" * 40)
    
    # You can replace this with a real transaction ID from your database
    test_tx_id = "ab423714-8e2e-4d16-b681-d952df0123ed"  # Replace with real ID
    
    try:
        response = requests.get(f"{API_BASE}/ai-enhanced/test-enhanced/{test_tx_id}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Transaction: {result['description'][:60]}...")
            print(f"Amount: ${result['amount']}")
            
            print(f"\n🔴 Current suggestions:")
            for suggestion in result['current_suggestions']:
                print(f"   - {suggestion['category_name']}: {suggestion['confidence']:.1%}")
            
            print(f"\n🟢 Enhanced suggestions:")
            for suggestion in result['enhanced_suggestions']:
                print(f"   - {suggestion['category_name']}: {suggestion['confidence']:.1%}")
                print(f"     Reasoning: {suggestion['reasoning']}")
            
            if result['improvement']['better_categories']:
                print(f"\n✅ Enhanced AI provides better categorization!")
            
        else:
            print(f"❌ Test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

def main():
    """Main function"""
    
    print("🤖 LEDGERLOOP AI CATEGORIZATION FIX")
    print("=" * 50)
    print("This script will fix the weak 'purchase' categorization")
    print("by applying our enhanced AI categorization system.")
    print()
    
    # Test single transaction first
    test_single_transaction()
    
    # Fix all purchase categorizations
    success = fix_purchase_categorization()
    
    if success:
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Refresh your LedgerLoop UI")
        print(f"   2. Check the transactions - they should now have specific categories")
        print(f"   3. Use 'Accept All' to apply the improved categorizations")
        print(f"   4. The system will create missing categories automatically")
    else:
        print(f"\n❌ Fix failed - check your backend is running")

if __name__ == "__main__":
    main()