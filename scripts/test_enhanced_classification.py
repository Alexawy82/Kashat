#!/usr/bin/env python3
"""
Test script for enhanced transaction classification system.
"""

import sys
import os
import re

# Add the backend src to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'backend', 'src'))

from kashat.ai import LocalAIService
from kashat.detect.income import mark_income, BUSINESS_TRANSFER_RE, INTERNAL_TRANSFER_RE
from kashat.detect.zelle import parse_zelle_descriptor


def test_sample_transactions():
    """Test the enhanced classification on sample transactions."""
    
    # Sample transactions based on the real data we saw
    test_transactions = [
        {
            "description": "online banking transfer from brk 5906 confirmation# 3948098469",
            "amount": 1400.0,
            "expected_type": "Income",
            "reasoning": "Transfer from business/employer 'brk'"
        },
        {
            "description": "online banking transfer from sav 3454 confirmation# 5451565925",
            "amount": 1000.0,
            "expected_type": "Internal Transfer",
            "reasoning": "Transfer from savings account"
        },
        {
            "description": "keep the change transfer to acct 3454 for 09/10/25",
            "amount": -1.63,
            "expected_type": "Internal Transfer",
            "reasoning": "Keep the change program"
        },
        {
            "description": "zelle from john smith conf# 123456789",
            "amount": 50.0,
            "expected_type": "Zelle",
            "reasoning": "Zelle payment from person"
        },
        {
            "description": "payroll deposit from abc corp",
            "amount": 2500.0,
            "expected_type": "Income",
            "reasoning": "Payroll deposit"
        },
        {
            "description": "checkcard 0908 chick-fil-a #04884 raleigh nc",
            "amount": -36.29,
            "expected_type": "Food & Dining",
            "reasoning": "Restaurant purchase"
        }
    ]
    
    print("🧪 Testing Enhanced Transaction Classification\n")
    print("=" * 80)
    
    ai_service = LocalAIService()
    passed = 0
    total = len(test_transactions)
    
    for i, tx in enumerate(test_transactions, 1):
        print(f"\n{i}. Testing: {tx['description']}")
        print(f"   Amount: ${tx['amount']:.2f}")
        print(f"   Expected: {tx['expected_type']}")
        
        # Test AI categorization
        suggestions = ai_service.suggest_categories(tx['description'], tx['amount'])
        
        if suggestions:
            top_suggestion = suggestions[0]
            print(f"   AI Result: {top_suggestion.category_name} (confidence: {top_suggestion.confidence:.2f})")
            print(f"   Reasoning: {top_suggestion.reasoning}")
            
            # Check if classification matches expected
            if top_suggestion.category_name == tx['expected_type']:
                print("   ✅ PASSED")
                passed += 1
            else:
                print("   ❌ FAILED")
        else:
            print("   ❌ FAILED - No suggestions returned")
        
        print("   " + "-" * 60)
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    return passed == total


def test_income_detection():
    """Test income detection patterns."""
    print("\n🔍 Testing Income Detection Patterns\n")
    print("=" * 50)
    
    test_cases = [
        {
            "description": "online banking transfer from brk 5906",
            "amount": 1400.0,
            "should_be_income": True
        },
        {
            "description": "online banking transfer from sav 3454",
            "amount": 1000.0,
            "should_be_income": False
        },
        {
            "description": "payroll deposit direct",
            "amount": 2500.0,
            "should_be_income": True
        },
        {
            "description": "freelance payment from client",
            "amount": 800.0,
            "should_be_income": True
        }
    ]
    
    # Create mock transaction records
    records = []
    for i, case in enumerate(test_cases):
        records.append({
            "id": f"test-{i}",
            "description_norm": case["description"],
            "amount": case["amount"],
            "posted_at": "2025-09-30"
        })
    
    income_ids = mark_income(records)
    
    passed = 0
    for i, case in enumerate(test_cases):
        tx_id = f"test-{i}"
        is_income = tx_id in income_ids
        expected = case["should_be_income"]
        
        print(f"'{case['description']}' -> {'Income' if is_income else 'Not Income'}")
        if is_income == expected:
            print("✅ PASSED")
            passed += 1
        else:
            print("❌ FAILED")
        print()
    
    print(f"Income Detection: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_zelle_parsing():
    """Test Zelle counterparty extraction."""
    print("\n💸 Testing Zelle Parsing\n")
    print("=" * 40)
    
    test_cases = [
        {
            "description": "zelle from john smith conf# 123456789",
            "expected": {"type": "zelle", "direction": "from", "counterparty": "john smith"}
        },
        {
            "description": "zelle to jane doe confirmation 987654321",
            "expected": {"type": "zelle", "direction": "to", "counterparty": "jane doe"}
        },
        {
            "description": "regular purchase at store",
            "expected": None
        }
    ]
    
    passed = 0
    for case in test_cases:
        result = parse_zelle_descriptor(case["description"])
        expected = case["expected"]
        
        print(f"'{case['description']}'")
        print(f"Result: {result}")
        print(f"Expected: {expected}")
        
        if result == expected:
            print("✅ PASSED")
            passed += 1
        else:
            print("❌ FAILED")
        print()
    
    print(f"Zelle Parsing: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_regex_patterns():
    """Test regex patterns."""
    print("\n🔍 Testing Regex Patterns\n")
    print("=" * 40)
    
    # Test business transfer pattern
    print("Business Transfer Pattern:")
    test_descriptions = [
        "online banking transfer from brk 5906",
        "online banking transfer from sav 3454",
        "transfer from abc corp",
        "transfer from chk 1234"
    ]
    
    for desc in test_descriptions:
        match = BUSINESS_TRANSFER_RE.search(desc)
        internal_match = INTERNAL_TRANSFER_RE.search(desc)
        
        print(f"  '{desc}'")
        if match:
            print(f"    Business: {match.group(1)}")
        if internal_match:
            print(f"    Internal: YES")
        if not match and not internal_match:
            print(f"    No match")
        print()


if __name__ == "__main__":
    print("🚀 Starting Enhanced Classification Tests\n")
    
    all_passed = True
    
    try:
        # Run all tests
        all_passed &= test_sample_transactions()
        all_passed &= test_income_detection()
        all_passed &= test_zelle_parsing()
        test_regex_patterns()  # This is informational
        
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Enhanced classification is working correctly.")
        else:
            print("❌ Some tests failed. Review the output above.")
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()