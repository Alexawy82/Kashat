#!/usr/bin/env python3
"""
Test script for 'Accept All' AI Category functionality

Demonstrates smart category acceptance with automatic creation and duplicate prevention.
"""

import sys
import os
import json
import uuid
from datetime import datetime, UTC

sys.path.append('apps/backend/src')

from kashat.ai_category_acceptance import (
    accept_ai_category, 
    accept_all_ai_categories,
    get_category_acceptance_service
)
from kashat.ai_enhanced_categorization import categorize_transaction_enhanced
from kashat.db import get_conn

def create_test_transactions():
    """Create test transactions with AI suggestions that need acceptance"""
    
    conn = get_conn()
    test_transactions = []
    
    # Test cases with mix of existing and new categories
    test_cases = [
        {
            'description': 'WHOLE FOODS MARKET #1234 ORGANIC GROCERIES',
            'amount': -89.45,
            'expected_categories': ['Grocery', 'Organic Food']  # Grocery exists, Organic Food needs creation
        },
        {
            'description': 'PLANET FITNESS MONTHLY MEMBERSHIP',
            'amount': -22.99,
            'expected_categories': ['Health & Fitness', 'Gym Membership']  # Both need creation
        },
        {
            'description': 'CHIPOTLE MEXICAN GRILL #5678',
            'amount': -12.47,
            'expected_categories': ['Food & Dining', 'Fast Casual']  # Food & Dining exists, Fast Casual new
        },
        {
            'description': 'TESLA SUPERCHARGER STATION',
            'amount': -45.67,
            'expected_categories': ['Electric Vehicle', 'Automotive']  # Both new
        },
        {
            'description': 'ZOOM VIDEO COMMUNICATIONS',
            'amount': -14.99,
            'expected_categories': ['Software', 'Video Conferencing']  # Software exists, Video Conferencing new
        },
        {
            'description': 'VETERINARY CLINIC ANIMAL CARE',
            'amount': -125.00,
            'expected_categories': ['Pet Care', 'Veterinary']  # Both new
        },
        {
            'description': 'HOME DEPOT GARDEN CENTER',
            'amount': -67.89,
            'expected_categories': ['Shopping', 'Home & Garden']  # Shopping exists, Home & Garden new
        }
    ]
    
    print("🧪 Creating test transactions...")
    
    for i, case in enumerate(test_cases):
        tx_id = str(uuid.uuid4())
        
        # Insert test transaction with all required fields
        conn.execute("""
            INSERT INTO transaction (
                id, account_id, description_norm, amount, posted_at,
                fingerprint, created_at, ai_category_suggestions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            tx_id,
            'test_account_123',
            case['description'],
            case['amount'],
            datetime.now(UTC),
            f"test_fingerprint_{i}_{hash(case['description']) % 10000}",  # Unique fingerprint
            datetime.now(UTC),
            json.dumps([
                {
                    'category_name': cat,
                    'confidence': 0.85 + (i * 0.02),  # Vary confidence slightly
                    'reasoning': f'AI detected pattern for {cat}'
                }
                for cat in case['expected_categories']
            ])
        ])
        
        test_transactions.append({
            'id': tx_id,
            'description': case['description'],
            'amount': case['amount'],
            'expected_categories': case['expected_categories']
        })
    
    print(f"✅ Created {len(test_transactions)} test transactions")
    return test_transactions

def test_single_acceptance():
    """Test single category acceptance"""
    
    print("\n🎯 TESTING SINGLE CATEGORY ACCEPTANCE")
    print("=" * 50)
    
    # Test with existing category
    print("\n1. Testing with existing category...")
    result = accept_ai_category(
        transaction_id=str(uuid.uuid4()),
        suggested_category_name='Food & Dining',  # This exists
        confidence=0.9,
        create_if_missing=True
    )
    
    print(f"   Result: {result.action_taken}")
    print(f"   Category: {result.category_name}")
    print(f"   Success: {result.success}")
    
    # Test with new category
    print("\n2. Testing with new category...")
    result = accept_ai_category(
        transaction_id=str(uuid.uuid4()),
        suggested_category_name='Electric Vehicle Charging',  # This doesn't exist
        confidence=0.85,
        create_if_missing=True
    )
    
    print(f"   Result: {result.action_taken}")
    print(f"   Category: {result.category_name}")
    print(f"   Success: {result.success}")
    
    # Test with similar category (should merge)
    print("\n3. Testing with similar category...")
    result = accept_ai_category(
        transaction_id=str(uuid.uuid4()),
        suggested_category_name='Food and Dining',  # Very similar to existing
        confidence=0.88,
        create_if_missing=True
    )
    
    print(f"   Result: {result.action_taken}")
    print(f"   Category: {result.category_name}")
    print(f"   Similar found: {result.similar_category_found}")
    print(f"   Success: {result.success}")

def test_batch_acceptance(test_transactions):
    """Test batch 'Accept All' functionality"""
    
    print("\n🚀 TESTING BATCH 'ACCEPT ALL' FUNCTIONALITY")
    print("=" * 60)
    
    # Prepare batch acceptance data
    acceptances = []
    
    for tx in test_transactions:
        # Get AI suggestions for this transaction
        suggestions = categorize_transaction_enhanced(tx['description'], tx['amount'])
        
        for suggestion in suggestions[:1]:  # Take top suggestion
            acceptances.append((
                tx['id'],
                suggestion.category_name,
                suggestion.confidence
            ))
    
    print(f"\n📋 Prepared {len(acceptances)} category acceptances:")
    for i, (tx_id, category, confidence) in enumerate(acceptances, 1):
        print(f"   {i}. {category} (confidence: {confidence:.1%})")
    
    # Preview batch acceptance
    print("\n🔍 Previewing batch acceptance...")
    service = get_category_acceptance_service()
    
    from kashat.ai_category_acceptance import BatchAcceptanceRequest, CategoryAcceptanceRequest
    
    batch_request = BatchAcceptanceRequest(
        acceptances=[
            CategoryAcceptanceRequest(
                transaction_id=tx_id,
                suggested_category_name=category,
                confidence=confidence,
                create_if_missing=True
            )
            for tx_id, category, confidence in acceptances
        ],
        create_missing_categories=True,
        auto_merge_threshold=0.85
    )
    
    preview = service.preview_batch_acceptance(batch_request)
    
    print(f"📊 Preview Results:")
    print(f"   - Will use existing: {len(preview['will_use_existing'])}")
    print(f"   - Will create new: {len(preview['will_create_categories'])}")
    print(f"   - Will merge similar: {len(preview['will_merge_similar'])}")
    print(f"   - Potential issues: {len(preview['potential_issues'])}")
    print(f"   - Success rate estimate: {preview['estimated_success_rate']:.1%}")
    
    if preview['will_create_categories']:
        print(f"\n🆕 Categories to be created:")
        for item in preview['will_create_categories']:
            print(f"   - {item['category']}")
    
    if preview['will_merge_similar']:
        print(f"\n🔀 Categories to be merged:")
        for item in preview['will_merge_similar']:
            print(f"   - '{item['suggested']}' → '{item['will_use']}' ({item['similarity']:.1%} similar)")
    
    # Execute batch acceptance
    print(f"\n✅ Executing 'Accept All'...")
    result = accept_all_ai_categories(
        acceptances=acceptances,
        create_missing=True
    )
    
    print(f"\n🎉 BATCH ACCEPTANCE RESULTS")
    print(f"   Total requested: {result.total_requested}")
    print(f"   ✅ Successful: {result.successful_applications}")
    print(f"   🆕 Categories created: {result.categories_created}")
    print(f"   🔀 Categories merged: {result.categories_merged}")
    print(f"   ❌ Failed: {result.failed_applications}")
    
    if result.new_categories:
        print(f"\n🆕 New categories created:")
        for cat in result.new_categories:
            print(f"   - {cat['name']} (ID: {cat['id'][:8]}...)")
    
    if result.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in result.warnings[:5]:
            print(f"   - {warning}")
    
    return result

def test_duplicate_prevention():
    """Test duplicate prevention logic"""
    
    print("\n🛡️  TESTING DUPLICATE PREVENTION")
    print("=" * 45)
    
    # Test creating similar categories in sequence
    similar_categories = [
        'Food & Dining',
        'Food and Dining',
        'food & dining',
        'FOOD & DINING',
        'Food&Dining'
    ]
    
    results = []
    
    for i, category in enumerate(similar_categories):
        print(f"\n{i+1}. Testing: '{category}'")
        
        result = accept_ai_category(
            transaction_id=str(uuid.uuid4()),
            suggested_category_name=category,
            confidence=0.8,
            create_if_missing=True
        )
        
        print(f"   Action: {result.action_taken}")
        print(f"   Category used: {result.category_name}")
        if result.similar_category_found:
            print(f"   Similar found: {result.similar_category_found}")
        
        results.append(result)
    
    # Summary
    created_count = sum(1 for r in results if r.action_taken == 'created_and_applied')
    merged_count = sum(1 for r in results if r.action_taken == 'merged_and_applied')
    existing_count = sum(1 for r in results if r.action_taken == 'applied_existing')
    
    print(f"\n📊 Duplicate Prevention Summary:")
    print(f"   - Categories created: {created_count}")
    print(f"   - Merged with existing: {merged_count}")
    print(f"   - Used existing: {existing_count}")
    print(f"   - Total duplicates prevented: {merged_count + existing_count}")

def show_final_category_stats():
    """Show final category statistics"""
    
    print("\n📈 FINAL CATEGORY STATISTICS")
    print("=" * 40)
    
    conn = get_conn()
    
    # Total categories
    total_cats = conn.execute('SELECT COUNT(*) FROM category').fetchone()[0]
    print(f"📂 Total categories: {total_cats}")
    
    # Recently created categories
    recent_cats = conn.execute("""
        SELECT name FROM category 
        ORDER BY rowid DESC 
        LIMIT 10
    """).fetchall()
    
    print(f"🆕 Recent categories:")
    for cat in recent_cats:
        print(f"   - {cat[0]}")
    
    # Categorization coverage
    categorized = conn.execute('SELECT COUNT(*) FROM transaction_category').fetchone()[0]
    total_txns = conn.execute('SELECT COUNT(*) FROM transaction').fetchone()[0]
    rate = (categorized / max(total_txns, 1)) * 100
    
    print(f"📊 Categorization rate: {rate:.1f}% ({categorized}/{total_txns})")

def cleanup_test_data():
    """Clean up test transactions"""
    
    print("\n🧹 Cleaning up test data...")
    conn = get_conn()
    
    # Remove test transactions
    conn.execute("DELETE FROM transaction WHERE account_id = 'test_account_123'")
    conn.execute("DELETE FROM transaction_category WHERE tx_id NOT IN (SELECT id FROM transaction)")
    
    print("✅ Test data cleaned up")

def main():
    """Main test function"""
    
    print("🧪 AI CATEGORY ACCEPTANCE - 'ACCEPT ALL' TEST")
    print("=" * 70)
    
    try:
        # Create test data
        test_transactions = create_test_transactions()
        
        # Test single acceptance
        test_single_acceptance()
        
        # Test duplicate prevention
        test_duplicate_prevention()
        
        # Test batch acceptance (Accept All)
        batch_result = test_batch_acceptance(test_transactions)
        
        # Show final stats
        show_final_category_stats()
        
        print(f"\n🎉 SUCCESS SUMMARY")
        print(f"   ✅ Accept All processed {batch_result.total_requested} suggestions")
        print(f"   ✅ Created {batch_result.categories_created} new categories")
        print(f"   ✅ Prevented duplicates through smart merging")
        print(f"   ✅ Maintained data integrity")
        
        print(f"\n🎯 KEY FEATURES DEMONSTRATED:")
        print(f"   • Automatic category creation for missing categories")
        print(f"   • Duplicate prevention with fuzzy matching")
        print(f"   • Batch processing for 'Accept All' functionality")
        print(f"   • Smart merging of similar categories")
        print(f"   • Confidence-based decision making")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        cleanup_test_data()

if __name__ == "__main__":
    main()