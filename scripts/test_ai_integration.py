#!/usr/bin/env python3
"""
Comprehensive AI Integration Test

Tests the complete AI enhancement pipeline from frontend to backend,
validating all AI features work correctly end-to-end.
"""

import sys
import json
import asyncio
import requests
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "apps" / "backend" / "src"
sys.path.insert(0, str(backend_path))

from kashat.ai import get_ai_service
from kashat.ai_categories import get_category_matcher

# API Configuration
API_BASE = "http://127.0.0.1:8000/api"
WEB_BASE = "http://localhost:3001"

class AIIntegrationTester:
    """Comprehensive AI integration test suite"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
        if not success:
            self.errors.append(test_name)
    
    def test_api_health(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            success = response.status_code == 200
            self.log_test("API Health Check", success, f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_test("API Health Check", False, f"Error: {e}")
            return False
    
    def test_ai_stats_endpoint(self):
        """Test AI stats endpoint"""
        try:
            response = requests.get(f"{API_BASE}/ai/stats")
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_transactions", "ai_enhanced_transactions", "ai_service_status"]
                has_all_fields = all(field in data for field in required_fields)
                
                details = f"Total transactions: {data.get('total_transactions', 0)}, AI enhanced: {data.get('ai_enhanced_transactions', 0)}"
                self.log_test("AI Stats Endpoint", has_all_fields, details)
                return has_all_fields
            else:
                self.log_test("AI Stats Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("AI Stats Endpoint", False, f"Error: {e}")
            return False
    
    def test_merchant_normalization(self):
        """Test merchant normalization endpoint"""
        try:
            test_data = {
                "description": "STARBUCKS STORE #1234 SEATTLE WA",
                "amount": -4.50
            }
            
            response = requests.post(f"{API_BASE}/ai/normalize/merchant", json=test_data)
            if response.status_code == 200:
                data = response.json()
                
                # Check if Starbucks was correctly normalized
                normalized_correctly = data.get('normalized_name') == 'Starbucks'
                confidence_ok = data.get('confidence', 0) > 0.8
                
                success = normalized_correctly and confidence_ok
                details = f"Normalized: '{data.get('normalized_name')}', Confidence: {data.get('confidence', 0):.2f}"
                
                self.log_test("Merchant Normalization", success, details)
                return success
            else:
                self.log_test("Merchant Normalization", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Merchant Normalization", False, f"Error: {e}")
            return False
    
    def get_test_transaction_id(self):
        """Get a transaction ID for testing"""
        try:
            response = requests.get(f"{API_BASE}/transactions?limit=1")
            if response.status_code == 200:
                transactions = response.json()
                if transactions:
                    return transactions[0]['id']
            return None
        except:
            return None
    
    def test_transaction_analysis(self):
        """Test AI transaction analysis"""
        transaction_id = self.get_test_transaction_id()
        if not transaction_id:
            self.log_test("Transaction Analysis", False, "No transactions found for testing")
            return False
        
        try:
            response = requests.post(f"{API_BASE}/ai/analyze/transaction/{transaction_id}")
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["transaction_id", "confidence", "processing_method"]
                has_fields = all(field in data for field in required_fields)
                
                has_merchant = data.get('merchant_name') is not None
                has_confidence = 0 <= data.get('confidence', -1) <= 1
                
                success = has_fields and has_confidence
                details = f"Merchant: {data.get('merchant_name', 'None')}, Confidence: {data.get('confidence', 0):.2f}"
                
                self.log_test("Transaction Analysis", success, details)
                return success
            else:
                self.log_test("Transaction Analysis", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Transaction Analysis", False, f"Error: {e}")
            return False
    
    def test_smart_category_suggestions(self):
        """Test smart category suggestions"""
        transaction_id = self.get_test_transaction_id()
        if not transaction_id:
            self.log_test("Smart Category Suggestions", False, "No transactions found for testing")
            return False
        
        try:
            response = requests.get(f"{API_BASE}/ai/suggestions/smart-categories/{transaction_id}")
            if response.status_code == 200:
                data = response.json()
                
                # Check structure
                has_suggestions = 'suggestions' in data
                has_patterns = 'patterns' in data
                
                suggestions = data.get('suggestions', [])
                suggestions_valid = all(
                    'category_name' in s and 'confidence' in s and 'match_type' in s
                    for s in suggestions
                )
                
                success = has_suggestions and has_patterns and suggestions_valid
                details = f"Found {len(suggestions)} suggestions"
                
                self.log_test("Smart Category Suggestions", success, details)
                return success
            else:
                self.log_test("Smart Category Suggestions", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Smart Category Suggestions", False, f"Error: {e}")
            return False
    
    def test_category_usage_stats(self):
        """Test category usage statistics"""
        try:
            response = requests.get(f"{API_BASE}/ai/categories/usage-stats")
            if response.status_code == 200:
                data = response.json()
                
                # Check structure
                has_stats = 'category_stats' in data
                has_total = 'total_categories' in data
                has_most_used = 'most_used' in data
                
                success = has_stats and has_total and has_most_used
                details = f"Total categories: {data.get('total_categories', 0)}"
                
                self.log_test("Category Usage Stats", success, details)
                return success
            else:
                self.log_test("Category Usage Stats", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Category Usage Stats", False, f"Error: {e}")
            return False
    
    def test_ai_service_functionality(self):
        """Test core AI service functionality"""
        try:
            ai_service = get_ai_service()
            
            # Test merchant normalization
            merchant_info = ai_service.local_service.normalize_merchant("STARBUCKS #1234")
            merchant_ok = merchant_info.normalized_name == "Starbucks"
            
            # Test category suggestions
            suggestions = ai_service.local_service.suggest_categories("STARBUCKS COFFEE", -5.50)
            suggestions_ok = len(suggestions) > 0
            
            # Test anomaly detection
            anomalies = ai_service.local_service.detect_anomalies("LARGE PURCHASE", -5000.00)
            anomaly_ok = "large_amount" in anomalies
            
            success = merchant_ok and suggestions_ok and anomaly_ok
            details = f"Merchant: {merchant_ok}, Suggestions: {suggestions_ok}, Anomalies: {anomaly_ok}"
            
            self.log_test("AI Service Core Functions", success, details)
            return success
        except Exception as e:
            self.log_test("AI Service Core Functions", False, f"Error: {e}")
            return False
    
    def test_category_matcher_functionality(self):
        """Test category matcher functionality"""
        try:
            category_matcher = get_category_matcher()
            
            # Test cache refresh
            category_matcher._refresh_cache()
            has_categories = len(category_matcher.categories_cache) > 0
            
            # Test pattern analysis (will work even with empty results)
            patterns = category_matcher.analyze_transaction_patterns("Starbucks", -5.00)
            patterns_ok = isinstance(patterns, dict) and 'similar_count' in patterns
            
            success = has_categories and patterns_ok
            details = f"Cached categories: {len(category_matcher.categories_cache)}, Patterns: {patterns_ok}"
            
            self.log_test("Category Matcher Functions", success, details)
            return success
        except Exception as e:
            self.log_test("Category Matcher Functions", False, f"Error: {e}")
            return False
    
    def test_frontend_accessibility(self):
        """Test frontend accessibility"""
        try:
            # Test if frontend is accessible
            response = requests.get(WEB_BASE, timeout=10)
            success = response.status_code == 200
            
            details = f"Frontend accessible at {WEB_BASE}" if success else f"HTTP {response.status_code}"
            self.log_test("Frontend Accessibility", success, details)
            return success
        except Exception as e:
            self.log_test("Frontend Accessibility", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🧪 Starting AI Integration Test Suite")
        print("=" * 50)
        
        # Core connectivity tests
        api_ok = self.test_api_health()
        frontend_ok = self.test_frontend_accessibility()
        
        if not api_ok:
            print("\n❌ Cannot continue - API is not accessible")
            return False
        
        # AI functionality tests
        self.test_ai_stats_endpoint()
        self.test_merchant_normalization()
        self.test_transaction_analysis()
        self.test_smart_category_suggestions()
        self.test_category_usage_stats()
        
        # Core service tests
        self.test_ai_service_functionality()
        self.test_category_matcher_functionality()
        
        # Results summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.errors:
            print(f"\n❌ Failed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! AI integration is working perfectly!")
            return True
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please review the issues above.")
            return False


async def main():
    """Run the comprehensive AI integration test"""
    tester = AIIntegrationTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)