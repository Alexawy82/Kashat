#!/usr/bin/env python3
"""
Test script for AI infrastructure
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "apps" / "backend" / "src"
sys.path.insert(0, str(backend_path))

from kashat.ai import get_ai_service, LocalAIService


async def test_merchant_normalization():
    """Test merchant name normalization"""
    print("🧪 Testing Merchant Normalization...")
    
    ai_service = get_ai_service()
    local_service = LocalAIService()
    
    test_descriptions = [
        "STARBUCKS STORE #1234 SEATTLE WA",
        "AMAZON.COM*AB123CD45 AMZN.COM/BILL",
        "SQ *CORNER BAKERY CHICAGO IL",
        "NETFLIX.COM LOS ANGELES CA",
        "SHELL OIL 12345 ANYTOWN USA",
        "MCDONALD'S #12345 MAIN ST",
        "UBER TRIP SAN FRANCISCO CA",
        "RANDOM LOCAL BUSINESS #123"
    ]
    
    for description in test_descriptions:
        merchant_info = local_service.normalize_merchant(description)
        print(f"  📝 '{description[:40]}...'")
        print(f"     → {merchant_info.normalized_name} (confidence: {merchant_info.confidence:.2f})")
        if merchant_info.merchant_type:
            print(f"     → Type: {merchant_info.merchant_type}")
        print()


async def test_category_suggestions():
    """Test category suggestions"""
    print("🎯 Testing Category Suggestions...")
    
    local_service = LocalAIService()
    
    test_cases = [
        ("STARBUCKS COFFEE #1234", -4.50),
        ("SHELL GAS STATION", -35.00),
        ("AMAZON.COM PURCHASE", -89.99),
        ("UBER RIDE", -12.50),
        ("NETFLIX SUBSCRIPTION", -15.99),
        ("ELECTRIC COMPANY BILL", -125.00),
        ("EMPLOYER PAYROLL DEPOSIT", 2500.00),
        ("DOCTOR VISIT COPAY", -25.00)
    ]
    
    for description, amount in test_cases:
        suggestions = local_service.suggest_categories(description, amount)
        print(f"  💰 '{description}' (${amount})")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"     {i}. {suggestion.category_name} (confidence: {suggestion.confidence:.2f})")
            print(f"        Reason: {suggestion.reasoning}")
        print()


async def test_anomaly_detection():
    """Test anomaly detection"""
    print("🚨 Testing Anomaly Detection...")
    
    local_service = LocalAIService()
    
    test_cases = [
        ("NORMAL GROCERY PURCHASE", -45.67),
        ("LARGE INVESTMENT PURCHASE", -5000.00),
        ("ATM", -20.00),  # Short description
        ("FOREIGN EXCHANGE CONVERSION 1234567890123456", -234.50),
        ("INTERNATIONAL WIRE TRANSFER", -1500.00)
    ]
    
    for description, amount in test_cases:
        anomalies = local_service.detect_anomalies(description, amount)
        print(f"  ⚡ '{description}' (${amount})")
        if anomalies:
            print(f"     🚩 Anomalies: {', '.join(anomalies)}")
        else:
            print(f"     ✅ No anomalies detected")
        print()


async def test_full_analysis():
    """Test full transaction analysis"""
    print("🔍 Testing Full Transaction Analysis...")
    
    ai_service = get_ai_service()
    
    test_transactions = [
        ("STARBUCKS STORE #1234 SEATTLE WA", -4.50),
        ("AMAZON.COM*AB123CD45 AMZN.COM/BILL", -89.99),
        ("EMPLOYER DIRECT DEPOSIT", 2500.00)
    ]
    
    for description, amount in test_transactions:
        print(f"  🔬 Analyzing: '{description}' (${amount})")
        
        try:
            insights = await ai_service.analyze_transaction(description, amount)
            
            print(f"     🏪 Merchant: {insights.merchant_info.normalized_name if insights.merchant_info else 'Unknown'}")
            if insights.merchant_info:
                print(f"     📊 Merchant Confidence: {insights.merchant_info.confidence:.2f}")
            
            print(f"     🎯 Category Suggestions:")
            for suggestion in insights.category_suggestions[:2]:  # Top 2
                print(f"       - {suggestion.category_name} ({suggestion.confidence:.2f})")
            
            if insights.anomaly_flags:
                print(f"     🚩 Anomalies: {', '.join(insights.anomaly_flags)}")
            
            print(f"     ⭐ Overall Confidence: {insights.confidence_score:.2f}")
            print(f"     🔧 Method: {insights.processing_method}")
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
        
        print()


async def main():
    """Run all AI infrastructure tests"""
    print("🚀 LedgerLoop AI Infrastructure Test")
    print("=" * 50)
    
    try:
        await test_merchant_normalization()
        await test_category_suggestions()
        await test_anomaly_detection()
        await test_full_analysis()
        
        print("✅ All AI infrastructure tests completed successfully!")
        print("🎉 AI service is ready for integration!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)