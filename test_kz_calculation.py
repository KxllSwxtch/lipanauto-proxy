#!/usr/bin/env python3
"""
Test Kazakhstan turnkey price calculation
Example: Kia Sorento 2023
"""

import requests
import json

# Test data for Kia Sorento (example from http://localhost:3000/car/kia/the-new-sorento-4/40705389)
# Model name from Encar: "The New Sorento 4"
# Base model name in kz-table.xlsx: "SORENTO"
# The mapper should automatically convert "The New Sorento 4" → "Sorento"
test_data = {
    "manufacturer": "Kia",
    "model": "The New Sorento 4",  # Use actual Encar model name
    "price_krw": 42900000,  # Example price in KRW
    "year": 2023,
    "engine_volume": 2.2  # 2.2L diesel engine
}

print("=" * 80)
print("TESTING KAZAKHSTAN TURNKEY PRICE CALCULATION")
print("=" * 80)
print(f"\nTest Vehicle:")
print(f"  Manufacturer: {test_data['manufacturer']}")
print(f"  Model: {test_data['model']}")
print(f"  Year: {test_data['year']}")
print(f"  Engine: {test_data['engine_volume']}L")
print(f"  Price (KRW): {test_data['price_krw']:,}")
print("\n" + "=" * 80)

# Make API request
url = "http://localhost:8000/api/customs/calculate-kazakhstan"

try:
    print(f"\nMaking API request to: {url}")
    response = requests.post(url, json=test_data, timeout=30)

    print(f"Response status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        print("\n" + "=" * 80)
        print("CALCULATION RESULT")
        print("=" * 80)

        if result.get("success"):
            print(f"\n✅ Calculation successful!")
            print(f"\n🎯 TURNKEY PRICE:")
            print(f"  KZT: {result['turnkey_price_kzt']:,.2f} ₸")
            print(f"  USD: ${result['turnkey_price_usd']:,.2f}")

            if result.get("breakdown"):
                breakdown = result["breakdown"]
                print(f"\n📊 BREAKDOWN:")
                print(f"\n  Korea Expenses:")
                print(f"    Car price (KRW): {breakdown['car_price_krw']:,.0f}")
                print(f"    Parking fee (KRW): {breakdown['parking_fee_krw']:,.0f}")
                print(f"    Transportation (KRW): {breakdown['transportation_korea_krw']:,.0f}")
                print(f"    Export docs (KRW): {breakdown['export_docs_krw']:,.0f}")
                print(f"    Freight (USD): ${breakdown['freight_usd']:,.0f}")
                print(f"    Total Korea (KZT): {breakdown['total_korea_kzt']:,.2f}")

                print(f"\n  Kazakhstan Customs:")
                print(f"    Customs price (USD): ${breakdown['customs_price_usd']:,.2f}")
                print(f"    Customs price (KZT): {breakdown['customs_price_kzt']:,.2f}")
                print(f"    Customs duty (15%): {breakdown['customs_duty']:,.2f}")
                print(f"    Excise: {breakdown['excise']:,.2f}")
                print(f"    VAT (12%): {breakdown['vat']:,.2f}")
                print(f"    Utilization fee: {breakdown['utilization_fee']:,.2f}")
                print(f"    Registration fee: {breakdown['registration_fee']:,.2f}")
                print(f"    Total customs: {breakdown['total_customs']:,.2f}")

                print(f"\n  Company Commission:")
                print(f"    Commission (USD): ${breakdown['company_commission_usd']:,.0f}")
                print(f"    Commission (KZT): {breakdown['company_commission_kzt']:,.2f}")

                print(f"\n  Exchange Rates:")
                print(f"    USD/KRW: {breakdown['usd_krw_rate']:,.2f}")
                print(f"    KZT/KRW: {breakdown['kzt_krw_rate']:.4f}")
                print(f"    USD/KZT: {breakdown['usd_krw_rate'] / breakdown['kzt_krw_rate']:,.2f}")
        else:
            print(f"\n❌ Calculation failed!")
            print(f"  Error: {result.get('error', 'Unknown error')}")
    else:
        print(f"\n❌ API request failed!")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")

except Exception as e:
    print(f"\n❌ Exception occurred: {e}")

print("\n" + "=" * 80)
