"""
Комплексный тест для диагностики проблем с фильтрацией KBChaChaCha
Тестирует всю иерархию: производители → модели → поколения → конфигурации
"""

import asyncio
import sys
import json
import time
from typing import Dict, List, Any, Optional

# Добавляем путь к проекту
sys.path.append(".")

from services.kbchachacha_service import KBChaChaService
from schemas.kbchachacha import (
    KBMakersResponse,
    KBModelsResponse,
    KBGenerationsResponse,
    KBConfigsTrimsResponse,
    KBSearchFilters,
    FuelType,
)


class KBChaChaDebugger:
    """Класс для комплексной диагностики KBChaChaCha API"""

    def __init__(self):
        self.service = KBChaChaService()
        self.test_results = {
            "manufacturers": {},
            "models": {},
            "generations": {},
            "configs_trims": {},
            "cascade_test": {},
            "search_test": {},
            "summary": {},
        }

    def print_section(self, title: str, symbol: str = "="):
        """Красивый вывод секции"""
        print(f"\n{symbol * 80}")
        print(f"{title}")
        print(f"{symbol * 80}")

    def print_success(self, message: str):
        """Вывод успешного результата"""
        print(f"✅ {message}")

    def print_error(self, message: str):
        """Вывод ошибки"""
        print(f"❌ {message}")

    def print_warning(self, message: str):
        """Вывод предупреждения"""
        print(f"⚠️  {message}")

    def print_info(self, message: str):
        """Вывод информации"""
        print(f"ℹ️  {message}")

    async def test_manufacturers(self) -> Dict[str, Any]:
        """Тест 1: Загрузка производителей"""
        self.print_section("🚗 ТЕСТ 1: ПРОИЗВОДИТЕЛИ (MANUFACTURERS)")

        try:
            start_time = time.time()
            result = await self.service.get_manufacturers()
            end_time = time.time()

            test_result = {
                "success": result.success,
                "response_time": round(end_time - start_time, 2),
                "total_count": result.total_count,
                "domestic_count": len(result.domestic) if result.domestic else 0,
                "imported_count": len(result.imported) if result.imported else 0,
                "errors": [],
            }

            if result.success:
                self.print_success(
                    f"Производители загружены за {test_result['response_time']}с"
                )
                self.print_info(f"Общее количество: {test_result['total_count']}")
                self.print_info(f"Отечественные: {test_result['domestic_count']}")
                self.print_info(f"Импортные: {test_result['imported_count']}")

                # Проверяем структуру данных
                if result.domestic:
                    sample_domestic = result.domestic[0]
                    self.print_info(
                        f"Пример отечественного: {sample_domestic.makerName} (код: {sample_domestic.makerCode})"
                    )

                if result.imported:
                    sample_imported = result.imported[0]
                    self.print_info(
                        f"Пример импортного: {sample_imported.makerName} (код: {sample_imported.makerCode})"
                    )

                # Сохраняем коды для дальнейшего тестирования
                test_result["sample_domestic_code"] = (
                    result.domestic[0].makerCode if result.domestic else None
                )
                test_result["sample_imported_code"] = (
                    result.imported[0].makerCode if result.imported else None
                )

            else:
                self.print_error("Не удалось загрузить производителей")
                test_result["errors"].append(result.meta.get("error", "Unknown error"))

            self.test_results["manufacturers"] = test_result
            return test_result

        except Exception as e:
            self.print_error(f"Исключение при тестировании производителей: {str(e)}")
            test_result = {"success": False, "errors": [str(e)]}
            self.test_results["manufacturers"] = test_result
            return test_result

    async def test_models(self, manufacturer_codes: List[str]) -> Dict[str, Any]:
        """Тест 2: Загрузка моделей для производителей"""
        self.print_section("🚙 ТЕСТ 2: МОДЕЛИ (MODELS)")

        test_result = {"success": True, "tested_manufacturers": [], "errors": []}

        for maker_code in manufacturer_codes:
            try:
                self.print_info(f"Тестирую модели для производителя: {maker_code}")

                start_time = time.time()
                result = await self.service.get_models(maker_code)
                end_time = time.time()

                manufacturer_test = {
                    "maker_code": maker_code,
                    "success": result.success,
                    "response_time": round(end_time - start_time, 2),
                    "total_count": result.total_count,
                    "models_count": len(result.models) if result.models else 0,
                }

                if result.success:
                    self.print_success(
                        f"Модели для {maker_code}: {manufacturer_test['models_count']} моделей за {manufacturer_test['response_time']}с"
                    )

                    # Проверяем структуру данных
                    if result.models:
                        sample_model = result.models[0]
                        self.print_info(
                            f"Пример модели: {sample_model.modelName} (код: {sample_model.carCode})"
                        )
                        manufacturer_test["sample_model_code"] = sample_model.carCode
                        manufacturer_test["sample_model_name"] = sample_model.modelName

                else:
                    self.print_error(f"Не удалось загрузить модели для {maker_code}")
                    manufacturer_test["error"] = result.meta.get(
                        "error", "Unknown error"
                    )
                    test_result["success"] = False
                    test_result["errors"].append(
                        f"Maker {maker_code}: {manufacturer_test['error']}"
                    )

                test_result["tested_manufacturers"].append(manufacturer_test)

            except Exception as e:
                self.print_error(
                    f"Исключение при тестировании моделей для {maker_code}: {str(e)}"
                )
                test_result["success"] = False
                test_result["errors"].append(f"Maker {maker_code}: {str(e)}")

        self.test_results["models"] = test_result
        return test_result

    async def test_generations(self, car_codes: List[str]) -> Dict[str, Any]:
        """Тест 3: Загрузка поколений для моделей"""
        self.print_section("🔧 ТЕСТ 3: ПОКОЛЕНИЯ (GENERATIONS)")

        test_result = {"success": True, "tested_models": [], "errors": []}

        for car_code in car_codes:
            try:
                self.print_info(f"Тестирую поколения для модели: {car_code}")

                start_time = time.time()
                result = await self.service.get_generations(car_code)
                end_time = time.time()

                model_test = {
                    "car_code": car_code,
                    "success": result.success,
                    "response_time": round(end_time - start_time, 2),
                    "total_count": result.total_count,
                    "generations_count": (
                        len(result.generations) if result.generations else 0
                    ),
                }

                if result.success:
                    self.print_success(
                        f"Поколения для {car_code}: {model_test['generations_count']} поколений за {model_test['response_time']}с"
                    )

                    # Проверяем структуру данных
                    if result.generations:
                        sample_generation = result.generations[0]
                        self.print_info(
                            f"Пример поколения: {sample_generation.codeModel} - {sample_generation.nameModel}"
                        )
                        model_test["sample_generation_code"] = (
                            sample_generation.codeModel
                        )
                        model_test["sample_generation_name"] = (
                            sample_generation.nameModel
                        )

                else:
                    self.print_error(f"Не удалось загрузить поколения для {car_code}")
                    model_test["error"] = result.meta.get("error", "Unknown error")
                    test_result["success"] = False
                    test_result["errors"].append(
                        f"Car {car_code}: {model_test['error']}"
                    )

                test_result["tested_models"].append(model_test)

            except Exception as e:
                self.print_error(
                    f"Исключение при тестировании поколений для {car_code}: {str(e)}"
                )
                test_result["success"] = False
                test_result["errors"].append(f"Car {car_code}: {str(e)}")

        self.test_results["generations"] = test_result
        return test_result

    async def test_configs_trims(self, car_codes: List[str]) -> Dict[str, Any]:
        """Тест 4: Загрузка конфигураций и комплектаций"""
        self.print_section("⚙️ ТЕСТ 4: КОНФИГУРАЦИИ И КОМПЛЕКТАЦИИ (CONFIGS-TRIMS)")

        test_result = {"success": True, "tested_models": [], "errors": []}

        for car_code in car_codes:
            try:
                self.print_info(f"Тестирую конфигурации для модели: {car_code}")

                start_time = time.time()
                result = await self.service.get_configs_trims(car_code)
                end_time = time.time()

                model_test = {
                    "car_code": car_code,
                    "success": result.success,
                    "response_time": round(end_time - start_time, 2),
                    "total_count": result.total_count,
                    "configurations_count": (
                        len(result.configurations) if result.configurations else 0
                    ),
                    "trims_count": len(result.trims) if result.trims else 0,
                }

                if result.success:
                    self.print_success(
                        f"Конфигурации для {car_code}: {model_test['configurations_count']} конфигураций, {model_test['trims_count']} комплектаций за {model_test['response_time']}с"
                    )

                    # Проверяем структуру данных
                    if result.configurations:
                        sample_config = result.configurations[0]
                        self.print_info(
                            f"Пример конфигурации: {sample_config.codeModel} - {sample_config.nameModel}"
                        )

                    if result.trims:
                        sample_trim = result.trims[0]
                        self.print_info(
                            f"Пример комплектации: {sample_trim.codeModel} - {sample_trim.nameModel}"
                        )

                else:
                    self.print_error(
                        f"Не удалось загрузить конфигурации для {car_code}"
                    )
                    model_test["error"] = result.meta.get("error", "Unknown error")
                    test_result["success"] = False
                    test_result["errors"].append(
                        f"Car {car_code}: {model_test['error']}"
                    )

                test_result["tested_models"].append(model_test)

            except Exception as e:
                self.print_error(
                    f"Исключение при тестировании конфигураций для {car_code}: {str(e)}"
                )
                test_result["success"] = False
                test_result["errors"].append(f"Car {car_code}: {str(e)}")

        self.test_results["configs_trims"] = test_result
        return test_result

    async def test_cascade_flow(self) -> Dict[str, Any]:
        """Тест 5: Каскадная загрузка данных"""
        self.print_section("🔄 ТЕСТ 5: КАСКАДНАЯ ЗАГРУЗКА (CASCADE FLOW)")

        test_result = {"success": True, "flow_steps": [], "errors": []}

        try:
            # Шаг 1: Загружаем производителей
            self.print_info("Шаг 1: Загружаем производителей...")
            manufacturers_result = await self.service.get_manufacturers()

            if not manufacturers_result.success:
                test_result["success"] = False
                test_result["errors"].append("Не удалось загрузить производителей")
                return test_result

            # Берем первого отечественного производителя
            if not manufacturers_result.domestic:
                test_result["success"] = False
                test_result["errors"].append("Нет отечественных производителей")
                return test_result

            selected_maker = manufacturers_result.domestic[0]
            self.print_success(
                f"Выбран производитель: {selected_maker.makerName} (код: {selected_maker.makerCode})"
            )

            # Шаг 2: Загружаем модели для выбранного производителя
            self.print_info(
                f"Шаг 2: Загружаем модели для {selected_maker.makerName}..."
            )
            models_result = await self.service.get_models(selected_maker.makerCode)

            if not models_result.success:
                test_result["success"] = False
                test_result["errors"].append(
                    f"Не удалось загрузить модели для {selected_maker.makerName}"
                )
                return test_result

            if not models_result.models:
                test_result["success"] = False
                test_result["errors"].append(
                    f"Нет моделей для {selected_maker.makerName}"
                )
                return test_result

            selected_model = models_result.models[0]
            self.print_success(
                f"Выбрана модель: {selected_model.modelName} (код: {selected_model.carCode})"
            )

            # Шаг 3: Загружаем поколения для выбранной модели
            self.print_info(
                f"Шаг 3: Загружаем поколения для {selected_model.modelName}..."
            )
            generations_result = await self.service.get_generations(
                selected_model.carCode
            )

            if not generations_result.success:
                test_result["success"] = False
                test_result["errors"].append(
                    f"Не удалось загрузить поколения для {selected_model.modelName}"
                )
                return test_result

            self.print_success(
                f"Поколения загружены: {len(generations_result.generations) if generations_result.generations else 0} поколений"
            )

            # Шаг 4: Загружаем конфигурации для выбранной модели
            self.print_info(
                f"Шаг 4: Загружаем конфигурации для {selected_model.modelName}..."
            )
            configs_result = await self.service.get_configs_trims(
                selected_model.carCode
            )

            if not configs_result.success:
                test_result["success"] = False
                test_result["errors"].append(
                    f"Не удалось загрузить конфигурации для {selected_model.modelName}"
                )
                return test_result

            self.print_success(
                f"Конфигурации загружены: {len(configs_result.configurations) if configs_result.configurations else 0} конфигураций, {len(configs_result.trims) if configs_result.trims else 0} комплектаций"
            )

            test_result["flow_steps"] = [
                {
                    "step": "manufacturers",
                    "success": True,
                    "selected": f"{selected_maker.makerName} ({selected_maker.makerCode})",
                },
                {
                    "step": "models",
                    "success": True,
                    "selected": f"{selected_model.modelName} ({selected_model.carCode})",
                },
                {
                    "step": "generations",
                    "success": True,
                    "count": (
                        len(generations_result.generations)
                        if generations_result.generations
                        else 0
                    ),
                },
                {
                    "step": "configs_trims",
                    "success": True,
                    "configs_count": (
                        len(configs_result.configurations)
                        if configs_result.configurations
                        else 0
                    ),
                    "trims_count": (
                        len(configs_result.trims) if configs_result.trims else 0
                    ),
                },
            ]

            self.print_success("Каскадная загрузка завершена успешно!")

        except Exception as e:
            self.print_error(f"Исключение при каскадной загрузке: {str(e)}")
            test_result["success"] = False
            test_result["errors"].append(str(e))

        self.test_results["cascade_test"] = test_result
        return test_result

    async def test_search_functionality(self) -> Dict[str, Any]:
        """Тест 6: Функциональность поиска"""
        self.print_section("🔍 ТЕСТ 6: ФУНКЦИОНАЛЬНОСТЬ ПОИСКА")

        test_result = {"success": True, "search_tests": [], "errors": []}

        # Тест 1: Базовый поиск
        try:
            self.print_info("Тест 1: Базовый поиск (первая страница)")
            basic_filters = KBSearchFilters(page=1, sort="-orderDate")
            result = await self.service.search_cars(basic_filters)

            basic_test = {
                "test_name": "basic_search",
                "success": result.success,
                "total_count": result.total_count,
                "listings_count": len(result.listings) if result.listings else 0,
            }

            if result.success:
                self.print_success(
                    f"Базовый поиск: {basic_test['total_count']} автомобилей, {basic_test['listings_count']} на странице"
                )
            else:
                self.print_error("Базовый поиск не удался")
                basic_test["error"] = result.meta.get("error", "Unknown error")
                test_result["success"] = False
                test_result["errors"].append(f"Basic search: {basic_test['error']}")

            test_result["search_tests"].append(basic_test)

        except Exception as e:
            self.print_error(f"Исключение при базовом поиске: {str(e)}")
            test_result["success"] = False
            test_result["errors"].append(f"Basic search: {str(e)}")

        # Тест 2: Поиск по производителю
        try:
            self.print_info("Тест 2: Поиск по производителю (현대)")
            hyundai_filters = KBSearchFilters(page=1, makerCode="101")
            result = await self.service.search_cars(hyundai_filters)

            hyundai_test = {
                "test_name": "manufacturer_search",
                "success": result.success,
                "total_count": result.total_count,
                "listings_count": len(result.listings) if result.listings else 0,
            }

            if result.success:
                self.print_success(
                    f"Поиск по 현대: {hyundai_test['total_count']} автомобилей, {hyundai_test['listings_count']} на странице"
                )
            else:
                self.print_error("Поиск по производителю не удался")
                hyundai_test["error"] = result.meta.get("error", "Unknown error")
                test_result["success"] = False
                test_result["errors"].append(
                    f"Manufacturer search: {hyundai_test['error']}"
                )

            test_result["search_tests"].append(hyundai_test)

        except Exception as e:
            self.print_error(f"Исключение при поиске по производителю: {str(e)}")
            test_result["success"] = False
            test_result["errors"].append(f"Manufacturer search: {str(e)}")

        # Тест 3: Комплексный поиск с фильтрами
        try:
            self.print_info("Тест 3: Комплексный поиск с фильтрами")
            complex_filters = KBSearchFilters(
                page=1,
                makerCode="101",  # 현대
                year_from=2020,
                year_to=2024,
                price_to=3000,  # До 3000만원
                fuel_types=[FuelType.GASOLINE, FuelType.HYBRID_GASOLINE],
            )
            result = await self.service.search_cars(complex_filters)

            complex_test = {
                "test_name": "complex_search",
                "success": result.success,
                "total_count": result.total_count,
                "listings_count": len(result.listings) if result.listings else 0,
                "filters": {
                    "manufacturer": "현대",
                    "year_range": "2020-2024",
                    "max_price": "3000만원",
                    "fuel_types": ["gasoline", "hybrid_gasoline"],
                },
            }

            if result.success:
                self.print_success(
                    f"Комплексный поиск: {complex_test['total_count']} автомобилей, {complex_test['listings_count']} на странице"
                )
            else:
                self.print_error("Комплексный поиск не удался")
                complex_test["error"] = result.meta.get("error", "Unknown error")
                test_result["success"] = False
                test_result["errors"].append(f"Complex search: {complex_test['error']}")

            test_result["search_tests"].append(complex_test)

        except Exception as e:
            self.print_error(f"Исключение при комплексном поиске: {str(e)}")
            test_result["success"] = False
            test_result["errors"].append(f"Complex search: {str(e)}")

        self.test_results["search_test"] = test_result
        return test_result

    def generate_summary(self):
        """Генерация итогового отчета"""
        self.print_section("📊 ИТОГОВЫЙ ОТЧЕТ", "=")

        # Подсчет успешных тестов
        total_tests = 0
        passed_tests = 0

        for test_name, test_result in self.test_results.items():
            if test_name == "summary":
                continue

            total_tests += 1
            if test_result.get("success", False):
                passed_tests += 1
                self.print_success(f"{test_name.upper()}: УСПЕХ")
            else:
                self.print_error(f"{test_name.upper()}: ОШИБКА")
                errors = test_result.get("errors", [])
                for error in errors:
                    print(f"    • {error}")

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        self.print_section("🎯 РЕЗУЛЬТАТ", "-")
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {passed_tests}")
        print(f"Не удалось: {total_tests - passed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")

        if success_rate == 100:
            self.print_success("🚀 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
            print("   Frontend должен корректно работать с API")
        elif success_rate >= 80:
            self.print_warning("⚠️ ЕСТЬ МЕЛКИЕ ПРОБЛЕМЫ")
            print("   Основная функциональность работает, но есть исправления")
        else:
            self.print_error("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ")
            print("   Требуются серьезные исправления перед использованием")

        # Рекомендации для frontend
        self.print_section("💡 РЕКОМЕНДАЦИИ ДЛЯ FRONTEND", "-")

        if self.test_results.get("manufacturers", {}).get("success"):
            print("✅ Производители: Можно использовать /api/kbchachacha/manufacturers")
        else:
            print("❌ Производители: Проблемы с загрузкой")

        if self.test_results.get("models", {}).get("success"):
            print("✅ Модели: Можно использовать /api/kbchachacha/models/{maker_code}")
        else:
            print("❌ Модели: Проблемы с загрузкой")

        if self.test_results.get("generations", {}).get("success"):
            print(
                "✅ Поколения: Можно использовать /api/kbchachacha/generations/{car_code}"
            )
        else:
            print("❌ Поколения: Проблемы с загрузкой")

        if self.test_results.get("configs_trims", {}).get("success"):
            print(
                "✅ Конфигурации: Можно использовать /api/kbchachacha/configs-trims/{car_code}"
            )
        else:
            print("❌ Конфигурации: Проблемы с загрузкой")

        if self.test_results.get("search_test", {}).get("success"):
            print("✅ Поиск: Можно использовать /api/kbchachacha/search с фильтрами")
        else:
            print("❌ Поиск: Проблемы с функциональностью")

        # Сохраняем итоговый отчет
        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "timestamp": time.time(),
            "status": (
                "SUCCESS"
                if success_rate == 100
                else "PARTIAL" if success_rate >= 80 else "FAILURE"
            ),
        }

        return self.test_results["summary"]

    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ KBCHACHACHA")
        print("=" * 80)

        # Тест 1: Производители
        manufacturers_result = await self.test_manufacturers()

        # Получаем коды производителей для дальнейшего тестирования
        test_manufacturer_codes = []
        if manufacturers_result.get("success"):
            if manufacturers_result.get("sample_domestic_code"):
                test_manufacturer_codes.append(
                    manufacturers_result["sample_domestic_code"]
                )
            if manufacturers_result.get("sample_imported_code"):
                test_manufacturer_codes.append(
                    manufacturers_result["sample_imported_code"]
                )

        # Тест 2: Модели
        models_result = await self.test_models(
            test_manufacturer_codes[:2]
        )  # Тестируем только первые 2

        # Получаем коды моделей для дальнейшего тестирования
        test_car_codes = []
        if models_result.get("success"):
            for manufacturer_test in models_result.get("tested_manufacturers", []):
                if manufacturer_test.get("sample_model_code"):
                    test_car_codes.append(manufacturer_test["sample_model_code"])

        # Тест 3: Поколения
        await self.test_generations(test_car_codes[:3])  # Тестируем только первые 3

        # Тест 4: Конфигурации
        await self.test_configs_trims(test_car_codes[:3])  # Тестируем только первые 3

        # Тест 5: Каскадная загрузка
        await self.test_cascade_flow()

        # Тест 6: Поиск
        await self.test_search_functionality()

        # Генерация итогового отчета
        summary = self.generate_summary()

        return summary


async def main():
    """Главная функция"""
    debugger = KBChaChaDebugger()

    try:
        summary = await debugger.run_all_tests()

        # Сохраняем полный отчет в файл для анализа
        with open("kbchachacha_test_report.json", "w", encoding="utf-8") as f:
            json.dump(debugger.test_results, f, ensure_ascii=False, indent=2)

        print(f"\n📝 Полный отчет сохранен в: kbchachacha_test_report.json")

        # Возвращаем код выхода
        return 0 if summary["status"] == "SUCCESS" else 1

    except Exception as e:
        print(f"❌ Критическая ошибка при тестировании: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
