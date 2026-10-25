"""Numbermill: a small playable village and logic workshop."""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import pygame

from circuit import Circuit, Part, ARITHMETIC, SEQUENTIAL, UTILITY, CONDUCTORS, VECTORS, WIDTH, HEIGHT, validate_device, standard_device_ports
from commissions import COMMISSIONS
from economy import Village, CONTRACTS, LICENSE_RATE
from town import Town, WORLD_W as TOWN_W, WORLD_H as TOWN_H, LOCATIONS
import ledger
import computation
import workbench
import component_info
import inventions
import sequential
import timing_workshop
import manufacturing
import factory_ui
import factory_controller
import factory_shannon
import workshop_floor
import sandbox
import adventure
import developer_mode
import boiler_tower
import ui_theme
import presentation
import opening_chapter
import chapter_ui
from opening_screen import OpeningScreen
from shannon import Shannon


SCREEN_W, SCREEN_H = 1280, 760
FPS = 60
CELL = 54
BOARD_X, BOARD_Y = 48, 154
PANEL_X = 770
DATA_DIR = Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Keep packaged-game saves outside the read-only application bundle."""
    if not getattr(sys, "frozen", False):
        return DATA_DIR
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "Numbermill"


USER_DATA_DIR = user_data_dir()
SAVE_FILE = USER_DATA_DIR / "save.json"
DESIGNS_FILE = USER_DATA_DIR / "designs.json"
SAVES_DIR = USER_DATA_DIR / "saves"
SLOT_COUNT = 5

from ui_theme import INK, MUTED, CREAM, PAPER, COPPER, TEAL, GOLD
STONE = (157, 153, 136)
STONE_DARK = (109, 107, 99)
COPPER_LIGHT = (227, 158, 100)
TEAL_LIGHT = (123, 199, 175)
RED = (171, 75, 67)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    for attempt in range(4):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 3:
                raise
            # Windows scanners can briefly hold the destination after a save.
            from time import sleep
            sleep(.025 * (attempt + 1))


def village_from_data(data) -> Village:
    if not isinstance(data, dict):
        return Village()
    # Keep existing saves playable after the resident and player names change.
    name_changes = {"Cora": "Agnes"}

    def rename_saved_values(value):
        if isinstance(value, dict):
            renamed = {}
            for key, item in value.items():
                new_key = name_changes.get(key, "Boole" if key == "You" else key)
                renamed[new_key] = rename_saved_values(item)
            return renamed
        if isinstance(value, list):
            return [rename_saved_values(item) for item in value]
        if isinstance(value, str):
            return name_changes.get(value, "Boole" if value == "You" else value)
        return value

    data = rename_saved_values(data)
    # Historical rival records belong to the original inventor, now Grace.
    for offer in data.get('offers', {}).values():
        if offer.get('status') == 'rival' and not offer.get('inventor_id'):
            offer['design_owner'] = 'Grace'
    allowed = Village.__dataclass_fields__
    try:
        village = Village(**{key: value for key, value in data.items() if key in allowed})
        if "daily_life" not in data:
            # Older saves already paid wages and allocated meals for this day.
            from daily_life import state, DAY_SECONDS
            state(village).update(elapsed=DAY_SECONDS, started=True, settled=True)
        return village
    except (TypeError, ValueError):
        return Village()


def slot_path(slot: int) -> Path:
    if not 1 <= slot <= SLOT_COUNT:
        raise ValueError("Invalid save slot")
    return SAVES_DIR / f"slot_{slot}.json"


def load_slot(slot: int):
    path = slot_path(slot)
    if path.exists():
        data = load_json(path, None)
        return data if isinstance(data, dict) and isinstance(data.get("village"), dict) else "unreadable"
    if slot == 1 and not (SAVES_DIR / "legacy_hidden.json").exists() and SAVE_FILE.exists():
        village = load_json(SAVE_FILE, None)
        if not isinstance(village, dict):
            return "unreadable"
        designs = load_json(DESIGNS_FILE, [])
        return {"village": village, "designs": designs if isinstance(designs, list) else [], "legacy": True}
    return None


def text(surface, font, content, x, y, color=INK, width=None):
    return ui_theme.fit_text(surface, font, content, x, y,
                             width if width is not None else surface.get_width() - x - 16, color)


def rounded(surface, color, rect, radius=12, border=0):
    area = pygame.Rect(rect)
    if color == PAPER and not border and area.width >= 250 and area.height >= 150:
        ui_theme.draw_panel(surface, area)
    else:
        pygame.draw.rect(surface, color, area, border, border_radius=radius)


class PixelFont:
    """Keep body text readable and scale headings to crisp game pixels."""

    def __init__(self, size: int, bold: bool = False):
        self.scale = 1
        self.base = ui_theme.make_font(size, bold)

    def render(self, content, antialias, color):
        return self.base.render(str(content), True, color)


class Game:
    def __init__(self):
        presentation.prepare_display()
        pygame.init()
        pygame.display.set_caption("Numbermill — Copperside Village")
        pygame.display.set_icon(presentation.window_icon())
        self.preferences_path = SAVES_DIR.parent / "preferences.json"
        self.settings = presentation.load_preferences(self.preferences_path)
        self.viewport = presentation.Viewport(self.settings)
        self.screen = self.viewport.canvas
        self.settings_open = self.controls_open = False
        self.reduced_motion = self.settings["reduced_motion"]
        self.clock = pygame.time.Clock()
        self.font = PixelFont(18)
        self.small = PixelFont(16)
        self.tiny = PixelFont(14)
        self.big = PixelFont(30, bold=True)
        self.menu_title = PixelFont(42, bold=True)
        self.heading = PixelFont(24, bold=True)
        self.circuit = Circuit()
        self.village = Village()
        self.town = Town()
        self.shannon = Shannon()
        self.scene = "menu"
        self.menu_page = "title"
        self.opening_screen = None
        self.opening_reveal = 0.0
        self.current_slot = None
        self.pending_delete = None
        self.board_return_scene = "town"
        self.contract_page = 0
        self.ledger_tab = "Overview"
        self.ledger_index = 0
        self.trade_day_offset = 0
        self.ledger_return_scene = "town"
        self.town_dialogue = None
        self.town_topic = "work"
        self.chapter_view = None
        self.designs = []
        self.library_sequence = 0
        self.library_versions = {}
        self.pending_design_delete = None
        self.port_names = {"A": "Input A", "B": "Input B", "OUT": "Output"}
        self.design_source = None
        self.held_device = None
        self.device_stack = []
        self.port_editor = None
        self.active_compute = None
        self.compute_key = "fuel_quote"
        self.compute_results = []
        self.compute_message = "Choose one of Mely and Luca's calculation jobs."
        self.compute_return_scene = "workshop"
        self.numeric_mode = False
        self.invention = None
        self.invention_return_scene = "workshop"
        self.library_page = 0
        self.selected = "TRACE"
        self.trace_source = None
        self.trace_points = []
        self.invention_context = None
        self.adventure_context = self.adventure_editor = None
        self.adventure_runtime = None
        self.sandbox_context = None
        self.sandbox_draft = {}
        self.timing_key = self.timing_context = self.timing_results = None
        self.factory_context = self.factory_machine_id = None
        self.factory_dialog = None
        self.factory_dialog_buttons = []
        self.palette_page = 0
        self.factory_page = "floor"
        self.factory_message = ""
        self.factory_order_page = 0
        self.factory_selected = self.factory_placing = self.factory_moving = None
        self.invention_picker = False
        self.rotation = 0
        self.tab = "BUILD"
        self.running = True
        self.developer_mode = False
        self.pause_menu_open = False
        self.component_info = None
        self.paused = False
        self.tick_interval = 0.22
        self.elapsed = 0.0
        self.message = "Every workshop invention changes a business."
        self.message_timer = 0.0
        self.test_results = None
        self.test_scroll = 0
        self.task_help_open = False
        self.test_message = ""
        self.tested_job = None
        self.tested_snapshot = None
        self.success_job = None
        self.help_open = False
        self.delivery_open = False
        self.delivery_error = ""
        self.success_payout = 0
        self.success_mode = "install"
        self.buttons: list[tuple[pygame.Rect, object]] = []
        self.focus_index = -1
        self.focus_context = None

    def start_slot(self, slot: int, *, introduce=False):
        self.component_info = None
        data = load_slot(slot)
        if data == "unreadable":
            self.toast(f"Slot {slot} could not be read. Its file was left untouched.")
            return
        try:
            loaded_circuit = Circuit.from_snapshot(data.get("circuit", [])) if data and isinstance(data.get("circuit"), list) else Circuit()
        except (ValueError, RecursionError):
            self.toast(f"Slot {slot} contains an invalid device. Its file was left untouched.")
            return
        self.pending_delete = None
        self.current_slot = slot
        self.device_stack = []
        self.design_source = None
        self.held_device = None
        self.selected = "TRACE"
        workshop_floor.cancel(self)
        self.invention_context = None
        self.adventure_context = self.adventure_editor = None
        self.adventure_runtime = None
        self.sandbox_context = None
        self.sandbox_draft = {}
        self.timing_key = self.timing_context = self.timing_results = None
        self.factory_context = self.factory_machine_id = None
        self.factory_dialog = None
        self.factory_dialog_buttons = []
        self.palette_page = 0
        self.factory_page = "floor"
        self.factory_message = ""
        self.factory_order_page = 0
        self.factory_selected = self.factory_placing = self.factory_moving = None
        self.rotation = 0
        self.port_editor = None
        self.active_compute = None
        self.compute_results = []
        self.numeric_mode = False
        self.invention = None
        self.invention_picker = False
        self.port_names = {"A": "Input A", "B": "Input B", "OUT": "Output"}
        if data:
            self.active_compute = data.get("active_compute") if data.get("active_compute") in computation.JOBS else None
            self.numeric_mode = bool(data.get("numeric_mode", self.active_compute is not None))
            if self.active_compute:
                self.compute_key = self.active_compute
        if data and isinstance(data.get("port_names"), dict):
            self.port_names.update(data["port_names"])
        self.village = village_from_data(data.get("village")) if data else Village()
        active_job = COMMISSIONS.get(self.village.active_commission)
        if active_job is None or (active_job.prerequisite and not self.contract_complete(active_job.prerequisite)):
            self.village.active_commission = "mill"
        designs = data.get("designs", []) if data else []
        self.designs = designs if isinstance(designs, list) else []
        self.library_sequence = data.get("library_sequence", 0) if data else 0
        self.library_versions = dict(data.get("library_versions", {})) if data else {}
        self.pending_design_delete = None
        self.track_library_versions()
        for design in self.designs:
            if isinstance(design, dict):
                design.setdefault("owner", "Boole")
                design.setdefault("rights_note", "Private design")
        if data and data.get("version", 1) < 5 and "arithmetic_unlocks" not in data.get("village", {}):
            rows = loaded_circuit.snapshot()
            for entry in self.designs:
                if isinstance(entry, dict):
                    rows.extend(entry.get("parts", []))
            for entry in self.village.compute_designs.values():
                rows.extend(entry.get("parts", []))
            self.village.arithmetic_unlocks = sorted(inventions.required_blocks(rows))
        self.sandbox_draft = data.get("sandbox_draft", {}) if data else {}
        self.circuit = loaded_circuit
        if data and data.get("circuit_runtime"):
            try:
                self.circuit.restore_runtime(data["circuit_runtime"])
            except ValueError:
                self.circuit.reset()
        self.town = Town()
        self.shannon = Shannon()
        if data and isinstance(data.get("town"), list) and len(data["town"]) == 2:
            try:
                if data.get("version", 1) < 2:
                    old_x = float(data["town"][0])
                    old_sites = {"mill": 226, "workshop": 625, "bakery": 1024,
                                 "market": 1423, "home_1": 1735, "home_2": 1924}
                    nearest = min(old_sites, key=lambda key: abs(old_sites[key] - old_x))
                    self.town.player_x, self.town.player_y = LOCATIONS[nearest]
                else:
                    self.town.player_x = max(45, min(TOWN_W - 45, float(data["town"][0])))
                    self.town.player_y = max(145, min(TOWN_H - 45, float(data["town"][1])))
            except (TypeError, ValueError):
                pass
        self.town.player_x, self.town.player_y = self.town.safe_position(
            (self.town.player_x, self.town.player_y))
        self.town.companion.reset((self.town.player_x, self.town.player_y), self.town.player_facing)
        self.town.update_people(self.village, 0)
        self.scene = "town"
        self.town_dialogue = None
        self.town_topic = "work"
        self.chapter_view = None
        opening_chapter.observe(self.village)
        self.library_page = 0
        self.contract_page = 0
        self.ledger_tab = "Overview"
        self.ledger_index = 0
        self.trade_day_offset = 0
        self.selected = "TRACE"
        self.rotation = 0
        self.tab = "BUILD"
        self.paused = False
        self.elapsed = float(data.get("circuit_elapsed", 0.0)) if data else 0.0
        self.paused = bool(data.get("circuit_paused", False)) if data else False
        self.tick_interval = min(1.0, max(.04, float(data.get("circuit_tick_interval", .22)))) if data else .22
        self.pause_menu_open = False
        self.developer_mode = False
        self.test_results = None
        self.test_scroll = 0
        self.task_help_open = False
        self.tested_job = None
        self.tested_snapshot = None
        self.success_job = None
        self.help_open = False
        self.delivery_open = False
        self.delivery_error = ""
        self.toast(f"{'Loaded' if data else 'Created'} slot {slot}. Enter your workshop to start manufacturing.")
        self.settings["last_slot"] = slot
        self.__dict__.pop("title_continue_slot", None)
        self.settings_open = self.controls_open = False
        self.save_preferences()
        if not data:
            self.save_game()
            if introduce:
                self.scene = "menu"
                self.menu_page = "new_save"
                self.buttons.clear()
                self.focus_index = -1

    def finish_new_save_intro(self):
        self.menu_page = "title"
        self.scene = "town"
        self.buttons.clear()
        self.focus_index = -1

    def save_game(self):
        opening_chapter.observe(self.village)
        adventure.sync(self)
        factory_controller.sync(self)
        factory_shannon.observe(self.village)
        timing_workshop.sync(self)
        sandbox.sync(self)
        if self.invention:
            self.invention.design["port_names"] = self.port_names.copy()
            self.invention.sync()
        if self.current_slot is None:
            return
        context = self.adventure_context or self.sandbox_context or self.invention_context or self.timing_context or self.factory_context
        root_circuit = context["circuit"] if context else self.circuit
        root_names = context["port_names"] if context else self.port_names
        stack = context["device_stack"] if context else self.device_stack
        if stack:
            root_circuit, root_names, _ = stack[0]
        save_json(slot_path(self.current_slot), {
            "version": 10,
            "sandbox_draft": self.sandbox_draft,
            "village": vars(self.village),
            "designs": self.designs,
            "library_sequence": self.library_sequence,
            "library_versions": self.library_versions,
            "circuit": root_circuit.snapshot(),
            "circuit_runtime": root_circuit.runtime_snapshot(),
            "circuit_elapsed": context["elapsed"] if context else self.elapsed,
            "circuit_paused": context["paused"] if context else self.paused,
            "circuit_tick_interval": context["tick_interval"] if context else self.tick_interval,
            "port_names": root_names,
            "active_compute": context["active_compute"] if context else self.active_compute,
            "numeric_mode": context["numeric_mode"] if context else self.numeric_mode,
            "town": [self.town.player_x, self.town.player_y],
        })

    def return_to_menu(self):
        self.component_info = None
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        if self.timing_key is not None:
            timing_workshop.leave(self)
        self.pause_menu_open = False
        if self.sandbox_context is not None:
            sandbox.leave(self)
        if self.invention:
            self.close_invention()
        self.save_game()
        self.scene = "menu"
        self.menu_page = "title"
        self.chapter_view = None
        self.pending_delete = None
        self.pending_design_delete = None
        self.town_dialogue = None
        self.test_results = None
        self.success_job = None
        self.current_slot = None
        self.task_help_open = False
        self.test_scroll = 0
        self.invention_picker = False
        self.help_open = False
        self.delivery_open = False
        self.port_editor = None
        self.toast("Progress saved. Welcome back, Boole.")

    def request_delete_slot(self, slot: int):
        if self.scene == "menu" and self.menu_page == "slots" and load_slot(slot) is not None:
            self.pending_delete = slot

    def confirm_delete_slot(self):
        if self.scene != "menu" or self.pending_delete is None:
            return
        slot = self.pending_delete
        if slot == 1:
            # Keep the original pre-slot files as a manual backup without
            # making them reappear after the visible slot is deleted.
            save_json(SAVES_DIR / "legacy_hidden.json", {"hidden": True})
        slot_path(slot).unlink(missing_ok=True)
        self.pending_delete = None
        self.toast(f"Slot {slot} deleted. It is ready for a new village.")

    @property
    def commission(self):
        return COMMISSIONS[self.village.active_commission]

    def contract_complete(self, key):
        return getattr(self.village, f"{key}_machine", False)

    def open_contract_board(self):
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.sandbox_context is not None:
            sandbox.leave(self)
        self.board_return_scene = self.scene
        self.contract_page = 0
        self.scene = "contracts"

    def open_requests(self, npc=None):
        from project_ui import visible
        self.request_return_scene = self.scene
        self.request_index = 0
        self.request_notice = ''
        self.request_notice_key = None
        for i, project in enumerate(visible(self.village)):
            if project['npc'] == npc:
                self.request_index = i
        self.scene = 'requests'

    def close_requests(self):
        self.scene = self.request_return_scene

    def act_on_request(self, key):
        from character_projects import accept, deliver
        state = self.village.character_projects[key]
        if state['status'] == 'offered':
            message = accept(self.village, key)
            success = True
        else:
            success, message = deliver(self.village, key)
        self.request_notice = '' if success else message
        self.request_notice_key = key
        self.toast(message)
        self.save_game()

    def request_suppliers(self):
        self.open_ledger()
        self.select_ledger_tab('Map')

    def open_ledger(self):
        self.ledger_return_scene = self.scene
        self.scene = "ledger"

    def close_ledger(self):
        self.scene = self.ledger_return_scene

    def select_ledger_tab(self, tab):
        self.ledger_tab = tab
        self.ledger_index = 0

    def shift_trade_day(self, delta):
        self.trade_day_offset = max(0, min(len(self.village.trade_history) - 1,
                                           self.trade_day_offset + delta))

    def toggle_service(self):
        self.toast(self.village.toggle_service())
        self.save_game()

    def open_compute(self):
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        if self.timing_key is not None:
            timing_workshop.leave(self)
        if self.sandbox_context is not None:
            sandbox.leave(self)
        if self.invention:
            self.close_invention()
        self.compute_return_scene = self.scene if self.scene != "compute" else self.compute_return_scene
        self.scene = "compute"

    def close_compute(self):
        self.scene = self.compute_return_scene

    def select_compute(self, key):
        self.compute_key = key
        self.compute_results = []
        self.test_scroll = 0

    def build_compute(self):
        operation = computation.JOBS[self.compute_key].operation
        if operation not in self.village.arithmetic_unlocks:
            self.open_invention(inventions.FOR_BLOCK[operation])
            return
        self.active_compute = self.compute_key
        job = computation.JOBS[self.compute_key]
        self.port_names = dict(zip(("A", "B", "OUT"), (*job.inputs, job.output)))
        self.numeric_mode = True
        workshop_floor.cancel(self)
        workshop_floor.prepare(self)
        self.scene = "workshop"
        self.tab = "BUILD"
        self.compute_results = []
        self.tested_snapshot = None
        self.design_source = None
        self.toast(job.description)

    def test_compute(self):
        self.test_scroll = 0
        self.compute_results = computation.check(self.circuit, self.compute_key)
        passed = sum(row["passed"] for row in self.compute_results)
        self.compute_message = f"{passed}/{len(self.compute_results)} cases passed. " + ("Ready to register." if passed == len(self.compute_results) else "Return to Build and fix the red cases.")
        if self.scene != "compute":
            self.open_compute()

    def approve_compute(self):
        self.compute_message, self.compute_results = computation.approve(self.village, self.compute_key, self.circuit, self.port_names)
        self.save_game()

    def run_compute(self):
        self.compute_message = computation.run_order(self.village, self.compute_key)
        self.save_game()

    def open_invention(self, key="adder"):
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        if self.timing_key is not None:
            timing_workshop.leave(self)
        if self.sandbox_context is not None:
            sandbox.leave(self)
        self.invention_picker = False
        if self.invention is None:
            self.invention_return_scene = self.scene
            self.invention_context = {name: getattr(self, name) for name in
                                      ("circuit", "port_names", "active_compute", "numeric_mode", "tab", "selected", "paused", "design_source", "device_stack",
                                       "rotation", "held_device", "elapsed", "tick_interval", "test_results", "tested_job", "tested_snapshot", "test_message",
                                       "success_job", "delivery_open", "help_open")}
        self.scene = "workshop"
        self.switch_invention(key)

    def switch_invention(self, key):
        if self.invention:
            self.invention.design["port_names"] = self.port_names.copy()
            self.invention.sync()
        challenge = inventions.CHALLENGES[key]
        prerequisite_missing = challenge.prerequisite and challenge.prerequisite not in self.village.arithmetic_unlocks
        if prerequisite_missing:
            key = inventions.FOR_BLOCK[challenge.prerequisite]
        self.invention = inventions.Bench(self.village, key)
        self.circuit = self.invention.circuit
        self.active_compute = None
        self.numeric_mode = False
        self.paused = True
        self.device_stack = []
        self.design_source = None
        self.rotation = 0
        self.held_device = None
        self.elapsed = 0
        self.test_results = None
        self.tested_job = None
        self.tested_snapshot = None
        self.success_job = None
        self.delivery_open = False
        self.help_open = False
        self.port_names = {"A": "Input A", "B": "Input B", "OUT": "Output"}
        self.port_names.update({port["name"]: port["name"] for port in self.circuit.terminals.values()})
        self.port_names.update(self.invention.design["port_names"])
        self.tab = "BUILD"
        self.selected = "TRACE"
        workshop_floor.cancel(self)
        if prerequisite_missing:
            self.invention.message = f"Invent {challenge.prerequisite} first; then return to earn {', '.join(challenge.unlocks)}."

    def close_invention(self):
        if self.invention is None:
            return
        self.invention.design["port_names"] = self.port_names.copy()
        self.invention.sync()
        self.invention = None
        for name, value in self.invention_context.items():
            setattr(self, name, value)
        self.invention_context = None
        self.port_editor = None
        workshop_floor.cancel(self)
        self.save_game()
        self.scene = self.invention_return_scene

    def test_invention(self):
        self.test_scroll = 0
        self.invention.run_tests()
        self.toast(self.invention.message)
        self.save_game()

    def select_part(self, kind):
        workshop_floor.cancel(self)
        if self.sandbox_context is None and self.factory_context is None and not adventure.active_editor(self) and kind in ARITHMETIC and kind not in self.village.arithmetic_unlocks:
            self.open_invention(inventions.FOR_BLOCK[kind])
            return
        self.selected = kind

    def choose_contract(self, key):
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        if self.timing_key is not None:
            timing_workshop.leave(self)
        if self.sandbox_context is not None:
            sandbox.leave(self)
        if self.invention:
            self.close_invention()
        job = COMMISSIONS[key]
        if self.village.offers.get(key, {}).get("status") not in ("open", "bid", "player", "rival"):
            return
        self.village.active_commission = key
        workshop_floor.cancel(self)
        self.active_compute = None
        self.numeric_mode = False
        self.test_results = None
        self.tested_job = None
        self.tested_snapshot = None
        self.success_job = None
        self.town_dialogue = None
        self.scene = "workshop"
        self.tab = "BUILD"
        self.save_game()
        self.toast(f"Workshop: {job.title}. Your floor plan is ready to edit.")

    @property
    def submission_ready(self):
        if adventure.active_editor(self):
            return False
        if self.factory_context is not None:
            return False
        if self.timing_key is not None:
            return False
        completed = self.contract_complete(self.commission.key)
        return (
            self.sandbox_context is None
            and not completed
            and self.village.offers.get(self.commission.key, {}).get("status") in ("open", "bid")
            and self.tested_job == self.commission.key
            and self.tested_snapshot == self.circuit.snapshot()
        )

    def open_factory(self):
        entering = self.scene != "factory"
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        if self.timing_key is not None:
            timing_workshop.leave(self)
        if self.sandbox_context is not None:
            sandbox.leave(self)
        if self.invention:
            self.close_invention()
        self.scene = "factory"
        self.town_dialogue = None
        self.factory_page = "floor"
        self.factory_message = ""
        self.factory_order_page = 0
        self.factory_placing = self.factory_moving = None
        manufacturing.state(self.village)
        factory_ui.close_dialog(self)
        if entering:
            factory_shannon.enter_workshop(self.village)

    def open_circuit_bench(self):
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        sandbox.enter(self)
        self.toast("Sandbox / free build")

    def edit_factory_controller(self, machine_id):
        factory_controller.enter(self, machine_id)

    def interact_town(self):
        if self.town_dialogue is None:
            nearby = self.town.nearby_place()
            if nearby == "adventure":
                adventure.enter(self)
                return
            if nearby == "workshop":
                self.open_factory()
                return
            self.town_dialogue = nearby
            self.town_topic = "work"
            if nearby == "market":
                self.toast("One loaf kept for walk-in shoppers. E buys bread.")
            if nearby is None:
                self.toast("Walk closer to a building entrance.")
            return
        location = self.town_dialogue
        from materials import SHOPS, buy_material
        if location in SHOPS:
            self.toast(buy_material(self.village, location))
            self.save_game()
            return
        if location == "market":
            self.toast(self.village.buy_bread())
            self.save_game()
            return
        if location in self.village.households:
            self.town_dialogue = None
            return
        if location not in ("mill", "bakery"):
            self.town_dialogue = None
            return
        if location == "bakery" and not self.village.mill_machine:
            self.toast("The baker needs the mill's flour supply first.")
            self.town_dialogue = None
            return
        if location in COMMISSIONS:
            self.town_dialogue = None
            self.choose_contract(location)
            return
        self.scene = "workshop"
        self.tab = "BUILD"
        self.town_dialogue = None
        self.toast(f"Workshop: {self.commission.title}.")

    def toast(self, message: str):
        self.message = message
        self.message_timer = 6.0

    def talk_journey(self, name):
        if name in opening_chapter.PEOPLE:
            self.town_topic = 'journey'
            opening_chapter.state(self.village)['topics'][name] = opening_chapter.topic_stage(self.village)
            self.save_game()

    def mouse_pos(self):
        return self.viewport.pointer(pygame.mouse.get_pos())

    def save_preferences(self):
        try:
            save_json(self.preferences_path, self.settings)
        except OSError:
            self.toast("Settings are active, but could not be saved.")

    def open_settings(self):
        self.settings_open = True
        self.focus_index = -1

    def close_settings(self):
        self.settings_open = self.controls_open = False
        self.focus_index = -1
        self.save_preferences()

    def toggle_preference(self, key):
        self.settings[key] = not self.settings[key]
        if key == "fullscreen":
            try:
                self.viewport.configure()
            except pygame.error:
                self.settings[key] = False
                self.viewport.configure()
                self.toast("Fullscreen is unavailable on this display. Windowed mode restored.")
        self.reduced_motion = self.settings["reduced_motion"]
        self.town.reduced_motion = self.reduced_motion
        self.save_preferences()

    def continue_slot(self):
        preferred = self.settings.get("last_slot")
        choices = ([preferred] if preferred else []) + list(range(1, SLOT_COUNT + 1))
        return next((slot for slot in choices if isinstance(load_slot(slot), dict)), None)

    def new_game(self):
        slot = next((slot for slot in range(1, SLOT_COUNT + 1) if load_slot(slot) is None), None)
        if slot is None:
            self.menu_page = "slots"
            self.toast("All slots are in use. Choose a save to continue or delete a slot.")
        else:
            self.start_slot(slot, introduce=True)

    def focus_navigation(self, event):
        """Keyboard focus is limited to menus, leaving circuit and receiver keys intact."""
        enabled = self.settings_open or self.pause_menu_open or (self.scene == "menu" and self.pending_delete is None)
        if not enabled or not self.buttons:
            return False
        key = event.key
        if key in (pygame.K_TAB, pygame.K_UP, pygame.K_DOWN):
            direction = -1 if key == pygame.K_UP or (key == pygame.K_TAB and getattr(event, "mod", 0) & pygame.KMOD_SHIFT) else 1
            self.focus_index = ((0 if direction > 0 else len(self.buttons) - 1)
                                if self.focus_index < 0 else (self.focus_index + direction) % len(self.buttons))
            return True
        if self.focus_index >= 0 and key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            action = self.buttons[min(self.focus_index, len(self.buttons)-1)][1]
            self.focus_index = -1
            action()
            return True
        return False

    def button(self, rect, label, action, *, active=False, small=False, enabled=True, danger=False, icon=False):
        rect = pygame.Rect(rect)
        hover = enabled and rect.collidepoint(self.mouse_pos())
        focused = enabled and self.focus_index == len(self.buttons)
        color = ui_theme.button_face(self.screen, rect, active=active, hover=hover,
                                     pressed=hover and pygame.mouse.get_pressed()[0], enabled=enabled,
                                     danger=danger, focused=focused)
        font = self.small if small else self.font
        rendered = font.render(ui_theme.elide(font, label, rect.width - 16), True, color)
        if rendered.get_height() > rect.height - 6:
            ink = rendered.get_bounding_rect()
            if ink.width:
                rendered = rendered.subsurface(ink).copy()
            if rendered.get_height() > rect.height - 6:
                rendered = pygame.transform.scale(rendered, (rendered.get_width(), rect.height - 6))
        self.screen.blit(rendered, rendered.get_rect(center=rect.center))
        if enabled:
            self.buttons.append((rect, action))

    def board_pos(self, mouse) -> tuple[int, int] | None:
        bx, by, cell = self.board_metrics()
        x = (mouse[0] - bx) // cell
        y = (mouse[1] - by) // cell
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            return x, y
        return None

    def board_metrics(self):
        if self.factory_context is not None and self.tab == "BUILD" and not self.device_stack:
            return (178, 220, 40)
        return (BOARD_X, BOARD_Y, CELL) if self.tab == "BUILD" and not self.device_stack else (76, 154, 41)

    def handle_click(self, mouse, button):
        if self.settings_open:
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        break
            return
        if self.component_info is not None:
            component_info.click(self, mouse, button)
            return
        if self.pause_menu_open:
            if button == 1:
                for rect, action in self.pause_buttons():
                    if rect.collidepoint(mouse):
                        action()
                        break
            return
        if chapter_ui.click(self, mouse, button):
            return
        if self.scene in ("adventure", "boiler_tower"):
            adventure.click(self, mouse, button)
            return
        if self.scene == "workshop" and adventure.active_editor(self) and adventure.editor_click(self, mouse, button):
            return
        if self.scene == "factory":
            factory_ui.click(self, mouse, button)
            return
        if self.scene == "town":
            from town import MINIMAP_RECT, TOWN_READOUT_RECT
            if self.shannon.click(self, mouse, button):
                return
            if MINIMAP_RECT.collidepoint(mouse):
                if button == 1:
                    self.open_ledger()
                    self.select_ledger_tab("Map")
                return
            if TOWN_READOUT_RECT.collidepoint(mouse):
                return
        if self.pending_design_delete is not None:
            if button == 1:
                if pygame.Rect(681, 423, 205, 43).collidepoint(mouse):
                    self.confirm_delete_design()
                elif pygame.Rect(394, 423, 205, 43).collidepoint(mouse):
                    self.pending_design_delete = None
            return
        if self.task_help_open:
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        return
            return
        if self.timing_results is not None:
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        break
            return
        if self.invention_picker or self.invention and self.invention.show_results:
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        return
            return
        if self.scene == "workshop" and self.port_editor is not None:
            if button == 1:
                for i in range(len(self.port_editor["keys"])):
                    if pygame.Rect(380, 222 + i * 42, 520, 36).collidepoint(mouse):
                        self.port_editor["field"] = i
                if pygame.Rect(700, 608, 200, 40).collidepoint(mouse):
                    self.finish_ports()
            return
        if self.scene == "workshop" and self.device_stack:
            for rect, action in reversed(self.buttons):
                if button == 1 and rect.collidepoint(mouse):
                    action()
                    return
            pos = self.board_pos(mouse)
            if pos and button == 3 and self.circuit.parts.get(pos, Part("PIPE")).kind == "DEVICE":
                self.inspect_device(pos)
            return
        if self.scene == "workshop" and self.help_open:
            if button == 1 and pygame.Rect(874, 596, 190, 43).collidepoint(mouse):
                self.help_open = False
            return
        if self.scene == "workshop" and self.delivery_open:
            if button == 1:
                for i, mode in enumerate(("install", "sell", "license")):
                    if pygame.Rect(330, 305 + i * 85, 620, 68).collidepoint(mouse):
                        self.submit_design(mode)
                        return
                if pygame.Rect(824, 584, 128, 37).collidepoint(mouse):
                    self.delivery_open = False
                elif pygame.Rect(330, 584, 310, 37).collidepoint(mouse):
                    self.request_material_advance()
            return
        if self.scene in ("town", "contracts", "ledger", "compute", "requests"):
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        return
                if self.scene == "town" and not (self.town_dialogue and pygame.Rect(235, 414, 810, 306).collidepoint(mouse)):
                    name = self.town.person_at(mouse)
                    if name:
                        self.town_dialogue = f"person:{name}"
                        self.town_topic = "work"
                    elif self.town_dialogue:
                        self.town_dialogue = None
            return
        if self.scene == "menu":
            if button == 1:
                if self.pending_delete is not None:
                    if pygame.Rect(681, 423, 205, 43).collidepoint(mouse):
                        self.confirm_delete_slot()
                    elif pygame.Rect(394, 423, 205, 43).collidepoint(mouse):
                        self.pending_delete = None
                    return
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        return
            return
        if self.scene == "town":
            return
        if self.success_job is not None:
            if button == 1 and pygame.Rect(655, 548, 270, 43).collidepoint(mouse):
                self.success_job = None
                self.scene = "town"
                self.toast("The village has new work for its inventor.")
            elif button == 1 and pygame.Rect(354, 548, 270, 43).collidepoint(mouse):
                self.success_job = None
            return
        if self.test_results is not None:
            if self.task_help_open:
                if button == 1 and pygame.Rect(547, 584, 186, 39).collidepoint(mouse):
                    self.task_help_open = False
            elif button == 1 and pygame.Rect(357, 627, 175, 39).collidepoint(mouse):
                self.test_results = None
            elif button == 1 and pygame.Rect(548, 627, 184, 39).collidepoint(mouse):
                self.task_help_open = True
            elif button == 1 and pygame.Rect(754, 627, 268, 39).collidepoint(mouse) and self.submission_ready:
                self.test_results = None
                self.open_delivery_choices()
            return
        if button == 1:
            for rect, action in reversed(self.buttons):
                if rect.collidepoint(mouse):
                    action()
                    return
        if self.tab == "BUILD":
            workshop_floor.click(self, mouse, button)

    def select_device(self, index):
        item = self.designs[index]
        if self.invention or not standard_device_ports(item["parts"]):
            self.toast("Load this prototype to edit its named ports and outputs.")
            return
        locked = inventions.locked_blocks(self.village, item["parts"])
        if locked and self.sandbox_context is None and self.factory_context is None and not adventure.active_editor(self):
            self.toast(f"Invent {', '.join(sorted(locked))} before placing this device.")
            return
        self.held_device = {"id": item.get("device_id", item["number"]),
                            "version": item.get("version", 1), "name": item["name"],
                            "ports": deepcopy(item.get("ports", {"A": "Input A", "B": "Input B", "OUT": "Output"})),
                            "parts": deepcopy(item["parts"])}
        try:
            validate_device(self.held_device)
        except ValueError as error:
            self.held_device = None
            self.toast(str(error))
            return
        self.selected = "DEVICE"
        workshop_floor.cancel(self)
        self.tab = "BUILD"
        self.toast(f"Placing {item['name']} v{item.get('version', 1)}. A west, B south, output east. R rotates.")

    def inspect_device(self, pos):
        part = self.circuit.parts[pos]
        self.device_stack.append((self.circuit, self.port_names, part.device["name"]))
        self.circuit = deepcopy(self.circuit.devices[pos])
        self.port_names = part.device.get("ports", {"A": "Input A", "B": "Input B", "OUT": "Output"}).copy()

    def leave_device(self):
        self.circuit, self.port_names, _ = self.device_stack.pop()

    def edit_ports(self):
        keys = [port["name"] for port in self.circuit.terminals.values()]
        self.port_editor = {"field": 0, "keys": keys, "values": [self.port_names.get(k, k) for k in keys]}

    def finish_ports(self):
        self.port_names.update({k: (value.strip() or k) for k, value in
                                zip(self.port_editor["keys"], self.port_editor["values"])})
        self.port_editor = None
        self.save_game()

    def save_copy(self, name=None, announce=True, job_key=None, delivery_mode=None):
        self.track_library_versions()
        number = self.library_sequence + 1
        source = self.design_source if name is None and job_key is None else None
        device_id = source.get("device_id", source["number"]) if source else number
        version = max(self.library_versions.get(str(device_id), 0), source.get("version", 1) if source else 0) + 1
        label = name or (source["name"] if source else f"Design {number:02d}")
        rights = "Private design"
        if job_key is not None:
            customer = COMMISSIONS[job_key].customer
            rights = {"install": f"Installed at {customer}; rights retained",
                      "sell": f"{customer} owns one copy",
                      "license": f"Licensed to {customer} at {LICENSE_RATE}/day"}[delivery_mode]
        self.designs.append({"number": number, "name": label, "parts": self.circuit.snapshot(),
                             "owner": "Boole", "job": job_key, "rights_note": rights,
                             "device_id": device_id, "version": version, "ports": self.port_names.copy()})
        if self.timing_key is not None:
            self.designs[-1]["timing"] = self.timing_key
        if self.invention:
            self.designs[-1]["invention"] = self.invention.key
        self.design_source = self.designs[-1]
        self.track_library_versions()
        self.library_page = 0
        self.save_game()
        if announce:
            self.toast(f"Saved {label}. Open Library to load a copy.")
        return label

    def track_library_versions(self):
        for item in self.designs:
            if not isinstance(item, dict):
                continue
            number = int(item.get("number", 0))
            self.library_sequence = max(self.library_sequence, number)
            key = str(item.get("device_id", number))
            self.library_versions[key] = max(self.library_versions.get(key, 0), item.get("version", 1))

    def request_delete_design(self, index):
        if self.scene == "workshop" and 0 <= index < len(self.designs):
            self.pending_design_delete = index

    def confirm_delete_design(self):
        index = self.pending_design_delete
        if index is None or not 0 <= index < len(self.designs):
            return
        self.track_library_versions()
        item = self.designs.pop(index)
        self.pending_design_delete = None
        self.library_page = min(self.library_page, max(0, (len(self.designs) - 1) // 4))
        self.save_game()
        self.toast(f"Deleted {item.get('name', 'Design')} v{item.get('version', 1)} from Library.")

    def load_design(self, index):
        try:
            entry = self.designs[index]
            locked = inventions.locked_blocks(self.village, entry["parts"])
            if locked and self.sandbox_context is None and self.factory_context is None and not adventure.active_editor(self):
                self.toast(f"Invent {', '.join(sorted(locked))} before loading this design.")
                return
            if entry.get("invention") and self.sandbox_context is None and not adventure.active_editor(self):
                if not self.invention or self.invention.key != entry["invention"]:
                    self.open_invention(entry["invention"])
            elif entry.get("timing") in sequential.CHALLENGES and self.sandbox_context is None and not adventure.active_editor(self):
                if self.timing_key != entry["timing"]:
                    timing_workshop.enter(self, entry["timing"])
            elif self.invention:
                self.close_invention()
                self.scene = "workshop"
            self.circuit = Circuit.from_snapshot(entry["parts"])
            workshop_floor.prepare(self)
            workshop_floor.cancel(self)
            if self.invention:
                self.invention.circuit = self.circuit
                self.invention.edit()
            self.port_names = entry.get("ports", {"A": "Input A", "B": "Input B", "OUT": "Output"}).copy()
            self.design_source = entry
            self.tested_job = None
            self.tested_snapshot = None
            self.toast(f"Loaded a copy of {entry['name']}.")
            self.tab = "BUILD"
        except (IndexError, KeyError, TypeError, ValueError):
            self.toast("That design could not be loaded.")

    def test_commission(self):
        if adventure.active_editor(self):
            adventure.validate(self)
            return
        if self.factory_context is not None:
            factory_controller.preview(self)
            return
        if self.timing_key is not None:
            timing_workshop.test(self)
            return
        if self.sandbox_context is not None:
            sandbox.probe(self)
            return
        self.test_scroll = 0
        self.task_help_open = False
        if self.invention:
            self.test_invention()
            return
        workshop_floor.prepare(self)
        locked = inventions.locked_blocks(self.village, self.circuit.snapshot())
        if locked and self.sandbox_context is None and self.factory_context is None and not adventure.active_editor(self):
            self.open_invention(inventions.FOR_BLOCK[sorted(locked)[0]])
            return
        if self.active_compute:
            self.compute_key = self.active_compute
            self.test_compute()
            return
        job = self.commission
        self.test_results = self.circuit.commission_test_results(job.logic)
        passed = all(case.passed for case in self.test_results)
        completed = self.contract_complete(job.key)
        if passed:
            self.tested_job = job.key
            self.tested_snapshot = self.circuit.snapshot()
            self.test_message = (
                f"{len(self.test_results)} / {len(self.test_results)} checks passed. This commission is already delivered."
                if completed else f"{len(self.test_results)} / {len(self.test_results)} checks passed. Choose delivery terms."
            )
        else:
            self.tested_job = None
            self.tested_snapshot = None
            count = sum(case.passed for case in self.test_results)
            self.test_message = f"{count} / {len(self.test_results)} checks passed. Fix the red rows and test again."
        self.toast(self.test_message)

    def open_delivery_choices(self):
        if self.factory_context is not None:
            factory_controller.install(self)
            return
        if self.active_compute:
            self.open_compute()
            return
        if not self.submission_ready:
            self.toast("Pass all input checks before choosing delivery terms.")
            return
        self.test_results = None
        self.delivery_open = True
        self.delivery_error = ""

    def request_material_advance(self):
        from materials import advance_materials
        self.delivery_error = advance_materials(self.village, self.commission.key)
        self.toast(self.delivery_error)
        self.save_game()

    def submit_design(self, mode="install"):
        if not self.submission_ready:
            self.toast("Run all input checks before delivering this design.")
            return
        job = self.commission
        if self.village.offers.get(job.key, {}).get("status") not in ("open", "bid"):
            self.toast("This contract is no longer open.")
            return
        checks = self.circuit.commission_test_results(job.logic)
        if not all(case.passed for case in checks):
            self.test_results = checks
            self.tested_job = None
            self.tested_snapshot = None
            self.test_message = "The design changed. Fix the red rows and test again."
            return
        before = self.village.coins
        from materials import deliver_project
        delivered, reason = deliver_project(self.village, job.key, mode)
        if not delivered:
            self.delivery_error = reason
            self.delivery_open = True
            self.toast(self.delivery_error)
            return
        self.save_copy(f"{job.customer} approved plan", announce=False,
                       job_key=job.key, delivery_mode=mode)
        self.save_game()
        self.tested_job = None
        self.tested_snapshot = None
        self.delivery_open = False
        self.success_job = job
        self.success_mode = mode
        self.success_payout = self.village.coins - before
        self.toast(f"{job.customer} accepted your {mode} terms! +{self.success_payout} coins.")

    def next_day(self):
        if adventure.active_editor(self):
            self.toast("Field design simulation / village time paused")
            return
        if self.factory_context is not None:
            self.toast("Return to the factory floor before advancing the day.")
            return
        if self.sandbox_context is not None:
            self.toast("The village is paused in sandbox. Return to your job to advance the day.")
            return
        self.village.advance_day(self.town)
        self.save_game()
        self.toast(self.village.last_contract_event or
                   f"Day {self.village.day}: village trades and production updated.")

    def handle_key(self, event):
        if event.key == pygame.K_F11:
            self.toggle_preference("fullscreen")
            return
        if self.focus_navigation(event):
            return
        if self.settings_open:
            if event.key == pygame.K_ESCAPE:
                if self.controls_open:
                    self.controls_open = False
                else:
                    self.close_settings()
            return
        if self.component_info is not None:
            component_info.key(self, event)
            return
        key = event.key
        if self.pause_menu_open:
            if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.pause_menu_open = False
            return
        if chapter_ui.key(self, event):
            return
        if key == pygame.K_b and chapter_ui.can_open(self):
            chapter_ui.open_journal(self)
            return
        if self.scene == "adventure":
            if not adventure.handle_key(self, event) and key == pygame.K_ESCAPE:
                self.pause_menu_open = True
            return
        if self.scene == "boiler_tower":
            if not boiler_tower.handle_key(self, event) and key == pygame.K_ESCAPE:
                self.pause_menu_open = True
            return
        if self.scene == "workshop" and adventure.active_editor(self) and adventure.editor_key(self, event):
            return
        if self.scene == "factory":
            if not factory_ui.handle_key(self, event):
                if key == pygame.K_ESCAPE:
                    self.pause_menu_open = True
                elif key == pygame.K_n:
                    self.next_day()
                elif key == pygame.K_j:
                    self.open_contract_board()
                elif key == pygame.K_l:
                    self.open_ledger()
            return
        if self.pending_design_delete is not None:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.confirm_delete_design()
            elif key == pygame.K_ESCAPE:
                self.pending_design_delete = None
            return
        if self.task_help_open:
            if key == pygame.K_ESCAPE:
                self.task_help_open = False
            return
        if self.timing_results is not None:
            if key == pygame.K_ESCAPE:
                self.timing_results = None
            elif key == pygame.K_t:
                timing_workshop.test(self)
            elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self.scroll_tests((-1 if key in (pygame.K_UP, pygame.K_PAGEUP) else 1) *
                                  (4 if key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN) else 1))
            return
        if self.invention_picker:
            if key == pygame.K_ESCAPE:
                self.invention_picker = False
            return
        if self.invention and self.invention.show_results:
            if key == pygame.K_ESCAPE:
                self.invention.show_results = False
            elif key == pygame.K_t:
                self.test_invention()
            elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self.scroll_tests((-1 if key in (pygame.K_UP, pygame.K_PAGEUP) else 1) *
                                  (4 if key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN) else 1))
            return
        if self.scene == "compute":
            if key == pygame.K_ESCAPE:
                self.close_compute()
            elif key == pygame.K_t:
                self.test_compute()
            elif key == pygame.K_n:
                self.next_day()
            elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self.scroll_tests((-1 if key in (pygame.K_UP, pygame.K_PAGEUP) else 1) *
                                  (4 if key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN) else 1))
            return
        if self.scene == "workshop" and self.port_editor is not None:
            if key == pygame.K_ESCAPE:
                self.port_editor = None
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.finish_ports()
            elif key == pygame.K_TAB:
                self.port_editor["field"] = (self.port_editor["field"] + 1) % len(self.port_editor["keys"])
            elif key == pygame.K_BACKSPACE:
                index = self.port_editor["field"]
                self.port_editor["values"][index] = self.port_editor["values"][index][:-1]
            elif getattr(event, "unicode", "").isprintable():
                index = self.port_editor["field"]
                self.port_editor["values"][index] = (self.port_editor["values"][index] + event.unicode)[:24]
            return
        if self.scene == "workshop" and self.device_stack:
            if key == pygame.K_ESCAPE:
                self.leave_device()
            return
        if self.scene == "workshop" and self.help_open:
            if key in (pygame.K_ESCAPE, pygame.K_h):
                self.help_open = False
            return
        if self.scene == "workshop" and self.delivery_open:
            if key == pygame.K_ESCAPE:
                self.delivery_open = False
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.submit_design(("install", "sell", "license")[key - pygame.K_1])
            return
        if self.scene == "menu":
            if self.menu_page == "new_save":
                if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.finish_new_save_intro()
                return
            if self.menu_page == "introduction":
                if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.menu_page = "title"
                elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.menu_page = "slots"
                return
            if self.menu_page == "title":
                if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.menu_page = "slots"
                elif key == pygame.K_i:
                    self.menu_page = "introduction"
                return
            if self.pending_delete is not None:
                if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.confirm_delete_slot()
                elif key == pygame.K_ESCAPE:
                    self.pending_delete = None
                return
            if pygame.K_1 <= key <= pygame.K_5:
                self.start_slot(key - pygame.K_1 + 1, introduce=True)
            elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.menu_page = "title"
            return
        if self.scene == 'requests':
            if key == pygame.K_ESCAPE:
                self.close_requests()
            elif key in (pygame.K_UP, pygame.K_DOWN):
                from project_ui import visible
                self.request_index = (self.request_index + (1 if key == pygame.K_DOWN else -1)) % max(1, len(visible(self.village)))
            return
        if self.scene == "ledger":
            if key in (pygame.K_ESCAPE, pygame.K_l):
                self.close_ledger()
            elif key == pygame.K_RIGHT:
                index = (ledger.TABS.index(self.ledger_tab) + 1) % len(ledger.TABS)
                self.select_ledger_tab(ledger.TABS[index])
            elif key == pygame.K_LEFT:
                index = (ledger.TABS.index(self.ledger_tab) - 1) % len(ledger.TABS)
                self.select_ledger_tab(ledger.TABS[index])
            elif key in (pygame.K_DOWN, pygame.K_UP) and self.ledger_tab in ("Businesses", "People", "Inventors"):
                from inventor_roster import roster
                count = (len(roster(self.village)) if self.ledger_tab == 'Inventors' else
                         len(self.village.businesses) if self.ledger_tab == "Businesses" else len(self.village.citizens))
                self.ledger_index = (self.ledger_index + (1 if key == pygame.K_DOWN else -1)) % count
            elif key in (pygame.K_DOWN, pygame.K_UP) and self.ledger_tab == "Trade":
                self.shift_trade_day(1 if key == pygame.K_UP else -1)
            elif key == pygame.K_j:
                self.open_contract_board()
            elif key == pygame.K_c:
                self.open_compute()
            elif key == pygame.K_n:
                self.next_day()
            return
        if self.scene == "contracts":
            if key in (pygame.K_ESCAPE, pygame.K_j):
                self.scene = self.board_return_scene
            elif pygame.K_1 <= key <= pygame.K_3:
                index = self.contract_page * 3 + key - pygame.K_1
                if index < len(COMMISSIONS):
                    self.choose_contract(tuple(COMMISSIONS)[index])
            elif key == pygame.K_RIGHT:
                self.contract_page = min((len(COMMISSIONS) - 1) // 3, self.contract_page + 1)
            elif key == pygame.K_LEFT:
                self.contract_page = max(0, self.contract_page - 1)
            return
        if self.scene == "town":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not self.town_dialogue and not self.shannon.open:
                pending = opening_chapter.pending(self.village)
                if pending:
                    chapter_ui.start_scene(self, pending)
                    return
            if key == pygame.K_h:
                self.shannon.toggle(self)
                return
            if key == pygame.K_ESCAPE and self.shannon.open:
                self.shannon.open = False
                self.shannon.page = None
                return
            if self.shannon.open:
                self.shannon.open = False
                self.shannon.page = None
            if key == pygame.K_i:
                self.open_invention()
            elif key == pygame.K_c:
                self.open_compute()
            elif key == pygame.K_j:
                self.open_contract_board()
            elif key == pygame.K_l:
                self.open_ledger()
            elif key == pygame.K_m:
                self.open_ledger()
                self.select_ledger_tab("Map")
            elif key == pygame.K_5 and self.town_dialogue:
                npc = self.town_dialogue[7:] if self.town_dialogue.startswith('person:') else self.village.businesses.get("east_bakery", {}).get("owner", "Jun") if self.town_dialogue == "east_bakery" else None
                self.open_requests(npc)
            elif key == pygame.K_6 and self.town_dialogue and self.town_dialogue.startswith('person:'):
                self.talk_journey(self.town_dialogue[7:])
            elif self.town_dialogue and self.town_dialogue.startswith("person:") and key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.town_topic = {pygame.K_1: "work", pygame.K_2: "family", pygame.K_3: "town", pygame.K_4: "hopes"}[key]
                self.village.talk_to(self.town_dialogue[7:], self.town_topic)
                self.save_game()
            elif key == pygame.K_e:
                if not (self.town_dialogue and self.town_dialogue.startswith("person:")):
                    self.interact_town()
            elif key == pygame.K_n and self.town_dialogue in (None, "market"):
                self.next_day()
            elif key == pygame.K_ESCAPE:
                if self.town_dialogue is not None:
                    self.town_dialogue = None
                else:
                    self.pause_menu_open = True
            return
        if self.success_job is not None:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.success_job = None
                self.scene = "town"
            elif key == pygame.K_ESCAPE:
                self.success_job = None
            return
        if self.test_results is not None:
            if self.task_help_open:
                if key == pygame.K_ESCAPE:
                    self.task_help_open = False
            elif key == pygame.K_ESCAPE:
                self.test_results = None
            elif key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.scroll_tests(4 if key == pygame.K_PAGEDOWN else 1)
            elif key in (pygame.K_UP, pygame.K_PAGEUP):
                self.scroll_tests(-4 if key == pygame.K_PAGEUP else -1)
            elif key == pygame.K_t:
                self.test_commission()
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.submission_ready:
                self.open_delivery_choices()
            return
        if key == pygame.K_n:
            self.next_day()
        elif key == pygame.K_i:
            self.invention_picker = True
        elif key == pygame.K_c:
            self.open_compute()
        elif key == pygame.K_ESCAPE:
            if self.trace_source is not None:
                workshop_floor.cancel(self)
            elif self.factory_context is not None:
                factory_controller.leave(self)
            elif self.timing_key is not None:
                timing_workshop.leave(self)
            elif self.invention:
                self.close_invention()
            elif self.sandbox_context is not None:
                self.open_factory()
            else:
                self.pause_menu_open = True
        elif pygame.K_1 <= key <= pygame.K_5:
            self.select_part(("TRACE", "AND", "OR", "NOT", "XOR")[key - pygame.K_1])
            self.tab = "BUILD"
        elif key == pygame.K_y:
            self.select_part("ERASE")
            self.tab = "BUILD"
        elif key == pygame.K_r:
            self.rotation = (self.rotation + 1) % 4
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_PERIOD:
            self.circuit.tick()
        elif key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.tick_interval = max(0.04, self.tick_interval / 1.5)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.tick_interval = min(1.0, self.tick_interval * 1.5)
        elif key == pygame.K_t:
            self.test_commission()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.open_delivery_choices()
        elif key == pygame.K_s and not (event.mod & pygame.KMOD_CTRL):
            self.save_copy()
        elif key == pygame.K_v:
            self.tab = "VILLAGE"
        elif key == pygame.K_l:
            self.tab = "LIBRARY"
        elif key == pygame.K_g:
            self.open_ledger()
        elif key == pygame.K_b:
            self.tab = "BUILD"
        elif key == pygame.K_j:
            self.open_contract_board()
        elif key == pygame.K_h:
            self.help_open = True

    def update(self, dt):
        if self.opening_screen is not None:
            self.opening_screen.update(dt)
            if self.opening_screen.finished:
                self.opening_screen = None
                self.opening_reveal = 0.5 if not self.reduced_motion else 0.0
            return
        self.opening_reveal = max(0.0, self.opening_reveal - min(max(dt, 0.0), 0.1))
        self.town.reduced_motion = self.reduced_motion
        if self.pause_menu_open or self.settings_open or self.component_info is not None or chapter_ui.active(self):
            return
        if self.reduced_motion:
            self.shannon.motion = float(self.shannon.open)
        self.shannon.update(dt)
        if self.scene != "menu" and self.sandbox_context is None and self.factory_context is None and not adventure.active_editor(self):
            from daily_life import update_continuous
            # A suspended window must not spend days of wages and deadlines
            # in one catch-up frame when the player returns.
            crossed = update_continuous(self.village, self.town, min(max(dt, 0), 1.0))
            if crossed:
                self.save_game()
                self.toast(f"Good morning! Day {self.village.day}. " +
                           (self.village.last_contract_event or "The village is starting a fresh day."))
            self.town.update_visuals(dt)
        if self.scene == "menu":
            pass
        elif self.scene == "adventure":
            adventure.update(self, dt)
        elif self.scene == "boiler_tower":
            boiler_tower.update(self, dt)
        elif self.scene == "town":
            if self.town_dialogue is None and not self.shannon.open:
                self.town.move(pygame.key.get_pressed(), dt)
            else:
                self.town.rest(dt)
        elif self.scene == "workshop" and not self.paused and not self.help_open:
            self.elapsed += dt
            while self.elapsed >= self.tick_interval:
                self.circuit.tick()
                self.elapsed -= self.tick_interval
        if self.scene != "menu":
            factory_shannon.update(self, dt)
        if self.message_timer > 0:
            self.message_timer -= dt

    def draw_background(self):
        ui_theme.backdrop(self.screen)
        rounded(self.screen, (49, 63, 62), (28, 20, 1224, 720), 5)
        rounded(self.screen, (124, 75, 58), (35, 27, 1210, 705), 5, 7)
        rounded(self.screen, (84, 59, 48), (48, 38, 1184, 87), 4)
        rounded(self.screen, (112, 80, 58), (55, 45, 1170, 73), 3, 3)
        for x in (70, 1210):
            for y in (56, 105):
                pygame.draw.circle(self.screen, GOLD, (x, y), 4)
                pygame.draw.circle(self.screen, (95, 64, 47), (x, y), 2)
        text(self.screen, self.heading, "WORKSHOP", 87, 66, PAPER)
        job_label = ("FIELD / " + adventure.specification(self)[0].upper() if adventure.active_editor(self) else "FACTORY / CONTROLLER" if self.factory_context is not None else "TIMING / " + self.timing_key.upper() if self.timing_key else "SANDBOX / FREE BUILD" if self.sandbox_context is not None else f"INVENT / {'/'.join(self.invention.challenge.unlocks)}" if self.invention else
                     f"COMPUTE / {computation.JOBS[self.active_compute].owner.upper()}" if self.active_compute else
                     f"JOB {self.commission.level} / {len(COMMISSIONS)}  /  {self.commission.customer.upper()}")
        text(self.screen, self.small, job_label, 310, 62, CREAM, width=365)
        text(self.screen, self.tiny, f"DAY {self.village.day}   /   {self.village.coins} COINS", 310, 87, CREAM, width=365)

    def draw_avatar(self, cx, cy):
        pygame.draw.ellipse(self.screen, (129, 105, 70), (cx - 24, cy + 22, 48, 11))
        pygame.draw.rect(self.screen, TEAL, (cx - 14, cy + 4, 28, 25))
        pygame.draw.rect(self.screen, (74, 52, 48), (cx - 13, cy - 16, 26, 25))
        pygame.draw.rect(self.screen, (232, 180, 130), (cx - 10, cy - 11, 20, 17))
        pygame.draw.rect(self.screen, (60, 45, 42), (cx - 7, cy - 3, 3, 3))
        pygame.draw.rect(self.screen, (60, 45, 42), (cx + 5, cy - 3, 3, 3))
        pygame.draw.rect(self.screen, COPPER, (cx - 18, cy - 20, 36, 8))

    def draw_board(self):
        workshop_floor.prepare(self)
        bx, by, cell = self.board_metrics()
        workshop_floor.draw_board_base(self)
        workshop_floor.draw_traces(self)
        for pos, part in self.circuit.parts.items():
            self.draw_part(pos, part)
        hovered = self.board_pos(self.mouse_pos())
        if hovered:
            x, y = hovered
            pygame.draw.rect(self.screen, GOLD, (bx + x * cell, by + y * cell, cell - 2, cell - 2), 2, border_radius=5)
        if self.factory_context is not None and self.tab == "BUILD" and not self.device_stack:
            workbench.controller_labels(self)

    def draw_part(self, pos, part):
        bx, by, cell = self.board_metrics()
        cx, cy = bx + pos[0] * cell + cell // 2 - 1, by + pos[1] * cell + cell // 2 - 1
        signal = self.circuit.active.get(pos, 0)
        r = int(cell * .36)
        rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        base = TEAL if signal else COPPER
        if pos in self.circuit.terminals:
            base = (78, 119, 127) if signal else (103, 112, 113)
        rounded(self.screen, (86, 66, 54), rect.move(2, 3), 5)
        rounded(self.screen, base, rect, 5)
        rounded(self.screen, COPPER_LIGHT, rect, 5, 2)
        inputs, outputs = part.ports()
        for direction in set(inputs + outputs):
            dx, dy = VECTORS[direction]
            start = (cx + dx * int(cell * .30), cy + dy * int(cell * .30))
            end = (cx + dx * int(cell * .47), cy + dy * int(cell * .47))
            pygame.draw.line(self.screen, TEAL_LIGHT if signal else (87, 79, 70), start, end, 3)
            port_point = workshop_floor.socket(self, pos, direction)
            pygame.draw.circle(self.screen, GOLD if self.trace_source == pos else TEAL_LIGHT if direction in outputs else PAPER, port_point, 5)
            pygame.draw.circle(self.screen, INK, port_point, 5, 1)
            if direction in inputs and self.trace_source is not None:
                pygame.draw.circle(self.screen, GOLD, port_point, 8, 2)
        if part.kind in CONDUCTORS:
            for direction in inputs:
                dx, dy = VECTORS[direction]
                pygame.draw.line(self.screen, PAPER if signal else GOLD, (cx, cy),
                                 (cx + dx * r, cy + dy * r), 3)
        elif part.kind in ('AND', 'OR', 'NOT', 'XOR') and pos not in self.circuit.terminals:
            from gate_symbols import draw_gate
            draw_gate(self.screen, part.kind, (cx, cy), int(cell * .70), PAPER,
                      part.rotation, floor_ports=True)
        else:
            symbol = self.circuit.terminals[pos]["name"] if pos in self.circuit.terminals else workbench.SYMBOLS.get(part.kind, part.kind)
            symbol = symbol[:6]
            show_value = self.numeric_mode or signal > 1 or part.kind in (*ARITHMETIC, *SEQUENTIAL, *UTILITY) or pos in self.circuit.terminals
            rendered = self.small.render(symbol, True, PAPER)
            self.screen.blit(rendered, rendered.get_rect(center=(cx, cy - 7 if show_value else cy)))
            if show_value:
                value = self.circuit.switches[self.circuit.terminals[pos]["name"]] if pos in self.circuit.terminals and not self.circuit.terminals[pos]["output"] else signal
                rendered = self.tiny.render(str(int(value)), True, PAPER)
                self.screen.blit(rendered, rendered.get_rect(center=(cx, cy + 9)))

    def draw_status(self):
        width = 866 if self.tab == "BUILD" and not self.device_stack else 688
        rounded(self.screen, CREAM, (42, 662, width, 62), 4)
        rounded(self.screen, (95, 67, 50), (42, 662, width, 62), 4, 3)
        icon = ">" if not self.paused else "||"
        text(self.screen, self.font, f"{icon}  tick {self.circuit.tick_count:03d}", 76, 675)
        text(self.screen, self.small, f"{1 / self.tick_interval:.1f} steps/s", 260, 679, MUTED)
        self.button((420, 674, 92, 36), "Pause" if not self.paused else "Run", lambda: setattr(self, "paused", not self.paused), small=True)
        self.button((520, 674, 82, 36), "Step", self.circuit.tick, small=True)
        self.button((610, 674, 110, 36), "Reset", self.circuit.reset, small=True)
        if width > 688:
            output_count = sum(port["output"] for port in self.circuit.terminals.values())
            label = f"OUT {self.circuit.output_value()}" if output_count == 1 else f"{output_count} outputs"
            text(self.screen, self.small, label, 746, 684, TEAL)

    def draw_panel_shell(self):
        rounded(self.screen, (103, 70, 52), (PANEL_X - 5, 131, 468, 598), 4)
        rounded(self.screen, PAPER, (PANEL_X, 136, 458, 588), 3)
        for x in (PANEL_X + 10, PANEL_X + 448):
            for y in (144, 711):
                pygame.draw.circle(self.screen, COPPER, (x, y), 3)
        for i, tab in enumerate(("BUILD", "VILLAGE", "LIBRARY")):
            self.button((PANEL_X + 15 + i * 147, 148, 138, 39), tab.title(), lambda t=tab: setattr(self, "tab", t), active=self.tab == tab, small=True)

    def draw_build_panel(self):
        workbench.panel(self)

    def draw_help_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 180))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (112, 73, 55), (178, 107, 924, 548), 4)
        rounded(self.screen, PAPER, (186, 115, 908, 532), 3)
        text(self.screen, self.big, "WORKSHOP HELP", 221, 147, TEAL)
        text(self.screen, self.small, "BUILD", 225, 212, COPPER)
        self.draw_lines((
            "1 Trace; 2 AND; 3 OR; 4 NOT; 5 XOR; Y erases.",
            "Place components on the floor. Click an output socket to start a trace.",
            "Click floor corners, then an input socket. Crossings never join.",
            "Right-click an input socket to disconnect; Esc cancels a trace.",
            "Right-click a component to rotate or inspect a device. R rotates held parts.",
            "Number inputs: click +/-1; Shift +/-16; Ctrl +/-256 (0-65535).",
        ), 225, 244, self.small, 27)
        text(self.screen, self.small, "TEST & NAVIGATE", 225, 400, COPPER)
        self.draw_lines((
            "T reads live sequential output, or settled combinational output." if self.sandbox_context is not None else "T tests the current contract, calculator, invention or timing goal.",
            "Space pauses the circuit; . steps; + and - change circuit speed.",
            "S saves a version; B/V/L change tabs; J opens contracts.",
            "Esc returns to your factory floor." if self.factory_context is not None else "Esc leaves this editor; Esc in town opens the pause menu." if self.sandbox_context is not None or self.timing_key is not None else "Esc pauses; use Back to Town in the pause menu.",
            "Sandbox pauses village time. All components are free to try here." if self.sandbox_context is not None else "N finishes today's remaining activity. Residents also work while you build.",
        ), 225, 432, self.small, 31)
        self.button((874, 596, 190, 43), "CLOSE  [H/ESC]", lambda: setattr(self, "help_open", False), active=True, small=True)

    def draw_lines(self, lines, x, y, font=None, spacing=22, color=INK):
        font = font or self.small
        for i, line in enumerate(lines):
            text(self.screen, font, line, x, y + spacing * i, color, width=(1228 - x - 20) if x >= PANEL_X else SCREEN_W - x - 40)

    def draw_village_panel(self):
        workbench.village_panel(self)

    def draw_library_panel(self):
        workbench.library_panel(self)

    def draw_design_delete_confirmation(self):
        item = self.designs[self.pending_design_delete]
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 180))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, PAPER, (350, 235, 580, 258), 8)
        text(self.screen, self.heading, "DELETE SAVED DESIGN?", 390, 265, RED)
        text(self.screen, self.font, f"{item.get('name', 'Design')[:32]} / v{item.get('version', 1)}", 390, 312)
        self.draw_lines(["Removes this version from Library.",
                         "Floor, device copies and delivered machines stay."], 390, 355, self.small, 25)
        self.buttons.clear()
        self.button((394, 423, 205, 43), "CANCEL  [ESC]", lambda: setattr(self, "pending_design_delete", None), small=True)
        self.button((681, 423, 205, 43), "DELETE  [ENTER]", self.confirm_delete_design, small=True, danger=True)

    def draw_test_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 165))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (112, 73, 55), (293, 75, 694, 610), 4)
        rounded(self.screen, PAPER, (301, 83, 678, 594), 3)
        passed = all(case.passed for case in self.test_results)
        count = sum(case.passed for case in self.test_results)
        text(self.screen, self.heading, f"{count} / {len(self.test_results)} CHECKS PASSED", 325, 100, TEAL if passed else RED)
        text(self.screen, self.tiny, self.commission.title, 766, 108, MUTED, width=188)
        text(self.screen, self.small, self.test_message, 325, 139, TEAL if passed else RED, width=630)
        rounded(self.screen, (223, 209, 176), (325, 169, 630, 40), 3)
        text(self.screen, self.small, "A", 349, 179)
        text(self.screen, self.small, "B", 438, 179)
        if any(len(case.inputs) > 2 for case in self.test_results):
            text(self.screen, self.small, "C", 488, 179)
        text(self.screen, self.small, "Needed", 533, 179)
        text(self.screen, self.small, "Your lamp", 666, 179)
        text(self.screen, self.small, "Result", 836, 179)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(319, 213, 642, 310))
        visible_rows = 8
        for row in range(visible_rows):
            i = self.test_scroll + row
            if i >= len(self.test_results):
                break
            case = self.test_results[i]
            y = 216 + row * 38
            rounded(self.screen, (224, 239, 220) if case.passed else (248, 217, 201), (325, y, 630, 33), 3)
            text(self.screen, self.font, int(case.inputs[0]), 351, y + 6)
            text(self.screen, self.font, int(case.inputs[1]), 440, y + 6)
            if len(case.inputs) > 2:
                text(self.screen, self.font, int(case.inputs[2]), 490, y + 7)
            text(self.screen, self.font, int(case.expected), 549, y + 6)
            text(self.screen, self.font, int(case.actual), 697, y + 6)
            text(self.screen, self.small, "PASS" if case.passed else "FAIL", 837, y + 7, TEAL if case.passed else RED)
        self.screen.set_clip(old_clip)
        first_row = min(len(self.test_results), self.test_scroll + 1)
        last_row = min(len(self.test_results), self.test_scroll + visible_rows)
        text(self.screen, self.tiny, f"Rows {first_row}-{last_row} / {len(self.test_results)}   UP/DOWN or mouse wheel to scroll", 325, 526, MUTED)
        if not passed:
            kinds = {part.kind for part in self.circuit.parts.values()}
            if self.commission.logic == "AND" and "OR" in kinds and "AND" not in kinds:
                hint = "An OR valve runs for either input. This job needs AND."
            elif self.commission.logic == "OR" and "AND" in kinds and "OR" not in kinds:
                hint = "An AND valve needs both inputs. This job needs OR."
            else:
                hint = "Follow a red row with Step and check each valve."
            text(self.screen, self.small, hint, 325, 551, RED, width=630)
        elif self.submission_ready:
            text(self.screen, self.small, "Choose how to deliver this working design.", 325, 551, TEAL)
        self.button((357, 627, 175, 39), "Close  [Esc]", lambda: setattr(self, "test_results", None), small=True)
        self.button((548, 627, 184, 39), "TASK DETAILS", lambda: setattr(self, "task_help_open", True), small=True)
        self.button((754, 627, 201, 39), "DELIVERY [ENTER]", self.open_delivery_choices, active=self.submission_ready, small=True, enabled=self.submission_ready)

    def task_description(self):
        if adventure.active_editor(self):
            return adventure.specification(self)
        if self.factory_context is not None:
            return factory_controller.description(self)
        if self.timing_key is not None:
            challenge = sequential.CHALLENGES[self.timing_key]
            return challenge.title, list(challenge.description)
        if self.sandbox_context is not None:
            return "Sandbox", ["Experiment with every component and save designs in your Library.",
                               "Click inputs to change values. Space runs the circuit; period steps one tick. T reads live sequential output or settled combinational output.",
                               "Switch between binary and number inputs, or add a third input. The village clock pauses here. Returning to your job restores its floor; earned blocks are still required there."]
        if self.invention:
            challenge = self.invention.challenge
            return challenge.title, [" ".join(challenge.lesson),
                                     "Inputs: " + ", ".join(challenge.inputs) + ".",
                                     "Outputs: " + ", ".join(challenge.outputs) + ".",
                                     "Each input and output is a single binary bit (0 or 1)."]
        if self.scene == "compute" or self.active_compute:
            job = computation.JOBS[self.compute_key if self.scene == "compute" else self.active_compute]
            return job.title, [job.description,
                               f"Input A: {job.inputs[0]}. Input B: {job.inputs[1]}.",
                               f"Required output: {job.output}.",
                               "Handle requests from 0 to 255; the result can use up to 16 bits."]
        job = self.commission
        from commission_logic import logic_description
        inputs = f"Input A: {job.input_a}. Input B: {job.input_b}."
        if job.input_c:
            inputs += f" Input C: {job.input_c}."
        return job.title, [inputs,
                           f"Required output: {job.output}.",
                           logic_description(job.logic),
                           "The required behavior must hold for every row of the test table."]

    def task_detail_lines(self):
        lines = []
        for paragraph in self.task_description()[1]:
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}".strip()
                if line and self.small.render(candidate, True, INK).get_width() > 636:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.extend((line, ""))
        return lines

    def draw_task_help_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 190))
        self.screen.blit(shade, (0, 0))
        self.buttons.clear()
        rounded(self.screen, (112, 73, 55), (272, 147, 736, 496), 4)
        rounded(self.screen, PAPER, (280, 155, 720, 480), 3)
        text(self.screen, self.heading, "WHAT THE MACHINE MUST DO", 320, 185, TEAL)
        text(self.screen, self.font, self.task_description()[0], 322, 226, MUTED)
        self.draw_lines(self.task_detail_lines(), 322, 270, self.small, 23)
        self.button((547, 584, 186, 39), "CLOSE  [ESC]", lambda: setattr(self, "task_help_open", False), small=True)

    def draw_delivery_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 180))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (112, 73, 55), (294, 127, 692, 517), 4)
        rounded(self.screen, PAPER, (302, 135, 676, 501), 3)
        text(self.screen, self.heading, "CHOOSE DELIVERY TERMS", 330, 162, TEAL)
        text(self.screen, self.small, f"{self.commission.title}  /  {self.commission.customer}", 330, 202)
        from materials import material_status
        text(self.screen, self.tiny, material_status(self.village, self.commission.key), 330, 238, TEAL, width=620)
        customer_id = CONTRACTS[self.commission.key][0]
        advance = self.village.material_advances.get(self.commission.key, 0)
        text(self.screen, self.tiny, f"Customer cash {self.village.businesses[customer_id]['cash']}c / advance {advance}c deducted from payout", 330, 264, MUTED, width=620)
        reward = self.commission.reward
        options = (
            ("1  INSTALL / KEEP RIGHTS", f"+{reward - advance} now. Customer owns the machine; you own the design."),
            ("2  SELL A COPY", f"+{reward + max(6, reward // 3) - advance} now. Customer owns a design copy."),
            ("3  LICENSE USE", f"+{reward // 2 - advance} now, then {LICENSE_RATE}/day while the machine operates."),
        )
        for i, (label, detail) in enumerate(options):
            y = 305 + i * 85
            self.button((330, y, 620, 68), "", lambda m=("install", "sell", "license")[i]: self.submit_design(m), small=True)
            text(self.screen, self.small, label, 348, y + 8)
            text(self.screen, self.tiny, detail, 348, y + 39, MUTED)
        if self.delivery_error:
            text(self.screen, self.tiny, self.delivery_error, 330, 558, RED, width=620)
        self.button((824, 584, 128, 37), "BACK [ESC]", lambda: setattr(self, "delivery_open", False), small=True)
        self.button((330, 584, 310, 37), "MATERIAL ADVANCE", self.request_material_advance, small=True)

    def draw_success_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((18, 33, 29, 180))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (111, 75, 51), (293, 170, 694, 443), 4)
        rounded(self.screen, PAPER, (302, 179, 676, 425), 3)
        for x, y in ((325, 200), (935, 205), (352, 468), (914, 462), (410, 238), (865, 250)):
            pygame.draw.rect(self.screen, GOLD, (x, y, 10, 10))
            pygame.draw.rect(self.screen, TEAL_LIGHT, (x + 16, y + 15, 6, 6))
        title = self.big.render(f"LEVEL {self.success_job.level} COMPLETE!", False, TEAL)
        self.screen.blit(title, title.get_rect(center=(640, 224)))
        subtitle = self.heading.render(f"{self.success_job.customer} accepted your machine", False, INK)
        self.screen.blit(subtitle, subtitle.get_rect(center=(640, 278)))
        rounded(self.screen, (236, 204, 126), (438, 321, 404, 77), 3)
        reward = self.big.render(f"+{self.success_payout} COINS", False, (99, 64, 37))
        self.screen.blit(reward, reward.get_rect(center=(640, 340)))
        if self.success_job.key == "mill":
            effects = ("Mill output: 1 to 4 flour per day", "Bakery commission unlocked in town")
        elif self.success_job.key == "bakery":
            effects = ("Bakery capacity: 3 to 5 bread per day", "More bread can reach the village")
        elif self.success_job.key == "vent":
            effects = ("Bakery boiler stays online every seventh day", "No shutdown loss when bread is needed")
        elif self.success_job.key == "pump":
            effects = ("Farm pumping improves daily grain capacity", "More grain can reach the mill")
        elif self.success_job.key == "sorter":
            effects = ("Market sorting improves bread distribution", "Your three-input controller is now installed")
        else:
            effects = ("Market cooling protects one loaf every sixth day", "Less spoiled bread reaches the price calculation")
        self.draw_lines(effects, 405, 420, self.small, 28, TEAL)
        rights = {"install": "You keep the design rights.", "sell": "Customer owns a copy; your original stays yours.",
                  "license": f"You own the design; earn {LICENSE_RATE} coins per paid day."}[self.success_mode]
        text(self.screen, self.tiny, rights, 405, 493, MUTED)
        self.button((354, 548, 270, 43), "Keep building  [Esc]", lambda: setattr(self, "success_job", None), small=True)
        self.button((655, 548, 270, 43), "Return to town  [Enter]", lambda: setattr(self, "scene", "town"), active=True, small=True)

    def draw_menu(self):
        if self.menu_page == "slots":
            self.draw_save_slots()
        elif self.menu_page == "introduction":
            self.draw_introduction()
        elif self.menu_page == "new_save":
            self.draw_introduction(new_save=True)
        else:
            self.draw_title_menu()

    def centered_text(self, font, content, y, color=INK):
        rendered = font.render(content, True, color)
        self.screen.blit(rendered, rendered.get_rect(midtop=(SCREEN_W // 2, y)))

    def draw_title_menu(self):
        ui_theme.backdrop(self.screen)
        # The living village gives the title a place without adding more lore text.
        if not hasattr(self, "title_village"):
            import scene_depth
            if self.town.background is None:
                self.town.draw(pygame.Surface((1280, 760)),
                               (self.small, self.font, self.heading, self.big), self.village, None, "")
            view = self.town.background.copy()
            scene_depth.draw(view, (0, 0), self.town.scenery_props)
            self.title_village = pygame.transform.scale(view, (1280, 740))
        self.screen.blit(self.title_village, (0, 20))
        veil = pygame.Surface((1280, 760), pygame.SRCALPHA)
        veil.fill((17, 38, 41, 205))
        self.screen.blit(veil, (0, 0))
        pygame.draw.rect(self.screen, (147, 130, 82), (28, 28, 1224, 704), 1, border_radius=5)
        ui_theme.mill_seal(self.screen, (640, 166), 39)
        self.centered_text(self.menu_title, "NUMBERMILL", 228, PAPER)
        pygame.draw.line(self.screen, (135, 124, 88), (480, 295), (800, 295))
        if not hasattr(self, "title_continue_slot"):
            self.title_continue_slot = self.continue_slot()
        slot = self.title_continue_slot
        self.button((440, 335, 400, 49), "Continue" if slot else "New game",
                    (lambda s=slot: self.start_slot(s)) if slot else self.new_game, active=True)
        if slot:
            self.button((440, 399, 194, 43), "Load game", lambda: setattr(self, "menu_page", "slots"))
            self.button((646, 399, 194, 43), "New game", self.new_game)
        else:
            self.button((440, 399, 400, 43), "Load game", lambda: setattr(self, "menu_page", "slots"))
        self.button((440, 457, 400, 43), "Settings", self.open_settings)
        self.button((440, 515, 400, 43), "Read introduction", lambda: setattr(self, "menu_page", "introduction"))
        self.button((535, 586, 210, 41), "Exit game", self.exit_game, small=True)
        self.centered_text(self.tiny, "by Luca Molinari", 682, (207, 195, 159))

    def draw_introduction(self, new_save=False):
        ui_theme.backdrop(self.screen)
        rounded(self.screen, (49, 63, 62), (145, 27, 990, 707), 5)
        rounded(self.screen, (124, 75, 58), (153, 35, 974, 691), 4, 7)
        rounded(self.screen, PAPER, (173, 51, 934, 655), 3)
        # A simple parchment scroll introduces the player without locking in deeper lore.
        rounded(self.screen, (222, 197, 151), (287, 168, 706, 420), 12)
        rounded(self.screen, (145, 88, 57), (287, 168, 706, 420), 12, 3)
        rounded(self.screen, (240, 222, 184), (310, 187, 660, 382), 8)
        rounded(self.screen, (145, 88, 57), (298, 177, 684, 18), 8)
        rounded(self.screen, (145, 88, 57), (298, 561, 684, 18), 8)
        self.centered_text(self.heading, "A SMALL BEGINNING", 218, TEAL)
        self.draw_lines([
            "You are Boole, a young inventor in Copperside.",
            "Here, steam turns the wheels of everyday life.",
            "A small workshop is yours to make something of.",
            "Build useful machines. Help your neighbours.",
            "Beyond the village, old mechanisms still wait.",
            "Who built them, and what might they reveal?",
            "With Shannon beside you, follow your curiosity.",
        ], 357, 280, font=self.font, spacing=33, color=INK)
        if new_save:
            self.button((490, 622, 300, 45), "BEGIN  [Enter]", self.finish_new_save_intro, active=True, small=True)
        else:
            self.button((390, 631, 220, 45), "BACK", lambda: setattr(self, "menu_page", "title"), small=True)
            self.button((670, 631, 220, 45), "LOAD GAME", lambda: setattr(self, "menu_page", "slots"), active=True, small=True)

    def draw_save_slots(self):
        ui_theme.backdrop(self.screen)
        rounded(self.screen, (49, 63, 62), (145, 27, 990, 707), 5)
        rounded(self.screen, (124, 75, 58), (153, 35, 974, 691), 4, 7)
        rounded(self.screen, PAPER, (173, 51, 934, 655), 3)
        text(self.screen, self.big, "NUMBERMILL", 212, 77, TEAL)
        # A brass mill-wheel seal makes the archive feel part of the village.
        ui_theme.mill_seal(self.screen, (1024, 115), 32)
        pygame.draw.line(self.screen, (212, 189, 144), (212, 145), (958, 145), 1)
        text(self.screen, self.small, "Welcome back, Boole. Your workshop is ready.", 212, 121, COPPER)
        for slot in range(1, SLOT_COUNT + 1):
            data = load_slot(slot)
            y = 194 + (slot - 1) * 84
            rounded(self.screen, (226, 211, 179), (206, y, 868, 72), 3)
            text(self.screen, self.heading, f"SLOT {slot}", 226, y + 12, INK)
            if data == "unreadable":
                detail = "Unreadable save - file preserved"
            elif data is None:
                detail = "Empty slot"
            else:
                saved = data["village"]
                workshop = saved.get("manufacturing", {})
                tower = workshop.get("boiler_tower", {})
                field = workshop.get("adventure", {})
                chapter = ("Tower recovered" if tower.get("complete") else
                           "Boiler Tower" if tower.get("visited") else
                           "Mosswater archive" if field.get("expansion_complete") else
                           "Exploring Mosswater" if field.get("visited") else "Copperside")
                detail = f"Day {saved.get('day', 1)}  /  {saved.get('coins', 12)} coins  /  {chapter}"
                if data.get("legacy"):
                    detail += "  /  Existing save"
            text(self.screen, self.tiny, detail, 230, y + 46, MUTED if data is None else TEAL, width=590)
            if data is None:
                self.button((843, y + 14, 203, 43), "CREATE", lambda s=slot: self.start_slot(s, introduce=True), active=True, small=True)
            else:
                self.button((843, y + 14, 117, 43), "LOAD", lambda s=slot: self.start_slot(s), active=data != "unreadable", small=True, enabled=data != "unreadable")
                self.button((968, y + 14, 78, 43), "DELETE", lambda s=slot: self.request_delete_slot(s), small=True)
        text(self.screen, self.tiny, self.message[:95] if self.message_timer > 0 else "Progress saves when you return to this menu.", 212, 626, MUTED)
        self.button((610, 651, 203, 40), "BACK", lambda: setattr(self, "menu_page", "title"), small=True)
        self.button((843, 651, 203, 40), "EXIT GAME", lambda: setattr(self, "running", False), small=True)
        text(self.screen, self.tiny, "Press 1-5 for a slot. Esc returns to the title.", 212, 661, MUTED)
        if self.pending_delete is not None:
            self.draw_delete_confirmation()

    def draw_delete_confirmation(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 175))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (112, 73, 55), (350, 233, 580, 268), 4)
        rounded(self.screen, PAPER, (358, 241, 564, 252), 3)
        text(self.screen, self.heading, f"DELETE SLOT {self.pending_delete}?", 390, 268, RED)
        text(self.screen, self.small, "Progress and designs in this slot will be removed.", 390, 324)
        if self.pending_delete == 1 and SAVE_FILE.exists():
            text(self.screen, self.tiny, "Original save.json files stay on disk but stay hidden.", 390, 354, MUTED)
        else:
            text(self.screen, self.tiny, "This cannot be undone from the game.", 390, 354, MUTED)
        self.button((394, 423, 205, 43), "CANCEL  [ESC]", lambda: setattr(self, "pending_delete", None), small=True)
        self.button((681, 423, 205, 43), "DELETE  [ENTER]", self.confirm_delete_slot, small=True, danger=True)

    def draw_contract_board(self):
        ui_theme.backdrop(self.screen)
        rounded(self.screen, (112, 73, 55), (75, 35, 1130, 688), 4)
        rounded(self.screen, PAPER, (86, 46, 1108, 666), 3)
        text(self.screen, self.big, "VILLAGE CONTRACTS", 120, 75, TEAL)
        self.button((120, 112, 250, 34), 'NEIGHBOR REQUESTS', self.open_requests, small=True)
        jobs = list(COMMISSIONS.values())
        self.contract_page = min(self.contract_page, (len(jobs) - 1) // 3)
        for row, job in enumerate(jobs[self.contract_page * 3:self.contract_page * 3 + 3]):
            y = 161 + row * 152
            offer = self.village.offers.get(job.key)
            state = offer["status"] if offer else "waiting"
            locked = state == "waiting"
            from inventor_roster import name_for_offer
            inventor = name_for_offer(self.village, offer or {})
            status = {"player": "YOU DELIVERED", "rival": f"{inventor.upper()} DELIVERED",
                      "bid": f"{inventor.upper()} BID", "open": "AVAILABLE", "waiting": "WAITING"}[state]
            rounded(self.screen, (231, 218, 185), (113, y, 1052, 143), 3)
            text(self.screen, self.heading, f"{job.level}. {job.title}", 135, y + 8, width=820)
            text(self.screen, self.tiny, status, 985, y + 13, MUTED if locked else TEAL, width=170)
            timing = (f"Due {offer['due_day']} / {inventor} {offer['finish_day']}" if state == "bid" else
                      f"Due day {offer['due_day']}" if state == "open" else
                      "Delivered late" if state in ("player", "rival") and offer.get("missed_deadline") else
                      "Delivered" if state in ("player", "rival") else
                      "Awaiting business demand")
            text(self.screen, self.small, f"{job.customer}  /  {job.reward} coins  /  {timing}", 135, y + 39, COPPER)
            from materials import material_bill
            bill = ', '.join(f'{count} {good}' for good, count in material_bill(job.key).items())
            text(self.screen, self.tiny, f"{job.logic.replace('_', ' ')} / {8 if job.input_c else 4} checks / Delivery: {bill}", 135, y + 64, width=1000)
            text(self.screen, self.small, job.benefit, 135, y + 88, TEAL, width=714)
            if locked:
                prerequisite = COMMISSIONS.get(job.prerequisite)
                note = (f"First: {prerequisite.title}." if prerequisite and not self.contract_complete(prerequisite.key)
                        else f"Available from day {job.unlock_day}, when the business can fund it.")
            elif state in ("open", "bid"):
                note = offer["reason"]
            elif offer.get("delivery_mode") == "license":
                paid = self.village.licenses.get(job.key, {}).get("paid_day") == self.village.day
                note = f"Design: Boole  /  Licensed to {offer['licensee']} for {LICENSE_RATE}/day ({'active' if paid else 'paused'})."
            elif offer.get("copy_owner"):
                note = f"Design: {offer['design_owner']}  /  {offer['copy_owner']} owns a copy."
            else:
                note = f"Design: {offer['design_owner']}  /  Installed machine belongs to {job.customer}."
            text(self.screen, self.tiny, note, 135, y + 117, MUTED, width=714)
            self.button((873, y + 91, 265, 40), f"{'REVISIT' if state in ('player', 'rival') else 'BUILD DESIGN'} [{row + 1}]", lambda k=job.key: self.choose_contract(k), active=not locked, enabled=not locked, small=True)
        if self.contract_page > 0:
            self.button((484, 644, 165, 43), "PREV  [LEFT]", lambda: setattr(self, "contract_page", self.contract_page - 1), small=True)
        if (self.contract_page + 1) * 3 < len(jobs):
            self.button((676, 644, 165, 43), "NEXT  [RIGHT]", lambda: setattr(self, "contract_page", self.contract_page + 1), active=True, small=True)
        self.button((894, 644, 242, 43), "BACK  [ESC]", lambda: setattr(self, "scene", self.board_return_scene), small=True)
        text(self.screen, self.tiny, f"Page {self.contract_page + 1}/{(len(jobs) + 2) // 3}  /  1-3 choose on this page", 135, 657, MUTED)

    def exit_game(self):
        if self.scene != "menu":
            self.return_to_menu()
        self.save_preferences()
        self.running = False

    def pause_entries(self):
        entries = [('Resume  [Enter / Esc]', lambda: setattr(self, 'pause_menu_open', False)),
                   ('Settings', self.open_settings)]
        if self.scene in ("workshop", "factory"):
            entries.append(('Back to Town', self.resume_in_town))
        entries.extend([('Back to Main Menu', self.return_to_menu), ('Exit Game', self.exit_game)])
        entries.append(('Developer mode: ' + ('ON' if developer_mode.enabled(self) else 'OFF'),
                        lambda: developer_mode.toggle(self)))
        return entries

    def pause_buttons(self):
        return [(pygame.Rect(460, 248 + i * 53, 360, 42), action)
                for i, (_, action) in enumerate(self.pause_entries())]

    def resume_in_town(self):
        if adventure.active_editor(self):
            adventure.close_editor(self)
        if self.factory_context is not None:
            factory_controller.leave(self)
        self.pause_menu_open = False
        self.scene = "town"

    def draw(self):
        if self.opening_screen is not None:
            self.buttons.clear()
            self.opening_screen.draw(self.screen, self.heading, self.menu_title)
            self.viewport.present()
            return
        context = (self.scene, self.menu_page, self.pause_menu_open, self.settings_open, self.controls_open)
        if context != self.focus_context:
            self.focus_index = -1
            self.focus_context = context
            if self.scene == "menu" and self.menu_page == "title":
                self.__dict__.pop("title_continue_slot", None)
        self.draw_scene()
        if self.scene in ('adventure', 'boiler_tower') and chapter_ui.can_open(self):
            self.button(chapter_ui.JOURNAL_BUTTON, 'Field journal [B]', lambda: chapter_ui.open_journal(self), small=True)
        if self.scene == 'factory' and chapter_ui.can_open(self):
            self.button((490, 92, 270, 30), 'Field journal [B]', lambda: chapter_ui.open_journal(self), small=True)
        developer_mode.draw(self)
        if self.scene == "workshop" and adventure.active_editor(self):
            adventure.draw_specification(self)
        if self.component_info is not None:
            component_info.draw(self)
        chapter_ui.draw(self)
        if self.pause_menu_open:
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((20, 29, 29, 185))
            self.screen.blit(shade, (0, 0))
            rounded(self.screen, PAPER, (390, 170, 500, 480), 12)
            text(self.screen, self.heading, "Paused", 460, 197, TEAL)
            self.buttons.clear()
            labels = [label for label, _ in self.pause_entries()]
            for label, (rect, action) in zip(labels, self.pause_buttons()):
                self.button(rect, label, action, small=True)
            text(self.screen, self.tiny, "Your village and machines are paused.", 460, 589, MUTED)
            text(self.screen, self.tiny, "Tab to select  /  Enter to confirm", 460, 613, MUTED)
        if self.settings_open:
            self.buttons.clear()
            if self.controls_open:
                presentation.draw_controls(self)
            else:
                presentation.draw_settings(self)
        if self.opening_reveal:
            veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            veil.fill((8, 16, 20, round(255 * self.opening_reveal / 0.5)))
            self.screen.blit(veil, (0, 0))
        self.viewport.present()

    def draw_scene(self):
        self.buttons.clear()
        if self.scene == "adventure":
            adventure.draw(self)
            return
        if self.scene == "boiler_tower":
            boiler_tower.draw(self)
            return
        if self.scene == "factory":
            factory_ui.draw(self)
            return
        if self.scene == 'requests':
            from project_ui import draw
            draw(self)
            return
        if self.scene == "compute":
            workbench.compute_screen(self)
            if self.task_help_open:
                self.draw_task_help_modal()
            return
        if self.scene == "contracts":
            self.draw_contract_board()
            return
        if self.scene == "ledger":
            ledger.draw(self)
            return
        if self.scene == "menu":
            self.draw_menu()
            return
        if self.scene == "town":
            self.town.draw(
                self.screen,
                (self.small, self.font, self.heading, self.big),
                self.village,
                self.town_dialogue,
                self.message if self.message_timer > 0 else "",
                self.town_topic,
            )
            self.shannon.draw(self)
            if self.town_dialogue and self.town_dialogue.startswith('person:'):
                name = self.town_dialogue[7:]
                if name in opening_chapter.PEOPLE:
                    self.button((830, 430, 183, 35), 'Journey [6]', lambda n=name: self.talk_journey(n),
                                active=self.town_topic == 'journey', small=True)
            chapter_ui.draw_prompt(self)
            return
        if self.device_stack:
            self.draw_background()
            self.draw_board()
            self.draw_status()
            rounded(self.screen, PAPER, (PANEL_X, 136, 458, 588), 3)
            text(self.screen, self.heading, "Inside device", PANEL_X + 23, 170)
            text(self.screen, self.small, self.device_stack[-1][2][:32], PANEL_X + 23, 215, TEAL)
            self.draw_lines([f"Layer {len(self.device_stack)} / inspection",
                             "This is a simulation copy of the interior.",
                             "Right-click a device to look deeper.",
                             "Load its design from Library to edit it.",
                             "Save a new version to reuse those edits.",
                             f"A: {self.port_names['A']}", f"B: {self.port_names['B']}",
                             f"Output: {self.port_names['OUT']}"], PANEL_X + 23, 265, self.small, 31)
            self.button((PANEL_X + 23, 620, 412, 44), "Back to parent  [Esc]", self.leave_device, small=True)
            return
        self.draw_background()
        if adventure.active_editor(self):
            self.button((980, 60, 228, 40), "BACK TO FIELD [ESC]", lambda: adventure.close_editor(self), small=True)
        elif self.factory_context is not None:
            self.button((980, 60, 228, 40), "BACK TO FLOOR [ESC]", self.open_factory, small=True)
        else:
            self.button((700, 60, 158, 40), "FACTORY FLOOR", self.open_factory, small=True)
            self.button((868, 60, 145, 40), "CONTRACTS [J]", self.open_contract_board, small=True)
            self.button((1023, 60, 145, 40), "LEDGER [G]", self.open_ledger, small=True)
        self.draw_board()
        self.draw_status()
        if self.tab != "BUILD":
            self.draw_panel_shell()
        if self.tab == "BUILD":
            self.draw_build_panel()
        elif self.tab == "VILLAGE":
            self.draw_village_panel()
        else:
            self.draw_library_panel()
        # A narrow notification strip stays visible across the three side tabs.
        rounded(self.screen, (52, 61, 58), (58, 730, 1164, 22), 5)
        from daily_life import progress
        status = self.message if self.message_timer > 0 else f"Day {self.village.day}: {round(progress(self.village) * 100)}% / N finish day | {self.village.market_note}"
        if (self.factory_context is not None or adventure.active_editor(self)) and self.message_timer <= 0:
            status = "Draft simulation / village time paused"
        hovered_part = self.circuit.parts.get(self.board_pos(self.mouse_pos()))
        if hovered_part and hovered_part.kind == "DEVICE":
            device = hovered_part.device
            ports = device.get("ports", {"A": "Input A", "B": "Input B", "OUT": "Output"})
            directions = ("north", "east", "south", "west")
            inputs, outputs = hovered_part.ports()
            status = (f"{device['name']} v{device.get('version', 1)} | "
                      f"{ports['A']} ({directions[inputs[0]]}), {ports['B']} ({directions[inputs[1]]}) -> "
                      f"{ports['OUT']} ({directions[outputs[0]]}) | Right-click: inspect")
        elif self.board_pos(self.mouse_pos()) in self.circuit.terminals:
            key = self.circuit.terminals[self.board_pos(self.mouse_pos())]["name"]
            status = f"Port {key}: {self.port_names.get(key, key)} / click body to change input; output socket starts a trace"
        socket_hit = workshop_floor.hit_socket(self, self.mouse_pos())
        if socket_hit:
            pos, output, pin = socket_hit
            label = workshop_floor.socket_label(self.circuit.parts[pos], output, pin)
            status = (f"{label} / output - click to draw a wire" if output else
                      f"{label} / input - click to connect" if self.trace_source is not None else
                      f"{label} / input - wire from an output; right-click disconnects")
        text(self.screen, self.tiny, status[:145], 69, 733, (245, 223, 172))
        if self.success_job is not None:
            self.draw_success_modal()
        elif self.test_results is not None:
            self.draw_test_modal()
        elif self.delivery_open:
            self.draw_delivery_modal()
        elif self.help_open:
            self.draw_help_modal()
        if self.invention and self.invention.show_results:
            workbench.invention_results(self)
        if self.timing_results is not None:
            timing_workshop.draw_results(self)
        if self.invention_picker:
            workbench.invention_picker(self)
        if self.task_help_open:
            self.draw_task_help_modal()
        if self.port_editor is not None:
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((20, 29, 29, 180)); self.screen.blit(shade, (0, 0))
            rounded(self.screen, PAPER, (330, 145, 620, 520), 10)
            text(self.screen, self.heading, "Port names", 380, 166, TEAL)
            text(self.screen, self.small, "Click a field; type a name. Tab moves to the next.", 380, 198)
            for i, label in enumerate(self.port_editor["keys"]):
                y = 222 + i * 42
                rounded(self.screen, CREAM, (380, y, 520, 36), 5)
                rounded(self.screen, TEAL if self.port_editor['field'] == i else STONE, (380, y, 520, 36), 5, 2)
                text(self.screen, self.tiny, label, 392, y + 10, MUTED)
                text(self.screen, self.small, self.port_editor['values'][i], 520, y + 9, width=365)
            self.button((700, 608, 200, 40), "Save names  [Enter]", self.finish_ports, small=True)
        if self.pending_design_delete is not None:
            self.draw_design_delete_confirmation()

    def result_rows(self):
        if self.timing_results is not None:
            return self.timing_results
        if self.scene == "workshop":
            if self.invention and self.invention.show_results:
                return self.invention.rows
            return self.test_results or []
        if self.scene == "compute":
            return self.compute_results
        return []

    def scroll_tests(self, delta):
        self.test_scroll = max(0, min(max(0, len(self.result_rows()) - 8), self.test_scroll + delta))

    def handle_event(self, event):
        """Use the same input dispatch in the live loop and regression checks."""
        if self.opening_screen is not None:
            if event.type == pygame.KEYDOWN and event.key != pygame.K_F11:
                self.opening_screen.begin()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 2, 3):
                    self.opening_screen.begin()
                return
        if event.type == pygame.QUIT:
            self.exit_game()
        elif event.type == pygame.VIDEORESIZE:
            self.viewport.resize(event.size)
        elif event.type == pygame.WINDOWFOCUSLOST:
            if self.scene != "menu":
                self.pause_menu_open = True
        elif self.pause_menu_open and event.type in (pygame.MOUSEWHEEL, pygame.MOUSEMOTION):
            return
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif chapter_ui.active(self) and event.type == pygame.MOUSEWHEEL:
            if not self.pause_menu_open and not self.settings_open and self.chapter_view['mode'] == 'journal':
                chapter_ui.choose(self, self.chapter_view['index'] - event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse = self.viewport.pointer(event.pos)
            if mouse == (-1000, -1000):
                return
            self.focus_index = -1
            if event.button in (4, 5):
                if chapter_ui.active(self):
                    if not self.pause_menu_open and not self.settings_open and self.chapter_view['mode'] == 'journal':
                        chapter_ui.choose(self, self.chapter_view['index'] + (-1 if event.button == 4 else 1))
                elif not self.task_help_open and not self.pause_menu_open and not self.settings_open:
                    self.scroll_tests(-1 if event.button == 4 else 1)
            else:
                self.handle_click(mouse, event.button)
        elif event.type == pygame.MOUSEMOTION:
            self.focus_index = -1
        elif event.type == pygame.MOUSEWHEEL and not self.task_help_open and not self.settings_open:
            self.scroll_tests(-event.y)

    def run(self):
        self.opening_screen = OpeningScreen(DATA_DIR / "assets" / "loading", self.reduced_motion)
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
