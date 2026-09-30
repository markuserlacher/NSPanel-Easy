# __init__.py
"""ESPHome component entry point for NSPanel Easy."""

import logging

from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import globals as globals_component
from esphome.components import nextion, text_sensor
from esphome.components.esp32 import add_idf_sdkconfig_option
from esphome.const import CONF_ID, CONF_TRIGGER_ID
from esphome.core import CORE, coroutine_with_priority
from esphome import pins

CODEOWNERS = ["@edwardtfn"]

_LOGGER = logging.getLogger(__name__)

nspanel_easy_ns = cg.esphome_ns.namespace('nspanel_easy')

CONF_DECIMAL_SEPARATOR_ID = "decimal_separator_id"
CONF_DETAILED_ENTITY_ID = "detailed_entity_id"
CONF_NEXTION_ID = "nextion_id"
CONF_ON_DUMP_CONFIG = "on_dump_config"
CONF_ON_SETUP = "on_setup"
CONF_UNITS_SEPARATOR_ID = "units_separator_id"
PSRAM_CLK_PIN = "psram_clk_pin"
PSRAM_CS_PIN = "psram_cs_pin"
REQUIRE_DISARM_BEFORE_REARM = "require_disarm_before_rearm"

NSPanelEasyComponent = nspanel_easy_ns.class_("NSPanelEasyComponent", cg.Component)
SetupTrigger = nspanel_easy_ns.class_("SetupTrigger", automation.Trigger.template())
DumpConfigTrigger = nspanel_easy_ns.class_("DumpConfigTrigger", automation.Trigger.template())

CONFIG_SCHEMA = cv.Schema({
    cv.Optional(CONF_ID, default="nspanel_easy_component"): cv.declare_id(NSPanelEasyComponent),
    cv.Required(CONF_DECIMAL_SEPARATOR_ID): cv.use_id(globals_component.GlobalsComponent),
    cv.Required(CONF_DETAILED_ENTITY_ID): cv.use_id(text_sensor.TextSensor),
    cv.Required(CONF_NEXTION_ID): cv.use_id(nextion.Nextion),
    cv.Optional(CONF_ON_SETUP): automation.validate_automation(
        {
            cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(SetupTrigger),
        },
    ),
    cv.Optional(CONF_ON_DUMP_CONFIG): automation.validate_automation(
        {
            cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(DumpConfigTrigger),
        },
    ),
    cv.Required(CONF_UNITS_SEPARATOR_ID): cv.use_id(globals_component.GlobalsComponent),

    # Rein optionale Pin-Nummern ohne Strapping-Pin Schema-Zwang
    cv.Optional(PSRAM_CLK_PIN): pins.internal_gpio_output_pin_number,
    cv.Optional(PSRAM_CS_PIN): pins.internal_gpio_output_pin_number,

    cv.Optional(REQUIRE_DISARM_BEFORE_REARM): cv.boolean,
})


@coroutine_with_priority(1.0)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    for conf in config.get(CONF_ON_SETUP, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for key, target in (
        (CONF_DECIMAL_SEPARATOR_ID, "decimal_separator_str"),
        (CONF_UNITS_SEPARATOR_ID, "units_separator_str"),
    ):
        global_ = await cg.get_variable(config[key])
        cg.add(cg.RawStatement(f"esphome::nspanel_easy::{target} = &{global_}->value();"))

    for conf in config.get(CONF_ON_DUMP_CONFIG, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    detailed = await cg.get_variable(config[CONF_DETAILED_ENTITY_ID])
    cg.add(cg.RawStatement(f"esphome::nspanel_easy::detailed_entity_sensor = {detailed};"))

    disp = await cg.get_variable(config[CONF_NEXTION_ID])
    cg.add(cg.RawStatement(f"esphome::nspanel_easy::nextion_display = {disp};"))

    if CORE.using_arduino:
        _LOGGER.warning("Arduino framework deprecated. Migrate to ESP-IDF.")

    # Nur anwenden, wenn es explizit definiert wurde (D0WD-spezifisch für altes NSPanel)
    if PSRAM_CLK_PIN in config:
        clk_pin = config[PSRAM_CLK_PIN]
        add_idf_sdkconfig_option("CONFIG_D0WD_PSRAM_CLK_IO", clk_pin)

    if PSRAM_CS_PIN in config:
        cs_pin = config[PSRAM_CS_PIN]
        add_idf_sdkconfig_option("CONFIG_D0WD_PSRAM_CS_IO", cs_pin)

    if REQUIRE_DISARM_BEFORE_REARM in config and config[REQUIRE_DISARM_BEFORE_REARM]:
        cg.add_define("USE_REQUIRE_DISARM_BEFORE_REARM")

    cg.add_define("USE_NSPANEL_EASY")
    cg.add_global(cg.RawExpression("using namespace esphome::nspanel_easy"))
