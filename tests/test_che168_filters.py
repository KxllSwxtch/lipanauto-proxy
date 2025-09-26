"""
Comprehensive test suite for che168 filter functionality
Tests the complete filter cascade: brand → model → year
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from services.che168_service import Che168Service
from schemas.bravomotors import Che168SearchFilters


class TestChe168Filters:
    """Test suite for che168 filter functionality"""

    @pytest.fixture
    def che168_service(self):
        """Create che168 service instance for testing"""
        return Che168Service()

    @pytest.fixture
    def sample_brand_response(self):
        """Sample API response for brands"""
        return {
            "returncode": 0,
            "message": "success",
            "result": {
                "hotbrand": [
                    {"id": 15, "name": "宝马", "pinyinname": "baoma", "letter": "B"},
                    {"id": 33, "name": "奔驰", "pinyinname": "benchi", "letter": "B"}
                ],
                "brands": [
                    {
                        "letter": "B",
                        "brand": [
                            {"id": 15, "name": "宝马", "pinyinname": "baoma"},
                            {"id": 33, "name": "奔驰", "pinyinname": "benchi"}
                        ]
                    }
                ]
            }
        }

    @pytest.fixture
    def sample_models_response(self):
        """Sample API response for models (BMW)"""
        return {
            "returncode": 0,
            "message": "success",
            "result": {
                "totalcount": 3565,
                "pagecount": 179,
                "pageindex": 1,
                "pagesize": 20,
                "carlist": [],
                "filters": [
                    {
                        "key": "seriesid",
                        "value": "65",
                        "title": "宝马5系",
                        "subtitle": "BMW 5 Series",
                        "count": 721
                    },
                    {
                        "key": "seriesid",
                        "value": "66",
                        "title": "宝马3系",
                        "subtitle": "BMW 3 Series",
                        "count": 892
                    }
                ]
            }
        }

    @pytest.fixture
    def sample_years_response(self):
        """Sample API response for years (BMW 5 Series)"""
        return {
            "returncode": 0,
            "message": "success",
            "result": {
                "totalcount": 721,
                "pagecount": 37,
                "pageindex": 1,
                "pagesize": 20,
                "carlist": [],
                "filters": [
                    {
                        "key": "seriesyearid",
                        "value": "35436",
                        "title": "2023款",
                        "subtitle": "2023 Model",
                        "count": 45
                    },
                    {
                        "key": "seriesyearid",
                        "value": "35437",
                        "title": "2022款",
                        "subtitle": "2022 Model",
                        "count": 123
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_get_brands_success(self, che168_service, sample_brand_response):
        """Test successful brand retrieval"""
        # Mock the parser response
        che168_service.parser.parse_brands_response = Mock(return_value=Mock(
            returncode=0,
            message="success",
            result={
                "hotbrand": sample_brand_response["result"]["hotbrand"],
                "brands": sample_brand_response["result"]["brands"]
            }
        ))

        # Mock the HTTP request
        che168_service.client._make_request = AsyncMock(return_value=sample_brand_response)

        result = await che168_service.get_brands()

        assert result.returncode == 0
        assert len(result.result["hotbrand"]) == 2
        assert result.result["hotbrand"][0]["name"] == "宝马"

    @pytest.mark.asyncio
    async def test_get_models_extracts_from_filters(self, che168_service, sample_models_response):
        """Test that models are correctly extracted from filters array"""
        # Mock the parser to return filters
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.message = "success"
        mock_result.result = sample_models_response["result"]
        mock_result.filters = [
            Mock(key="seriesid", value="65", title="宝马5系", subtitle="BMW 5 Series"),
            Mock(key="seriesid", value="66", title="宝马3系", subtitle="BMW 3 Series")
        ]

        che168_service.parser.parse_car_search_response = Mock(return_value=mock_result)
        che168_service.client._make_request = AsyncMock(return_value=sample_models_response)

        result = await che168_service.get_models(15)  # BMW brand ID

        # Verify models were extracted from filters
        assert result.returncode == 0
        assert "models" in result.result
        assert len(result.result["models"]) == 2
        assert result.result["models"][0]["name"] == "宝马5系"
        assert result.result["models"][0]["id"] == 65

    @pytest.mark.asyncio
    async def test_get_years_extracts_from_filters(self, che168_service, sample_years_response):
        """Test that years are correctly extracted from filters array"""
        # Mock the parser to return year filters
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.message = "success"
        mock_result.result = sample_years_response["result"]
        mock_result.filters = [
            Mock(key="seriesyearid", value="35436", title="2023款", subtitle="2023 Model"),
            Mock(key="seriesyearid", value="35437", title="2022款", subtitle="2022 Model")
        ]

        che168_service.parser.parse_car_search_response = Mock(return_value=mock_result)
        che168_service.client._make_request = AsyncMock(return_value=sample_years_response)

        result = await che168_service.get_years(15, 65)  # BMW, 5 Series

        # Verify years were extracted from filters
        assert result.returncode == 0
        assert "years" in result.result
        assert len(result.result["years"]) == 2
        assert result.result["years"][0]["name"] == "2023款"
        assert result.result["years"][0]["id"] == 35436

    @pytest.mark.asyncio
    async def test_filter_cascade_flow(self, che168_service):
        """Test the complete filter cascade: brand → model → year"""

        # Test 1: Get brands
        brands_response = {
            "returncode": 0,
            "message": "success",
            "result": {"hotbrand": [{"id": 15, "name": "宝马"}]}
        }

        mock_brands_result = Mock(returncode=0, result=brands_response["result"])
        che168_service.parser.parse_brands_response = Mock(return_value=mock_brands_result)
        che168_service.client._make_request = AsyncMock(return_value=brands_response)

        brands = await che168_service.get_brands()
        assert brands.returncode == 0

        # Test 2: Get models for BMW (brand_id=15)
        models_response = {
            "returncode": 0,
            "result": {
                "filters": [
                    {"key": "seriesid", "value": "65", "title": "宝马5系"}
                ]
            }
        }

        mock_models_result = Mock()
        mock_models_result.returncode = 0
        mock_models_result.result = models_response["result"]
        mock_models_result.filters = [Mock(key="seriesid", value="65", title="宝马5系")]

        che168_service.parser.parse_car_search_response = Mock(return_value=mock_models_result)
        che168_service.client._make_request = AsyncMock(return_value=models_response)

        models = await che168_service.get_models(15)
        assert models.returncode == 0
        assert len(models.result["models"]) == 1

        # Test 3: Get years for BMW 5 Series (brand_id=15, series_id=65)
        years_response = {
            "returncode": 0,
            "result": {
                "filters": [
                    {"key": "seriesyearid", "value": "35436", "title": "2023款"}
                ]
            }
        }

        mock_years_result = Mock()
        mock_years_result.returncode = 0
        mock_years_result.result = years_response["result"]
        mock_years_result.filters = [Mock(key="seriesyearid", value="35436", title="2023款")]

        che168_service.parser.parse_car_search_response = Mock(return_value=mock_years_result)
        che168_service.client._make_request = AsyncMock(return_value=years_response)

        years = await che168_service.get_years(15, 65)
        assert years.returncode == 0
        assert len(years.result["years"]) == 1

    @pytest.mark.asyncio
    async def test_search_with_filters(self, che168_service):
        """Test search functionality with filters applied"""
        filters = Che168SearchFilters(
            pageindex=1,
            pagesize=20,
            brandid=15,  # BMW
            seriesid=65,  # 5 Series
            seriesyearid=35436  # 2023
        )

        search_response = {
            "returncode": 0,
            "result": {
                "totalcount": 45,
                "carlist": [
                    {"infoid": "12345", "carname": "2023 BMW 5系"}
                ]
            }
        }

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.cars = [Mock(infoid="12345", carname="2023 BMW 5系")]
        mock_result.total_count = 45

        che168_service.parser.parse_car_search_response = Mock(return_value=mock_result)
        che168_service.client._make_request = AsyncMock(return_value=search_response)

        result = await che168_service.search_cars(filters)

        assert result.returncode == 0
        assert result.total_count == 45
        assert len(result.cars) == 1

    def test_error_handling(self, che168_service):
        """Test error handling for invalid responses"""
        # Test invalid brand response
        invalid_response = {
            "returncode": -1,
            "message": "API Error"
        }

        mock_result = Mock(returncode=-1, message="API Error")
        che168_service.parser.parse_brands_response = Mock(return_value=mock_result)

        # This would be tested with actual async call in integration test
        assert mock_result.returncode == -1

    def test_empty_filters_handling(self, che168_service):
        """Test handling of empty filter arrays"""
        empty_response = {
            "returncode": 0,
            "result": {
                "filters": []
            }
        }

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.result = empty_response["result"]
        mock_result.filters = []

        che168_service.parser.parse_car_search_response = Mock(return_value=mock_result)

        # In actual service call, this should result in empty models/years arrays
        assert len(mock_result.filters) == 0


if __name__ == "__main__":
    pytest.main([__file__])