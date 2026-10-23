"""Numbermill: a small playable village and logic workshop."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pygame

from circuit import Circuit, Part, PLACEABLE, ARITHMETIC, ALL_PARTS, CONDUCTORS, VECTORS, WIDTH, HEIGHT, validate_device
from commissions import COMMISSIONS
from economy import Village, CONTRACTS, LICENSE_RATE
from town import Town, WORLD_W as TOWN_W, WORLD_H as TOWN_H, LOCATIONS
import ledger
import computation
import workbench
import inventions


SCREEN_W, SCREEN_H = 1280, 760
FPS = 60
CELL = 54
BOARD_X, BOARD_Y = 48, 154
PANEL_X = 770
DATA_DIR = Path(__file__).resolve().parent
SAVE_FILE = DATA_DIR / "save.json"
DESIGNS_FILE = DATA_DIR / "designs.json"
SAVES_DIR = DATA_DIR / "saves"
SLOT_COUNT = 5

INK = (40, 43, 46)
MUTED = (95, 98, 94)
CREAM = (246, 231, 195)
PAPER = (251, 242, 216)
STONE = (157, 153, 136)
STONE_DARK = (109, 107, 99)
COPPER = (180, 101, 65)
COPPER_LIGHT = (227, 158, 100)
TEAL = (61, 125, 118)
TEAL_LIGHT = (123, 199, 175)
GOLD = (238, 184, 79)
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
    temporary.replace(path)


def village_from_data(data) -> Village:
    if not isinstance(data, dict):
        return Village()
    allowed = Village.__dataclass_fields__
    try:
        return Village(**{key: value for key, value in data.items() if key in allowed})
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


def text(surface, font, content, x, y, color=INK):
    surface.blit(font.render(str(content), True, color), (x, y))


def rounded(surface, color, rect, radius=12, border=0):
    pygame.draw.rect(surface, color, rect, border, border_radius=radius)


class PixelFont:
    """Keep body text readable and scale headings to crisp game pixels."""

    def __init__(self, size: int, bold: bool = False):
        self.scale = 2 if size >= 24 else 1
        self.base = pygame.font.SysFont("consolas", size // self.scale, bold=bold)

    def render(self, content, antialias, color):
        image = self.base.render(str(content), False, color)
        if self.scale == 1:
            return image
        return pygame.transform.scale(image, (image.get_width() * 2, image.get_height() * 2))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Numbermill — Copperside Village")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = PixelFont(18)
        self.small = PixelFont(16)
        self.tiny = PixelFont(14)
        self.big = PixelFont(30, bold=True)
        self.heading = PixelFont(24, bold=True)
        self.circuit = Circuit()
        self.village = Village()
        self.town = Town()
        self.scene = "menu"
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
        self.designs = []
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
        self.selected = "PIPE"
        self.rotation = 0
        self.tab = "BUILD"
        self.running = True
        self.paused = False
        self.tick_interval = 0.22
        self.elapsed = 0.0
        self.message = "Every workshop invention changes a business."
        self.message_timer = 0.0
        self.test_results = None
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

    def start_slot(self, slot: int):
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
        self.selected = "PIPE"
        self.rotation = 0
        self.port_editor = None
        self.active_compute = None
        self.compute_results = []
        self.numeric_mode = False
        self.invention = None
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
        for design in self.designs:
            if isinstance(design, dict):
                design.setdefault("owner", "You")
                design.setdefault("rights_note", "Private design")
        if data and data.get("version", 1) < 5 and "arithmetic_unlocks" not in data.get("village", {}):
            rows = loaded_circuit.snapshot()
            for entry in self.designs:
                if isinstance(entry, dict):
                    rows.extend(entry.get("parts", []))
            for entry in self.village.compute_designs.values():
                rows.extend(entry.get("parts", []))
            self.village.arithmetic_unlocks = sorted(inventions.required_blocks(rows))
        self.circuit = loaded_circuit
        self.town = Town()
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
        self.town.update_people(self.village, 0)
        self.scene = "town"
        self.town_dialogue = None
        self.town_topic = "work"
        self.library_page = 0
        self.contract_page = 0
        self.ledger_tab = "Overview"
        self.ledger_index = 0
        self.trade_day_offset = 0
        self.selected = "PIPE"
        self.rotation = 0
        self.tab = "BUILD"
        self.paused = False
        self.elapsed = 0.0
        self.test_results = None
        self.tested_job = None
        self.tested_snapshot = None
        self.success_job = None
        self.help_open = False
        self.delivery_open = False
        self.delivery_error = ""
        self.toast(f"{'Loaded' if data else 'Created'} slot {slot}. J opens contracts; L opens the Town Ledger.")
        if not data:
            self.save_game()

    def save_game(self):
        if self.current_slot is None:
            return
        save_json(slot_path(self.current_slot), {
            "version": 5,
            "village": vars(self.village),
            "designs": self.designs,
            "circuit": (self.device_stack[0][0] if self.device_stack else self.circuit).snapshot(),
            "port_names": self.device_stack[0][1] if self.device_stack else self.port_names,
            "active_compute": self.active_compute,
            "numeric_mode": self.numeric_mode,
            "town": [self.town.player_x, self.town.player_y],
        })

    def return_to_menu(self):
        self.save_game()
        self.scene = "menu"
        self.pending_delete = None
        self.town_dialogue = None
        self.test_results = None
        self.success_job = None
        self.current_slot = None
        self.toast("Progress saved. Choose a save slot to continue.")

    def request_delete_slot(self, slot: int):
        if self.scene == "menu" and load_slot(slot) is not None:
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
        self.board_return_scene = self.scene
        self.contract_page = 0
        self.scene = "contracts"

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
        self.compute_return_scene = self.scene if self.scene != "compute" else self.compute_return_scene
        self.scene = "compute"

    def close_compute(self):
        self.scene = self.compute_return_scene

    def select_compute(self, key):
        self.compute_key = key
        self.compute_results = []

    def build_compute(self):
        operation = computation.JOBS[self.compute_key].operation
        if operation not in self.village.arithmetic_unlocks:
            self.open_invention(inventions.FOR_BLOCK[operation])
            return
        self.active_compute = self.compute_key
        job = computation.JOBS[self.compute_key]
        self.port_names = dict(zip(("A", "B", "OUT"), (*job.inputs, job.output)))
        self.numeric_mode = True
        self.scene = "workshop"
        self.tab = "BUILD"
        self.compute_results = []
        self.tested_snapshot = None
        self.design_source = None
        self.toast(job.description)

    def test_compute(self):
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
        if self.scene != "invention":
            self.invention_return_scene = self.scene
        self.scene = "invention"
        self.switch_invention(key)

    def switch_invention(self, key):
        challenge = inventions.CHALLENGES[key]
        prerequisite_missing = challenge.prerequisite and challenge.prerequisite not in self.village.arithmetic_unlocks
        if prerequisite_missing:
            key = inventions.FOR_BLOCK[challenge.prerequisite]
        self.invention = inventions.Bench(self.village, key)
        if prerequisite_missing:
            self.invention.message = f"Invent {challenge.prerequisite} first; then return to earn {', '.join(challenge.unlocks)}."

    def close_invention(self):
        self.save_game()
        self.scene = self.invention_return_scene

    def test_invention(self):
        self.invention.run_tests()
        self.save_game()

    def select_part(self, kind):
        if kind in ARITHMETIC and kind not in self.village.arithmetic_unlocks:
            self.open_invention(inventions.FOR_BLOCK[kind])
            return
        self.selected = kind

    def choose_contract(self, key):
        job = COMMISSIONS[key]
        if self.village.offers.get(key, {}).get("status") not in ("open", "bid", "player", "rival"):
            return
        self.village.active_commission = key
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
        completed = self.contract_complete(self.commission.key)
        return (
            not completed
            and self.village.offers.get(self.commission.key, {}).get("status") in ("open", "bid")
            and self.tested_job == self.commission.key
            and self.tested_snapshot == self.circuit.snapshot()
        )

    def interact_town(self):
        if self.town_dialogue is None:
            nearby = self.town.nearby()
            if nearby == "workshop":
                self.scene = "workshop"
                self.tab = "BUILD"
                self.toast(f"Workshop: {self.commission.title}.")
                return
            self.town_dialogue = nearby
            self.town_topic = "work"
            if nearby == "market":
                self.toast("One loaf kept for walk-in shoppers. E buys bread.")
            if nearby is None:
                self.toast("Walk closer to a door or villager.")
            return
        location = self.town_dialogue
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
            self.village.active_commission = location
            self.save_game()
        self.scene = "workshop"
        self.tab = "BUILD"
        self.town_dialogue = None
        self.toast(f"Workshop: {self.commission.title}.")

    def toast(self, message: str):
        self.message = message
        self.message_timer = 6.0

    def button(self, rect, label, action, *, active=False, small=False, enabled=True, danger=False, icon=False):
        rect = pygame.Rect(rect)
        hover = enabled and rect.collidepoint(pygame.mouse.get_pos())
        if not enabled:
            color = (151, 147, 132)
        elif danger:
            color = (188, 84, 73) if hover else RED
        else:
            color = TEAL if active else (COPPER if hover else (215, 195, 156))
        rounded(self.screen, (74, 53, 42), rect.move(2, 3), 3)
        rounded(self.screen, color, rect, 3)
        rounded(self.screen, (80, 61, 48), rect, 3, 2)
        if not icon:
            for x in (rect.left + 8, rect.right - 8):
                pygame.draw.circle(self.screen, (118, 89, 60), (x, rect.centery), 2)
        font = self.small if small else self.font
        rendered = font.render(label, True, PAPER if active or hover or danger else INK)
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
        return (BOARD_X, BOARD_Y, CELL) if self.tab == "BUILD" and not self.device_stack else (76, 154, 41)

    def handle_click(self, mouse, button):
        if self.scene == "invention":
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        return
            self.invention.click(mouse, button)
            return
        if self.scene == "workshop" and self.port_editor is not None:
            if button == 1:
                for i in range(3):
                    if pygame.Rect(380, 260 + i * 70, 520, 48).collidepoint(mouse):
                        self.port_editor["field"] = i
                if pygame.Rect(700, 505, 200, 40).collidepoint(mouse):
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
            return
        if self.scene in ("town", "contracts", "ledger", "compute"):
            if button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(mouse):
                        action()
                        return
                if self.scene == "town" and not (self.town_dialogue and pygame.Rect(275, 500, 730, 219).collidepoint(mouse)):
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
            if button == 1 and pygame.Rect(357, 554, 175, 39).collidepoint(mouse):
                self.test_results = None
            elif button == 1 and pygame.Rect(655, 554, 268, 39).collidepoint(mouse) and self.submission_ready:
                self.test_results = None
                self.open_delivery_choices()
            return
        if button == 1:
            for rect, action in reversed(self.buttons):
                if rect.collidepoint(mouse):
                    action()
                    return
        pos = self.board_pos(mouse)
        if pos is None:
            return
        part = self.circuit.parts.get(pos)
        if part and part.kind in ("A", "B") and self.numeric_mode and button in (1, 3):
            increment = (16 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1) * (1 if button == 1 else -1)
            self.circuit.switches[part.kind] = (int(self.circuit.switches[part.kind]) + increment) % 256
            return
        if part and part.kind in ("A", "B") and button == 1:
            self.circuit.switches[part.kind] = not self.circuit.switches[part.kind]
            return
        if button == 3:
            if part and part.kind == "DEVICE":
                self.inspect_device(pos)
            elif part and part.kind in ALL_PARTS:
                self.circuit.set_part(pos, Part(part.kind, (part.rotation + 1) % 4))
            return
        if button == 1:
            if self.selected in ARITHMETIC and self.selected not in self.village.arithmetic_unlocks:
                self.select_part(self.selected)
                return
            if self.selected == "DEVICE" and self.held_device and inventions.locked_blocks(self.village, self.held_device["parts"]):
                self.toast("Invent the arithmetic inside this device before placing it.")
                return
            self.circuit.set_part(pos, None if self.selected == "ERASE" else
                                  Part(self.selected, self.rotation, self.held_device if self.selected == "DEVICE" else None))

    def select_device(self, index):
        item = self.designs[index]
        locked = inventions.locked_blocks(self.village, item["parts"])
        if locked:
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
        self.port_editor = {"field": 0, "values": [self.port_names[k] for k in ("A", "B", "OUT")]}

    def finish_ports(self):
        self.port_names = {k: (value.strip() or default) for k, value, default in
                           zip(("A", "B", "OUT"), self.port_editor["values"], ("Input A", "Input B", "Output"))}
        self.port_editor = None
        self.save_game()

    def save_copy(self, name=None, announce=True, job_key=None, delivery_mode=None):
        number = max((int(d.get("number", 0)) for d in self.designs if isinstance(d, dict)), default=0) + 1
        source = self.design_source if name is None and job_key is None else None
        device_id = source.get("device_id", source["number"]) if source else number
        version = max((d.get("version", 1) for d in self.designs if d.get("device_id", d.get("number")) == device_id), default=0) + 1
        label = name or (source["name"] if source else f"Design {number:02d}")
        rights = "Private design"
        if job_key is not None:
            customer = COMMISSIONS[job_key].customer
            rights = {"install": f"Installed at {customer}; rights retained",
                      "sell": f"{customer} owns one copy",
                      "license": f"Licensed to {customer} at {LICENSE_RATE}/day"}[delivery_mode]
        self.designs.append({"number": number, "name": label, "parts": self.circuit.snapshot(),
                             "owner": "You", "job": job_key, "rights_note": rights,
                             "device_id": device_id, "version": version, "ports": self.port_names.copy()})
        self.design_source = self.designs[-1]
        self.library_page = 0
        self.save_game()
        if announce:
            self.toast(f"Saved {label}. Open Library to load a copy.")
        return label

    def load_design(self, index):
        try:
            entry = self.designs[index]
            locked = inventions.locked_blocks(self.village, entry["parts"])
            if locked:
                self.toast(f"Invent {', '.join(sorted(locked))} before loading this design.")
                return
            self.circuit = Circuit.from_snapshot(entry["parts"])
            self.port_names = entry.get("ports", {"A": "Input A", "B": "Input B", "OUT": "Output"}).copy()
            self.design_source = entry
            self.tested_job = None
            self.tested_snapshot = None
            self.toast(f"Loaded a copy of {entry['name']}.")
            self.tab = "BUILD"
        except (IndexError, KeyError, TypeError, ValueError):
            self.toast("That design could not be loaded.")

    def test_commission(self):
        locked = inventions.locked_blocks(self.village, self.circuit.snapshot())
        if locked:
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
        if self.active_compute:
            self.open_compute()
            return
        if not self.submission_ready:
            self.toast("Pass all four checks before choosing delivery terms.")
            return
        self.test_results = None
        self.delivery_open = True
        self.delivery_error = ""

    def submit_design(self, mode="install"):
        if not self.submission_ready:
            self.toast("Run the four input checks before delivering this design.")
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
        if not getattr(self.village, f"complete_{job.key}_job")(mode):
            self.delivery_error = "Customer cannot afford that option. Choose another."
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
        self.village.advance_day()
        self.save_game()
        self.toast(self.village.last_contract_event or
                   f"Day {self.village.day}: village trades and production updated.")

    def handle_key(self, event):
        key = event.key
        if self.scene == "invention":
            if key == pygame.K_ESCAPE:
                self.close_invention()
            elif key == pygame.K_t:
                self.test_invention()
            elif key == pygame.K_PERIOD:
                self.invention.tick()
            elif key == pygame.K_q:
                self.return_to_menu()
            return
        if self.scene == "compute":
            if key == pygame.K_ESCAPE:
                self.close_compute()
            elif key == pygame.K_t:
                self.test_compute()
            elif key == pygame.K_n:
                self.next_day()
            elif key == pygame.K_q:
                self.return_to_menu()
            return
        if self.scene == "workshop" and self.port_editor is not None:
            if key == pygame.K_ESCAPE:
                self.port_editor = None
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.finish_ports()
            elif key == pygame.K_TAB:
                self.port_editor["field"] = (self.port_editor["field"] + 1) % 3
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
            if self.pending_delete is not None:
                if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.confirm_delete_slot()
                elif key in (pygame.K_ESCAPE, pygame.K_q):
                    self.pending_delete = None
                return
            if pygame.K_1 <= key <= pygame.K_5:
                self.start_slot(key - pygame.K_1 + 1)
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            return
        if key == pygame.K_q:
            self.return_to_menu()
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
            elif key in (pygame.K_DOWN, pygame.K_UP) and self.ledger_tab in ("Businesses", "People"):
                count = len(self.village.businesses) if self.ledger_tab == "Businesses" else len(self.village.citizens)
                self.ledger_index = (self.ledger_index + (1 if key == pygame.K_DOWN else -1)) % count
            elif key in (pygame.K_DOWN, pygame.K_UP) and self.ledger_tab == "Trade":
                self.shift_trade_day(1 if key == pygame.K_UP else -1)
            elif key == pygame.K_j:
                self.open_contract_board()
            elif key == pygame.K_c:
                self.open_compute()
            return
        if self.scene == "contracts":
            if key in (pygame.K_ESCAPE, pygame.K_j):
                self.scene = self.board_return_scene
            elif pygame.K_1 <= key < pygame.K_1 + len(COMMISSIONS):
                self.choose_contract(tuple(COMMISSIONS)[key - pygame.K_1])
            elif key == pygame.K_RIGHT:
                self.contract_page = min((len(COMMISSIONS) - 1) // 3, self.contract_page + 1)
            elif key == pygame.K_LEFT:
                self.contract_page = max(0, self.contract_page - 1)
            return
        if self.scene == "town":
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
            elif self.town_dialogue and self.town_dialogue.startswith("person:") and key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.town_topic = {pygame.K_1: "work", pygame.K_2: "family", pygame.K_3: "town"}[key]
                self.village.talk_to(self.town_dialogue[7:], self.town_topic)
                self.save_game()
            elif key == pygame.K_e:
                self.interact_town()
            elif key == pygame.K_n and self.town_dialogue == "market":
                self.next_day()
            elif key == pygame.K_ESCAPE:
                if self.town_dialogue is not None:
                    self.town_dialogue = None
                else:
                    self.return_to_menu()
            return
        if self.success_job is not None:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.success_job = None
                self.scene = "town"
            elif key == pygame.K_ESCAPE:
                self.success_job = None
            return
        if self.test_results is not None:
            if key == pygame.K_ESCAPE:
                self.test_results = None
            elif key == pygame.K_t:
                self.test_commission()
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.submission_ready:
                self.open_delivery_choices()
            return
        if key == pygame.K_i:
            self.open_invention()
        elif key == pygame.K_c:
            self.open_compute()
        elif key == pygame.K_ESCAPE:
            self.scene = "town"
            self.toast("Back in Copperside Village.")
        elif pygame.K_1 <= key <= pygame.K_6:
            self.selected = PLACEABLE[key - pygame.K_1]
            self.tab = "BUILD"
        elif key in (pygame.K_7, pygame.K_DELETE):
            self.selected = "ERASE"
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
        if self.scene == "menu":
            pass
        elif self.scene == "town":
            self.town.update_people(self.village, dt)
            if self.town_dialogue is None:
                self.town.move(pygame.key.get_pressed(), dt)
        elif self.scene == "workshop" and not self.paused and not self.help_open:
            self.elapsed += dt
            while self.elapsed >= self.tick_interval:
                self.circuit.tick()
                self.elapsed -= self.tick_interval
        if self.message_timer > 0:
            self.message_timer -= dt

    def draw_background(self):
        self.screen.fill((71, 91, 87))
        # Cobblestones and workshop walls create a little world around the floor grid.
        for y in range(0, SCREEN_H, 34):
            for x in range(0, SCREEN_W, 68):
                shift = 34 if (y // 34) % 2 else 0
                pygame.draw.rect(self.screen, (78, 99, 94), (x + shift, y, 64, 30), border_radius=4)
        rounded(self.screen, (49, 63, 62), (28, 20, 1224, 720), 5)
        rounded(self.screen, (124, 75, 58), (35, 27, 1210, 705), 5, 7)
        rounded(self.screen, (84, 59, 48), (48, 38, 1184, 87), 4)
        rounded(self.screen, (112, 80, 58), (55, 45, 1170, 73), 3, 3)
        for x in (70, 1210):
            for y in (56, 105):
                pygame.draw.circle(self.screen, GOLD, (x, y), 4)
                pygame.draw.circle(self.screen, (95, 64, 47), (x, y), 2)
        text(self.screen, self.heading, "WORKSHOP", 87, 66, PAPER)
        job_label = (f"COMPUTE / {computation.JOBS[self.active_compute].owner.upper()}" if self.active_compute else
                     f"JOB {self.commission.level} / {len(COMMISSIONS)}  /  {self.commission.customer.upper()}")
        text(self.screen, self.small, job_label, 391, 72, CREAM)
        text(self.screen, self.small, f"DAY {self.village.day}   {self.village.coins} COINS", 972, 72, CREAM)

    def draw_avatar(self, cx, cy):
        pygame.draw.ellipse(self.screen, (129, 105, 70), (cx - 24, cy + 22, 48, 11))
        pygame.draw.rect(self.screen, TEAL, (cx - 14, cy + 4, 28, 25))
        pygame.draw.rect(self.screen, (74, 52, 48), (cx - 13, cy - 16, 26, 25))
        pygame.draw.rect(self.screen, (232, 180, 130), (cx - 10, cy - 11, 20, 17))
        pygame.draw.rect(self.screen, (60, 45, 42), (cx - 7, cy - 3, 3, 3))
        pygame.draw.rect(self.screen, (60, 45, 42), (cx + 5, cy - 3, 3, 3))
        pygame.draw.rect(self.screen, COPPER, (cx - 18, cy - 20, 36, 8))

    def draw_board(self):
        bx, by, cell = self.board_metrics()
        rounded(self.screen, (89, 66, 52), (bx - 14, by - 14, WIDTH * cell + 26, HEIGHT * cell + 26), 6)
        rounded(self.screen, (198, 164, 113), (bx - 7, by - 7, WIDTH * cell + 12, HEIGHT * cell + 12), 4)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                rect = pygame.Rect(bx + x * cell, by + y * cell, cell - 2, cell - 2)
                shade = (188, 183, 158) if (x + y) % 2 else (196, 190, 165)
                pygame.draw.rect(self.screen, shade, rect, border_radius=3)
                pygame.draw.rect(self.screen, (170, 164, 143), rect, 1, border_radius=3)
        for pos, part in self.circuit.parts.items():
            self.draw_part(pos, part)
        hovered = self.board_pos(pygame.mouse.get_pos())
        if hovered:
            x, y = hovered
            pygame.draw.rect(self.screen, GOLD, (bx + x * cell, by + y * cell, cell - 2, cell - 2), 2, border_radius=5)

    def draw_part(self, pos, part):
        bx, by, cell = self.board_metrics()
        cx, cy = bx + pos[0] * cell + cell // 2 - 1, by + pos[1] * cell + cell // 2 - 1
        signal = self.circuit.active.get(pos, 0)
        r = int(cell * .36)
        rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        base = TEAL if signal else COPPER
        if part.kind in ('A', 'B', 'LAMP'):
            base = (78, 119, 127) if signal else (103, 112, 113)
        rounded(self.screen, (86, 66, 54), rect.move(2, 3), 5)
        rounded(self.screen, base, rect, 5)
        rounded(self.screen, COPPER_LIGHT, rect, 5, 2)
        inputs, outputs = part.ports()
        for direction in set(inputs + outputs):
            dx, dy = VECTORS[direction]
            start = (cx + dx * int(cell * .30), cy + dy * int(cell * .30))
            end = (cx + dx * int(cell * .47), cy + dy * int(cell * .47))
            pygame.draw.line(self.screen, TEAL_LIGHT if signal else (87, 79, 70), start, end, 5)
        if part.kind in CONDUCTORS:
            for direction in inputs:
                dx, dy = VECTORS[direction]
                pygame.draw.line(self.screen, PAPER if signal else GOLD, (cx, cy),
                                 (cx + dx * r, cy + dy * r), 3)
        else:
            symbol = workbench.SYMBOLS.get(part.kind, '*' if part.kind == 'LAMP' else part.kind)
            show_value = self.numeric_mode or signal > 1 or part.kind in ARITHMETIC
            rendered = self.small.render(symbol, True, PAPER)
            self.screen.blit(rendered, rendered.get_rect(center=(cx, cy - 7 if show_value else cy)))
            if show_value:
                value = self.circuit.switches[part.kind] if part.kind in ('A', 'B') else signal
                rendered = self.tiny.render(str(int(value)), True, PAPER)
                self.screen.blit(rendered, rendered.get_rect(center=(cx, cy + 9)))

    def draw_status(self):
        width = 866 if self.tab == "BUILD" and not self.device_stack else 688
        rounded(self.screen, CREAM, (42, 662, width, 62), 4)
        rounded(self.screen, (95, 67, 50), (42, 662, width, 62), 4, 3)
        icon = "●" if not self.paused else "Ⅱ"
        text(self.screen, self.font, f"{icon}  tick {self.circuit.tick_count:03d}", 76, 675)
        text(self.screen, self.small, f"{1 / self.tick_interval:.1f} steps/s", 260, 679, MUTED)
        self.button((420, 674, 92, 36), "Pause" if not self.paused else "Run", lambda: setattr(self, "paused", not self.paused), small=True)
        self.button((520, 674, 82, 36), "Step", self.circuit.tick, small=True)
        self.button((610, 674, 110, 36), "Reset", self.circuit.reset, small=True)
        if width > 688:
            text(self.screen, self.small, f"OUT {self.circuit.output_value()}", 746, 684, TEAL)

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
            "1-6 choose a part; 7 or Delete selects the eraser.",
            "Left click places a part or toggles input A or B.",
            "Right click rotates normal parts or inspects devices. R rotates held parts.",
            "B sends steam upward. Rotate a straight pipe once to connect it.",
            "NAND = AND then NOT. NOR = OR then NOT.",
            "Library: save devices. C: calculation jobs. Number inputs: click +1 / right -1.",
        ), 225, 244, self.small, 27)
        text(self.screen, self.small, "TEST & NAVIGATE", 225, 400, COPPER)
        self.draw_lines((
            "T checks four input cases; Enter opens delivery choices after a pass.",
            "Space pauses; . steps; + and - change speed.",
            "S saves a version; B/V/L change tabs; J opens contracts.",
            "Esc returns to town; Q saves and opens the menu.",
        ), 225, 432, self.small, 31)
        self.button((874, 596, 190, 43), "CLOSE  [H/ESC]", lambda: setattr(self, "help_open", False), active=True, small=True)

    def draw_lines(self, lines, x, y, font=None, spacing=22, color=INK):
        font = font or self.small
        for i, line in enumerate(lines):
            text(self.screen, font, line, x, y + spacing * i, color)

    def draw_village_panel(self):
        text(self.screen, self.heading, f"Village  /  day {self.village.day}", PANEL_X + 23, 210)
        text(self.screen, self.font, f"Your purse   {self.village.coins} coins", PANEL_X + 23, 255, COPPER)
        text(self.screen, self.small, "GOODS & PRICES", PANEL_X + 23, 302, MUTED)
        self.draw_lines([
            f"Grain {self.village.grain}    Flour {self.village.flour}    Bread {self.village.bread}",
            f"Bread price  {self.village.bread_price} coins / loaf",
            self.village.market_note,
        ], PANEL_X + 23, 332, self.tiny, 26, TEAL)
        text(self.screen, self.small, "BUSINESSES  /  DAILY CAPACITY & CASH", PANEL_X + 23, 425, MUTED)
        for row, (business_id, firm) in enumerate(self.village.businesses.items()):
            if row >= 4:
                break
            name = firm["name"].replace("Copperside ", "")[:13]
            line = f"{name:<13} {self.village.capacity(business_id)}/day   {firm['cash']} coins"
            text(self.screen, self.tiny, line, PANEL_X + 23, 447 + row * 23)
        self.button((PANEL_X + 23, 541, 412, 39), "Advance one day", self.next_day, active=True, small=True)
        text(self.screen, self.small, "TOWN LEDGER", PANEL_X + 23, 593, MUTED)
        self.draw_lines([line if len(line) <= 52 else line[:49] + "..." for line in self.village.journal[:4]], PANEL_X + 23, 620, self.tiny, 22)

    def draw_library_panel(self):
        text(self.screen, self.heading, "Design library", PANEL_X + 23, 210)
        self.draw_lines([
            "Load to edit; Place to reuse as one device.",
            "Saved versions keep existing machines intact.",
        ], PANEL_X + 23, 250)
        self.button((PANEL_X + 23, 318, 265, 44), "Save new version  [S]", self.save_copy, active=True, small=True)
        self.button((PANEL_X + 300, 318, 135, 44), "Name ports", self.edit_ports, small=True)
        text(self.screen, self.tiny, f"A: {self.port_names['A'][:12]}  B: {self.port_names['B'][:12]}  > {self.port_names['OUT'][:12]}", PANEL_X + 23, 373, TEAL)
        text(self.screen, self.small, f"{len(self.designs)} SAVED DESIGNS", PANEL_X + 23, 390, MUTED)
        if not self.designs:
            self.draw_lines(["Your design shelf is empty.", "Build something, then press S."], PANEL_X + 23, 431)
        else:
            ordered = list(range(len(self.designs) - 1, -1, -1))
            pages = (len(ordered) + 3) // 4
            self.library_page = min(self.library_page, pages - 1)
            visible = ordered[self.library_page * 4:(self.library_page + 1) * 4]
            for display_row, index in enumerate(visible):
                item = self.designs[index]
                if not isinstance(item, dict):
                    continue
                y = 421 + display_row * 66
                text(self.screen, self.small, f"{item.get('name', 'Design')[:24]}  v{item.get('version', 1)}", PANEL_X + 23, y)
                self.button((PANEL_X + 23, y + 24, 190, 30), "Load / edit", lambda j=index: self.load_design(j), small=True)
                self.button((PANEL_X + 225, y + 24, 210, 30), "Place device", lambda j=index: self.select_device(j), small=True)
            if pages > 1:
                self.button((PANEL_X + 23, 686, 95, 30), "Previous", lambda: setattr(self, "library_page", max(0, self.library_page - 1)), small=True)
                text(self.screen, self.tiny, f"Page {self.library_page + 1}/{pages}", PANEL_X + 192, 694, MUTED)
                self.button((PANEL_X + 340, 686, 95, 30), "Next", lambda: setattr(self, "library_page", min(pages - 1, self.library_page + 1)), small=True)

    def draw_test_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 165))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (112, 73, 55), (293, 173, 694, 441), 4)
        rounded(self.screen, PAPER, (301, 181, 678, 425), 3)
        passed = all(case.passed for case in self.test_results)
        count = sum(case.passed for case in self.test_results)
        text(self.screen, self.heading, f"{count} / {len(self.test_results)} CHECKS PASSED", 325, 202, TEAL if passed else RED)
        text(self.screen, self.tiny, self.commission.title, 766, 210, MUTED)
        text(self.screen, self.small, self.test_message, 325, 243, TEAL if passed else RED)
        rounded(self.screen, (223, 209, 176), (325, 276, 630, 44), 3)
        text(self.screen, self.small, "A", 349, 287)
        text(self.screen, self.small, "B", 438, 287)
        if len(self.test_results) > 4:
            text(self.screen, self.small, "C", 488, 287)
        text(self.screen, self.small, "Needed", 533, 287)
        text(self.screen, self.small, "Your lamp", 666, 287)
        text(self.screen, self.small, "Result", 836, 287)
        for i, case in enumerate(self.test_results):
            y = 329 + i * (34 if len(self.test_results) > 4 else 43)
            rounded(self.screen, (224, 239, 220) if case.passed else (248, 217, 201), (325, y, 630, 31 if len(self.test_results) > 4 else 38), 3)
            text(self.screen, self.font, int(case.inputs[0]), 351, y + 7)
            text(self.screen, self.font, int(case.inputs[1]), 440, y + 7)
            if len(case.inputs) > 2:
                text(self.screen, self.font, int(case.inputs[2]), 490, y + 7)
            text(self.screen, self.font, int(case.expected), 549, y + 7)
            text(self.screen, self.font, int(case.actual), 697, y + 7)
            text(self.screen, self.small, "PASS" if case.passed else "FAIL", 837, y + 9, TEAL if case.passed else RED)
        if not passed:
            kinds = {part.kind for part in self.circuit.parts.values()}
            if self.commission.logic == "AND" and "OR" in kinds and "AND" not in kinds:
                hint = "An OR valve runs for either input. This job needs AND."
            elif self.commission.logic == "OR" and "AND" in kinds and "OR" not in kinds:
                hint = "An AND valve needs both inputs. This job needs OR."
            else:
                hint = "Follow a red row with Step and check each valve."
            text(self.screen, self.small, hint, 325, 521, RED)
        elif self.submission_ready:
            text(self.screen, self.small, "Choose how to deliver this working design.", 325, 521, TEAL)
        self.button((357, 554, 175, 39), "Close  [Esc]", lambda: setattr(self, "test_results", None), small=True)
        self.button((655, 554, 268, 39), "CHOOSE DELIVERY  [ENTER]", self.open_delivery_choices, active=self.submission_ready, small=True, enabled=self.submission_ready)

    def draw_delivery_modal(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((20, 29, 29, 180))
        self.screen.blit(shade, (0, 0))
        rounded(self.screen, (112, 73, 55), (294, 127, 692, 517), 4)
        rounded(self.screen, PAPER, (302, 135, 676, 501), 3)
        text(self.screen, self.heading, "CHOOSE DELIVERY TERMS", 330, 162, TEAL)
        text(self.screen, self.small, f"{self.commission.title}  /  {self.commission.customer}", 330, 202)
        text(self.screen, self.tiny, "Your original design stays in the library in all three choices.", 330, 238, MUTED)
        customer_id = CONTRACTS[self.commission.key][0]
        text(self.screen, self.tiny, f"Customer cash: {self.village.businesses[customer_id]['cash']} coins", 330, 264, MUTED)
        reward = self.commission.reward
        options = (
            ("1  INSTALL / KEEP RIGHTS", f"+{reward} now. Customer owns the machine; you own the design."),
            ("2  SELL A COPY", f"+{reward + max(6, reward // 3)} now. Customer owns a design copy."),
            ("3  LICENSE USE", f"+{reward // 2} now, then {LICENSE_RATE}/day while the machine operates."),
        )
        for i, (label, detail) in enumerate(options):
            y = 305 + i * 85
            self.button((330, y, 620, 68), "", lambda m=("install", "sell", "license")[i]: self.submit_design(m), small=True)
            text(self.screen, self.small, label, 348, y + 8)
            text(self.screen, self.tiny, detail, 348, y + 39, MUTED)
        if self.delivery_error:
            text(self.screen, self.tiny, self.delivery_error, 330, 558, RED)
        self.button((824, 584, 128, 37), "BACK [ESC]", lambda: setattr(self, "delivery_open", False), small=True)

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
        else:
            effects = ("Market cooling protects one loaf every sixth day", "Less spoiled bread reaches the price calculation")
        self.draw_lines(effects, 405, 420, self.small, 28, TEAL)
        rights = {"install": "You keep the design rights.", "sell": "Customer owns a copy; your original stays yours.",
                  "license": f"You own the design; earn {LICENSE_RATE} coins per paid day."}[self.success_mode]
        text(self.screen, self.tiny, rights, 405, 493, MUTED)
        self.button((354, 548, 270, 43), "Keep building  [Esc]", lambda: setattr(self, "success_job", None), small=True)
        self.button((655, 548, 270, 43), "Return to town  [Enter]", lambda: setattr(self, "scene", "town"), active=True, small=True)

    def draw_menu(self):
        self.screen.fill((69, 91, 86))
        for y in range(0, SCREEN_H, 34):
            for x in range(0, SCREEN_W, 68):
                pygame.draw.rect(self.screen, (78, 100, 94), (x + (34 if y // 34 % 2 else 0), y, 64, 30), border_radius=3)
        rounded(self.screen, (49, 63, 62), (145, 27, 990, 707), 5)
        rounded(self.screen, (124, 75, 58), (153, 35, 974, 691), 4, 7)
        rounded(self.screen, PAPER, (173, 51, 934, 655), 3)
        text(self.screen, self.big, "NUMBERMILL", 212, 77, TEAL)
        text(self.screen, self.small, "COPPERSIDE VILLAGE  /  SAVE ARCHIVE", 212, 121, COPPER)
        text(self.screen, self.small, "Choose a slot to continue, or create a new village.", 212, 158)
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
                village = village_from_data(data["village"])
                finished = (int(village.mill_machine) + int(village.bakery_machine)
                            + int(village.vent_machine) + int(village.market_machine))
                detail = f"Day {village.day}  /  {village.coins} coins  /  {finished} of {len(COMMISSIONS)} jobs complete"
                if data.get("legacy"):
                    detail += "  /  Existing save"
            text(self.screen, self.tiny, detail, 230, y + 46, MUTED if data is None else TEAL)
            if data is None:
                self.button((843, y + 14, 203, 43), "CREATE", lambda s=slot: self.start_slot(s), active=True, small=True)
            else:
                self.button((843, y + 14, 117, 43), "LOAD", lambda s=slot: self.start_slot(s), active=data != "unreadable", small=True, enabled=data != "unreadable")
                self.button((968, y + 14, 78, 43), "DELETE", lambda s=slot: self.request_delete_slot(s), small=True)
        text(self.screen, self.tiny, self.message[:95] if self.message_timer > 0 else "Progress saves when you return to this menu.", 212, 626, MUTED)
        self.button((843, 651, 203, 40), "EXIT GAME", lambda: setattr(self, "running", False), small=True)
        text(self.screen, self.tiny, "Press 1-5 for a slot.  Q or Esc exits here.", 212, 661, MUTED)
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
        self.screen.fill((69, 91, 86))
        rounded(self.screen, (112, 73, 55), (75, 35, 1130, 688), 4)
        rounded(self.screen, PAPER, (86, 46, 1108, 666), 3)
        text(self.screen, self.big, "VILLAGE CONTRACTS", 120, 75, TEAL)
        text(self.screen, self.small, "Choose a job. Your current floor plan stays available to reuse.", 120, 121)
        jobs = list(COMMISSIONS.values())
        self.contract_page = min(self.contract_page, (len(jobs) - 1) // 3)
        for row, job in enumerate(jobs[self.contract_page * 3:self.contract_page * 3 + 3]):
            y = 161 + row * 152
            offer = self.village.offers.get(job.key)
            state = offer["status"] if offer else "waiting"
            locked = state == "waiting"
            status = {"player": "YOU DELIVERED", "rival": "NELL DELIVERED",
                      "bid": "NELL BID", "open": "AVAILABLE", "waiting": "WAITING"}[state]
            rounded(self.screen, (231, 218, 185), (113, y, 1052, 143), 3)
            text(self.screen, self.heading, job.title, 135, y + 8)
            text(self.screen, self.small, status, 985, y + 13, MUTED if locked else TEAL)
            timing = (f"Due {offer['due_day']} / Nell {offer['finish_day']}" if state == "bid" else
                      f"Due day {offer['due_day']}" if state == "open" else
                      "Delivered late" if state in ("player", "rival") and offer.get("missed_deadline") else
                      "Delivered" if state in ("player", "rival") else
                      "Awaiting business demand")
            text(self.screen, self.small, f"{job.customer}  /  {job.reward} coins  /  {timing}", 135, y + 39, COPPER)
            text(self.screen, self.small, f"Required: {job.logic}  /  {8 if job.logic == 'MAJORITY' else 4} input checks", 135, y + 64)
            text(self.screen, self.small, job.benefit, 135, y + 88, TEAL)
            if locked:
                note = f"Complete the {job.prerequisite} contract first."
            elif state in ("open", "bid"):
                note = offer["reason"]
            elif offer.get("delivery_mode") == "license":
                paid = self.village.licenses.get(job.key, {}).get("paid_day") == self.village.day
                note = f"Design: You  /  Licensed to {offer['licensee']} for {LICENSE_RATE}/day ({'active' if paid else 'paused'})."
            elif offer.get("copy_owner"):
                note = f"Design: {offer['design_owner']}  /  {offer['copy_owner']} owns a copy."
            else:
                note = f"Design: {offer['design_owner']}  /  Installed machine belongs to {job.customer}."
            text(self.screen, self.tiny, note, 135, y + 117, MUTED)
            self.button((873, y + 91, 265, 40), f"{job.level}  {'REVISIT' if state in ('player', 'rival') else 'BUILD DESIGN'}", lambda k=job.key: self.choose_contract(k), active=not locked, enabled=not locked, small=True)
        if self.contract_page > 0:
            self.button((484, 644, 165, 43), "PREV  [LEFT]", lambda: setattr(self, "contract_page", self.contract_page - 1), small=True)
        if (self.contract_page + 1) * 3 < len(jobs):
            self.button((676, 644, 165, 43), "NEXT  [RIGHT]", lambda: setattr(self, "contract_page", self.contract_page + 1), active=True, small=True)
        self.button((894, 644, 242, 43), "BACK  [ESC]", lambda: setattr(self, "scene", self.board_return_scene), small=True)
        text(self.screen, self.tiny, f"Page {self.contract_page + 1}/{(len(jobs) + 2) // 3}  /  1-{len(jobs)} choose job", 135, 657, MUTED)

    def draw(self):
        self.buttons.clear()
        if self.scene == "invention":
            inventions.screen(self)
            pygame.display.flip()
            return
        if self.scene == "compute":
            workbench.compute_screen(self)
            pygame.display.flip()
            return
        if self.scene == "contracts":
            self.draw_contract_board()
            pygame.display.flip()
            return
        if self.scene == "ledger":
            ledger.draw(self)
            pygame.display.flip()
            return
        if self.scene == "menu":
            self.draw_menu()
            pygame.display.flip()
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
            self.button((867, 26, 126, 34), "LEDGER [L]", self.open_ledger, small=True)
            self.button((1005, 26, 166, 34), "CONTRACTS [J]", self.open_contract_board, small=True)
            pygame.display.flip()
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
            pygame.display.flip()
            return
        self.draw_background()
        self.button((700, 60, 158, 40), "CONTRACTS [J]", self.open_contract_board, small=True)
        self.button((868, 60, 145, 40), "COMPUTE [C]", self.open_compute, small=True)
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
        status = self.message if self.message_timer > 0 else f"Day {self.village.day}: {self.village.market_note}"
        hovered_part = self.circuit.parts.get(self.board_pos(pygame.mouse.get_pos()))
        if hovered_part and hovered_part.kind == "DEVICE":
            device = hovered_part.device
            ports = device.get("ports", {"A": "Input A", "B": "Input B", "OUT": "Output"})
            directions = ("north", "east", "south", "west")
            inputs, outputs = hovered_part.ports()
            status = (f"{device['name']} v{device.get('version', 1)} | "
                      f"{ports['A']} ({directions[inputs[0]]}), {ports['B']} ({directions[inputs[1]]}) -> "
                      f"{ports['OUT']} ({directions[outputs[0]]}) | Right-click: inspect")
        elif hovered_part and hovered_part.kind in ("A", "B", "LAMP"):
            key = "OUT" if hovered_part.kind == "LAMP" else hovered_part.kind
            status = f"Port {key}: {self.port_names[key]}"
        text(self.screen, self.tiny, status[:145], 69, 733, (245, 223, 172))
        if self.success_job is not None:
            self.draw_success_modal()
        elif self.test_results is not None:
            self.draw_test_modal()
        elif self.delivery_open:
            self.draw_delivery_modal()
        elif self.help_open:
            self.draw_help_modal()
        if self.port_editor is not None:
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((20, 29, 29, 180)); self.screen.blit(shade, (0, 0))
            rounded(self.screen, PAPER, (330, 155, 620, 420), 10)
            text(self.screen, self.heading, "Device port names", 380, 184, TEAL)
            text(self.screen, self.small, "Click a field; type a name. Tab moves to the next.", 380, 224)
            for i, label in enumerate(("A / west", "B / south", "Output / east")):
                y = 260 + i * 70
                rounded(self.screen, CREAM, (380, y, 520, 48), 5)
                rounded(self.screen, TEAL if self.port_editor['field'] == i else STONE, (380, y, 520, 48), 5, 2)
                text(self.screen, self.tiny, label, 392, y + 7, MUTED)
                text(self.screen, self.small, self.port_editor['values'][i], 520, y + 17)
            self.button((700, 505, 200, 40), "Save names  [Enter]", self.finish_ports, small=True)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.scene == "menu":
                        self.running = False
                    else:
                        self.return_to_menu()
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos, event.button)
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
