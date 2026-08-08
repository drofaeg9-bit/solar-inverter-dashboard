from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_API_LANGUAGES = frozenset({"uk", "ru", "en"})
REGISTER_DESCRIPTION_TRANSLATIONS: dict[int, dict[str, str]] = {
    17: {
        "uk": "Старша складова версії протоколу. Разом із R18 утворює V<R17>.<R18/10 для двозначного R18>.",
        "ru": "Старшая составляющая версии протокола. Вместе с R18 образует V<R17>.<R18/10 для двузначного R18>.",
        "en": "Major protocol-version component. With R18 it forms V<R17>.<R18/10 when R18 has two digits>.",
    },
    18: {
        "uk": "Молодша закодована складова версії протоколу; читається разом із R17.",
        "ru": "Младшая закодированная составляющая версии протокола; читается вместе с R17.",
        "en": "Encoded minor protocol-version component; read together with R17.",
    },
    27: {
        "uk": "Старша складова версії ПЗ плати керування. Разом із R28 утворює відображувану версію.",
        "ru": "Старшая составляющая версии ПО платы управления. Вместе с R28 образует отображаемую версию.",
        "en": "Major control-board software-version component; combined with R28 for display.",
    },
    28: {
        "uk": "Молодша закодована складова версії ПЗ плати керування; читається разом із R27.",
        "ru": "Младшая закодированная составляющая версии ПО платы управления; читается вместе с R27.",
        "en": "Encoded minor control-board software-version component; read together with R27.",
    },
    58: {
        "uk": "Ідентифікатор сумісності протоколу, визначений картою V1.31.",
        "ru": "Идентификатор совместимости протокола, определённый картой V1.31.",
        "en": "Protocol compatibility identifier defined by the V1.31 map.",
    },
    65: {
        "uk": "Версія ПЗ: старші 8 біт — основна версія, молодші 8 біт — додаткова.",
        "ru": "Версия ПО: старшие 8 бит — основная версия, младшие 8 бит — дополнительная.",
        "en": "Firmware version: high 8 bits are the major version; low 8 bits are the minor version.",
    },
    66: {
        "uk": "Стан пошуку ID BMS: 0 — пошук; 1 — CAN; 2 — послідовний порт; 3 — віддалене блокування ID.",
        "ru": "Состояние поиска ID BMS: 0 — поиск; 1 — CAN; 2 — последовательный порт; 3 — удалённая фиксация ID.",
        "en": "BMS ID state: 0 searching; 1 locked by CAN; 2 locked by serial; 3 remotely locked.",
    },
    67: {
        "uk": "Код стану інвертора: 0 живлення; 1 ініціалізація; 2 очікування; 3 мережа; 4 PV; 5 батарея; 6 генератор; 7 несправність; 8 вимкнення; 9 заводський тест; 10 оновлення ПЗ.",
        "ru": "Код состояния инвертора: 0 питание; 1 инициализация; 2 ожидание; 3 сеть; 4 PV; 5 батарея; 6 генератор; 7 неисправность; 8 выключение; 9 заводской тест; 10 обновление ПО.",
        "en": "Inverter-state code: 0 power-on; 1 initialising; 2 standby; 3 grid; 4 PV; 5 battery; 6 generator; 7 fault; 8 shutdown; 9 factory test; 10 firmware upgrade.",
    },
    68: {
        "uk": "Упаковані стани: біти 0–1 мережа; 2–3 генератор; 4–5 PV1; 6–7 вихід; 8–10 батарея; 11–13 стадія заряджання; 14–15 PV2. Поточні підполя декодуються за значенням.",
        "ru": "Упакованные состояния: биты 0–1 сеть; 2–3 генератор; 4–5 PV1; 6–7 выход; 8–10 батарея; 11–13 стадия зарядки; 14–15 PV2. Текущие подполя декодируются по значению.",
        "en": "Packed states: bits 0–1 grid; 2–3 generator; 4–5 PV1; 6–7 output; 8–10 battery; 11–13 charging stage; 14–15 PV2. Current subfields are decoded from the value.",
    },
    69: {
        "uk": "Прапорці потоку: b0 мережа→випрямляч; b1 мережа→навантаження; b2 генератор→випрямляч; b3 генератор→навантаження; b4 PV→випрямляч; b5–7 випрямляч→батарея/інвертор/мережа; b8 батарея→інвертор; b9–10 інвертор→виходи; b12 Wi‑Fi; b13 економний; b15 тихий режим.",
        "ru": "Флаги потока: b0 сеть→выпрямитель; b1 сеть→нагрузка; b2 генератор→выпрямитель; b3 генератор→нагрузка; b4 PV→выпрямитель; b5–7 выпрямитель→батарея/инвертор/сеть; b8 батарея→инвертор; b9–10 инвертор→выходы; b12 Wi‑Fi; b13 экономичный; b15 тихий режим.",
        "en": "Flow flags: b0 grid→rectifier; b1 grid→load; b2 generator→rectifier; b3 generator→load; b4 PV→rectifier; b5–7 rectifier→battery/inverter/grid; b8 battery→inverter; b9–10 inverter→outputs; b12 Wi‑Fi; b13 economy; b15 silent mode.",
    },
    70: {
        "uk": "Код паралельної роботи: 0 один інвертор; 1 однофазна паралель; 2 фаза A/R; 3 фаза B/S; 4 фаза C/T трифазної системи.",
        "ru": "Код параллельной работы: 0 один инвертор; 1 однофазная параллель; 2 фаза A/R; 3 фаза B/S; 4 фаза C/T трёхфазной системы.",
        "en": "Parallel-operation code: 0 single unit; 1 single-phase parallel; 2 phase A/R; 3 phase B/S; 4 phase C/T of a three-phase system.",
    },
    71: {"uk": "Маска несправностей 1: b0 плавний запуск мережі; b1/2 перенапруга/низька напруга DC-шини; b3 надструм батареї; b4 перегрів; b5 перенапруга батареї; b6 плавний запуск батареї; b7 КЗ шини; b8–11 запуск/напруга/КЗ інвертора; b12 від’ємна потужність; b13 перевантаження; b14 невідповідність моделі; b15 завантажувач.", "ru": "Маска неисправностей 1: b0 плавный запуск сети; b1/2 перенапряжение/низкое напряжение DC-шины; b3 сверхток батареи; b4 перегрев; b5 перенапряжение батареи; b6 плавный запуск батареи; b7 КЗ шины; b8–11 запуск/напряжение/КЗ инвертора; b12 отрицательная мощность; b13 перегрузка; b14 несоответствие модели; b15 загрузчик.", "en": "Fault mask 1: b0 grid soft-start; b1/2 DC-bus over/undervoltage; b3 battery overcurrent; b4 overtemperature; b5 battery overvoltage; b6 battery soft-start; b7 bus short; b8–11 inverter start/voltage/short faults; b12 negative power; b13 overload; b14 model mismatch; b15 bootloader."},
    72: {"uk": "Маска несправностей 2: b0 запис ПЗ; b1 зворотна полярність PV; b2–8 помилки серійного номера, зв’язку, напруги, частоти, фази й синхронізації паралельної системи; b9 BMS; b10 MCU; b12 навантаження інвертора; b13 перенапруга PV.", "ru": "Маска неисправностей 2: b0 запись ПО; b1 обратная полярность PV; b2–8 ошибки серийного номера, связи, напряжения, частоты, фазы и синхронизации параллельной системы; b9 BMS; b10 MCU; b12 нагрузка инвертора; b13 перенапряжение PV.", "en": "Fault mask 2: b0 firmware flashing; b1 reversed PV; b2–8 parallel serial, communication, voltage, frequency, phase and synchronisation faults; b9 BMS; b10 MCU; b12 inverter load; b13 PV overvoltage."},
    73: {"uk": "Маска попереджень 1: b0–2 батарея не підключена/низька напруга; b3 КЗ зарядного; b5 перезаряд; b6 втрачено BMS; b8 вентилятор; b9 EEPROM; b10 перевантаження; b12 слабкий PV; b13 синхронізація паралелі; b14 відсутня фаза; b4, b7, b11, b15 зарезервовано.", "ru": "Маска предупреждений 1: b0–2 батарея не подключена/низкое напряжение; b3 КЗ зарядного; b5 перезаряд; b6 потеря BMS; b8 вентилятор; b9 EEPROM; b10 перегрузка; b12 слабый PV; b13 синхронизация параллели; b14 отсутствует фаза; b4, b7, b11, b15 зарезервированы.", "en": "Warning mask 1: b0–2 battery disconnected/low voltage; b3 charger short; b5 overcharge; b6 BMS lost; b8 fan; b9 EEPROM; b10 overload; b12 weak PV; b13 parallel sync; b14 phase missing; b4, b7, b11 and b15 reserved."},
    74: {"uk": "Маска попереджень 2: b0 зв’язок паралелі; b1 різниця мережі; b2 вимкнення за SOC; b3 низький SOC; b4 різниця батарей/немає батареї; b5 КЗ батареї; b6 низька стартова напруга; b7–9 перевантаження/напруга генератора; b10 зовнішній CT; b11 нестабільна мережа; b12 зв’язок лічильника.", "ru": "Маска предупреждений 2: b0 связь параллели; b1 разница сети; b2 выключение по SOC; b3 низкий SOC; b4 разница батарей/нет батареи; b5 КЗ батареи; b6 низкое стартовое напряжение; b7–9 перегрузка/напряжение генератора; b10 внешний CT; b11 нестабильная сеть; b12 связь счётчика.", "en": "Warning mask 2: b0 parallel communication; b1 grid mismatch; b2 SOC shutdown; b3 low SOC; b4 battery mismatch/disconnected; b5 battery short; b6 low startup voltage; b7–9 generator overload/voltage; b10 external CT; b11 unstable grid; b12 meter communication."},
    77: {"uk": "Режим і параметр переднього RGB-індикатора.", "ru": "Режим и параметр переднего RGB-индикатора.", "en": "Foreground RGB indicator mode and parameter."},
    80: {"uk": "Режим і параметр фонового RGB-індикатора.", "ru": "Режим и параметр фонового RGB-индикатора.", "en": "Background RGB indicator mode and parameter."},
    321: {"uk": "Поточний режим входу AC: APP, UPS або GEN.", "ru": "Текущий режим входа AC: APP, UPS или GEN.", "en": "Current AC input mode: APP, UPS, or GEN."},
    322: {"uk": "Поточна конфігурація паралельної роботи.", "ru": "Текущая конфигурация параллельной работы.", "en": "Current parallel-operation configuration."},
    323: {"uk": "Поточний порядок пріоритету джерел для виходу.", "ru": "Текущий порядок приоритета источников для выхода.", "en": "Current output-source priority order."},
    324: {"uk": "Поточний пріоритет джерела заряджання.", "ru": "Текущий приоритет источника зарядки.", "en": "Current charging-source priority."},
    325: {"uk": "Поточний стан автомата інвертора.", "ru": "Текущее состояние автомата инвертора.", "en": "Current inverter state-machine state."},
    375: {"uk": "Поточна стадія заряджання батареї.", "ru": "Текущая стадия зарядки батареи.", "en": "Current battery charging stage."},
    144: {"uk": "Зарезервоване поле сумісності стану зв’язку BMS.", "ru": "Зарезервированное поле совместимости состояния связи BMS.", "en": "Reserved BMS communication-status compatibility field."},
    145: {"uk": "Зарезервоване поле сумісності стану мережі літієвих батарей.", "ru": "Зарезервированное поле совместимости состояния сети литиевых батарей.", "en": "Reserved lithium-battery networking-status compatibility field."},
    146: {"uk": "Бітова маска несправностей BMS; окремі біти V1.31 не визначає.", "ru": "Битовая маска неисправностей BMS; отдельные биты V1.31 не определяет.", "en": "BMS fault bit mask; V1.31 does not define individual bits."},
    147: {"uk": "Бітова маска попереджень BMS; окремі біти V1.31 не визначає.", "ru": "Битовая маска предупреждений BMS; отдельные биты V1.31 не определяет.", "en": "BMS warning bit mask; V1.31 does not define individual bits."},
    148: {"uk": "SOH батареї для моделей PWR2KH/PWR4KL.", "ru": "SOH батареи для моделей PWR2KH/PWR4KL.", "en": "Battery SOH for PWR2KH/PWR4KL models."},
    149: {"uk": "Зворотна потужність батареї для моделей PWR2KH/PWR4KL.", "ru": "Обратная мощность батареи для моделей PWR2KH/PWR4KL.", "en": "Reverse battery power for PWR2KH/PWR4KL models."},
    150: {"uk": "Зворотна активна потужність мережі для моделей PWR2KH/PWR4KL.", "ru": "Обратная активная мощность сети для моделей PWR2KH/PWR4KL.", "en": "Reverse grid active power for PWR2KH/PWR4KL models."},
    401: {"uk": "Код протоколу зв’язку BMS; V1.31 не містить таблиці його значень.", "ru": "Код протокола связи BMS; V1.31 не содержит таблицы его значений.", "en": "BMS communication-protocol code; V1.31 provides no value table."},
    402: {"uk": "Ідентифікатор пакета BMS.", "ru": "Идентификатор пакета BMS.", "en": "BMS packet identifier."},
    403: {"uk": "Стан зв’язку BMS: 0 — пошук ID; 1 — ID віддалено заблоковано; 2 — ID заблоковано.", "ru": "Состояние связи BMS: 0 — поиск ID; 1 — ID удалённо заблокирован; 2 — ID заблокирован.", "en": "BMS communication state: 0 searching for ID; 1 ID remotely locked; 2 ID locked."},
    414: {"uk": "Зарезервований поріг попередження низького SOC; не використовується згідно з V1.31.", "ru": "Зарезервированный порог предупреждения низкого SOC; не используется согласно V1.31.", "en": "Reserved low-SOC warning threshold; unused according to V1.31."},
    418: {"uk": "Бітова маска попереджень BMS; окремі біти V1.31 не визначає.", "ru": "Битовая маска предупреждений BMS; отдельные биты V1.31 не определяет.", "en": "BMS warning bit mask; V1.31 does not define individual bits."},
    419: {"uk": "Бітова маска помилок BMS; окремі біти V1.31 не визначає.", "ru": "Битовая маска ошибок BMS; отдельные биты V1.31 не определяет.", "en": "BMS error bit mask; V1.31 does not define individual bits."},
    529: {"uk": "Фактично застосований пріоритет вихідного джерела.", "ru": "Фактически применённый приоритет выходного источника.", "en": "Output-source priority currently applied."},
    530: {"uk": "Фактично застосований режим входу AC.", "ru": "Фактически применённый режим входа AC.", "en": "AC input mode currently applied."},
    802: {"uk": "0 — вентилятор працює нормально; інше значення — зупинка або блокування.", "ru": "0 — вентилятор работает нормально; другое значение — остановка или блокировка.", "en": "0 means normal fan operation; another value indicates a stop or stall."},
}
DATA_TRANSLATIONS_PATH = (
    Path(__file__).resolve().parents[1] / "web" / "data" / "data-translations.json"
)
with DATA_TRANSLATIONS_PATH.open(encoding="utf-8") as translation_file:
    DATA_TRANSLATIONS: dict[str, dict[str, str]] = json.load(translation_file)


def resolve_api_language(explicit: str = "", accept_language: str = "") -> str:
    """Resolve an API language from ?lang first, then Accept-Language."""
    requested = explicit.strip().lower().replace("_", "-").split("-", 1)[0]
    if requested in SUPPORTED_API_LANGUAGES:
        return requested
    preferences: list[tuple[float, int, str]] = []
    for position, item in enumerate(accept_language.split(",")):
        language_part, *parameters = item.strip().split(";")
        language = language_part.strip().lower().replace("_", "-").split("-", 1)[0]
        if language not in SUPPORTED_API_LANGUAGES:
            continue
        quality = 1.0
        for parameter in parameters:
            name, separator, value = parameter.strip().partition("=")
            if separator and name.lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if quality > 0:
            preferences.append((quality, -position, language))
    return max(preferences, default=(0.0, 0, "uk"))[2]


def localize_api_text(value: Any, language: str) -> Any:
    """Translate known user-facing API text while preserving raw values."""
    if language == "uk" or not isinstance(value, str) or not value:
        return value
    translation = DATA_TRANSLATIONS.get(value, {}).get(language)
    if translation:
        return translation
    if value.startswith("Регістр ") and value[8:].isdigit():
        prefix = "Регистр" if language == "ru" else "Register"
        return f"{prefix} {value[8:]}"
    return value


def localize_api_status(status: dict[str, Any], language: str) -> dict[str, Any]:
    """Return a localized copy of a nested status object."""
    localized = dict(status)
    if "error" in localized:
        localized["error_source"] = localized["error"]
        localized["error"] = localize_api_text(localized["error"], language)
    return localized


def register_description(
    register: int,
    name: str,
    unit: str,
    scale: float,
    signed: bool,
    language: str,
) -> str:
    """Return a localized V1.31 description for every exposed register."""
    language = language if language in SUPPORTED_API_LANGUAGES else "uk"
    if 1 <= register <= 10:
        first_character = (register - 1) * 2 + 1
        last_character = first_character + 1
        return {
            "uk": f"Слово серійного номера: ASCII-символи {first_character}–{last_character}. R1–R10 з’єднуються по старшому, потім молодшому байту в повний ідентифікатор; 0x00 означає порожнє доповнення або кінець.",
            "ru": f"Слово серийного номера: ASCII-символы {first_character}–{last_character}. R1–R10 объединяются по старшему, затем младшему байту в полный идентификатор; 0x00 означает пустое заполнение или конец.",
            "en": f"Serial-number word containing ASCII characters {first_character}–{last_character}. Join R1–R10 high byte then low byte to form the full identifier; 0x00 is padding or the end.",
        }[language]
    specific = REGISTER_DESCRIPTION_TRANSLATIONS.get(register, {}).get(language)
    if specific:
        return specific
    if name == "Резерв":
        return {
            "uk": "Поле зарезервовано картою V1.31; його значення не слід інтерпретувати.",
            "ru": "Поле зарезервировано картой V1.31; его значение не следует интерпретировать.",
            "en": "Reserved by the V1.31 map; do not interpret its value.",
        }[language]
    localized_name = str(localize_api_text(name, language))
    if unit:
        sign_note = {
            "uk": " зі знаком" if signed else "",
            "ru": " со знаком" if signed else "",
            "en": " signed" if signed else "",
        }[language]
        return {
            "uk": f"Вимірюване значення «{localized_name}»{sign_note}; API = сире значення × {scale:g} {unit}.",
            "ru": f"Измеряемое значение «{localized_name}»{sign_note}; API = сырое значение × {scale:g} {unit}.",
            "en": f"Measured value “{localized_name}”{sign_note}; API = raw value × {scale:g} {unit}.",
        }[language]
    return {
        "uk": f"Поле «{localized_name}» з карти Modbus V1.31; поточний код розшифровується нижче, якщо таблиця значень визначена.",
        "ru": f"Поле «{localized_name}» из карты Modbus V1.31; текущий код расшифровывается ниже, если таблица значений определена.",
        "en": f"“{localized_name}” field from the V1.31 Modbus map; the current code is decoded below when a value table is defined.",
    }[language]
