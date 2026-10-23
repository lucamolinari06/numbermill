"""Small, data-driven business economy for the first village."""

from dataclasses import dataclass, field

from citizens import decide, prepare


# Each firm is an instance; its kind supplies the production recipe.
BUSINESS_TYPES = {
    "farm": {"input": None, "output": "grain", "capacity": 4, "input_price": 0},
    "mill": {"input": "grain", "output": "flour", "capacity": 1, "input_price": 2},
    "bakery": {"input": "flour", "output": "bread", "capacity": 3, "input_price": 5},
    "market": {"input": "bread", "output": "bread", "capacity": 4, "input_price": 7},
    "fuel": {"input": None, "output": "fuel", "capacity": 7, "input_price": 0},
    "parts": {"input": "fuel", "output": "parts", "capacity": 2, "input_price": 3},
}

# Upgrades affect an operation, not a global village score.
MACHINE_EFFECTS = {
    "mill_controller": {"capacity": 3},
    "bakery_selector": {"capacity": 2},
    "bakery_vent": {},
    "market_cooler": {},
    "farm_pump": {"capacity": 1},
    "market_sorter": {},
}

CONTRACTS = {
    "mill": ("mill", "mill_controller", 24),
    "bakery": ("bakery", "bakery_selector", 30),
    "vent": ("bakery", "bakery_vent", 20),
    "market": ("market", "market_cooler", 22),
    "pump": ("farm", "farm_pump", 28),
    "sorter": ("market", "market_sorter", 26),
}

LICENSE_RATE = 2


def starting_businesses(grain: int, flour: int, bread: int, mill_machine: bool, bakery_machine: bool,
                        vent_machine: bool = False, market_machine: bool = False):
    return {
        "farm": {"kind": "farm", "name": "Copperside Farm", "owner": "Farmer", "parent_id": None,
                 "cash": 120, "workers": 1, "stock": {"grain": grain}, "machines": []},
        "mill": {"kind": "mill", "name": "Copperside Mill", "owner": "Miller", "parent_id": None,
                 "cash": 120, "workers": 1, "stock": {"flour": flour},
                 "machines": ["mill_controller"] if mill_machine else []},
        "bakery": {"kind": "bakery", "name": "Copperside Bakery", "owner": "Baker", "parent_id": None,
                   "cash": 120, "workers": 1, "stock": {"bread": bread},
                   "machines": (["bakery_selector"] if bakery_machine else []) +
                               (["bakery_vent"] if vent_machine else [])},
        "market": {"kind": "market", "name": "Copperside Market", "owner": "Merchant", "parent_id": None,
                   "cash": 120, "workers": 1, "stock": {"bread": 2},
                   "machines": ["market_cooler"] if market_machine else []},
        "fuel_yard": {"kind": "fuel", "name": "Mely's Fuel Yard", "owner": "Mely", "parent_id": None,
                      "cash": 90, "workers": 1, "stock": {"fuel": 2}, "machines": []},
        "parts_shop": {"kind": "parts", "name": "Luca's Repair Shop", "owner": "Luca", "parent_id": None,
                       "cash": 90, "workers": 1, "stock": {"parts": 1}, "machines": []},
    }


@dataclass
class Village:
    day: int = 1
    coins: int = 12
    grain: int = 6
    flour: int = 1
    bread: int = 2
    mill_machine: bool = False
    bakery_machine: bool = False
    vent_machine: bool = False
    market_machine: bool = False
    active_commission: str = "mill"
    bread_price: int = 8
    market_note: str = "Mill output limits bakery supply."
    journal: list[str] = field(default_factory=lambda: [
        "Mill: needs a safety controller before full production.",
        "Bakery: flour deliveries are limited.",
    ])
    businesses: dict[str, dict] = field(default_factory=dict)
    player_bread: int = 0
    households: dict[str, dict] = field(default_factory=dict)
    citizens: list[dict] = field(default_factory=list)
    offers: dict[str, dict] = field(default_factory=dict)
    rival_cash: int = 0
    rival_busy_until: int = 0
    last_contract_event: str = ""
    licenses: dict[str, dict] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    service_active: bool = False
    service_earned: int = 0
    service_days: int = 0
    service_customer: str = ""
    service_paid_day: int = 0
    power_checked_day: int = 0
    trade_history: list[dict] = field(default_factory=list)
    daily_trades: list[dict] = field(default_factory=list)
    compute_designs: dict[str, dict] = field(default_factory=dict)
    compute_orders: list[dict] = field(default_factory=list)
    compute_earned: int = 0
    arithmetic_unlocks: list[str] = field(default_factory=list)
    invention_drafts: dict[str, dict] = field(default_factory=dict)
    invention_records: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.businesses, dict) or not self.businesses:
            # Older saves only contain the village totals; seed firms from them.
            self.businesses = starting_businesses(self.grain, self.flour, self.bread, self.mill_machine,
                                                  self.bakery_machine, self.vent_machine, self.market_machine)
        elif "market" not in self.businesses:
            # Saves made before the market opened keep their original firms.
            self.businesses["market"] = starting_businesses(0, 0, 0, False, False)["market"]
        for key in ("fuel_yard", "parts_shop"):
            self.businesses.setdefault(key, starting_businesses(0, 0, 0, False, False)[key])
        if not self.households:
            self.households = {key: {"cash": 40, "bread_need": 1, "missed_meals": 0, "bought": 0}
                               for key in ("home_1", "home_2")}
        if not self.citizens:
            self.citizens = [
                {"name": "Ada", "home": "home_1", "workplace": "farm", "wage": 4},
                {"name": "Bram", "home": "home_1", "workplace": "mill", "wage": 4},
                {"name": "Cora", "home": "home_2", "workplace": "bakery", "wage": 4},
                {"name": "Dara", "home": "home_2", "workplace": "market", "wage": 4},
            ]
        self.households.setdefault("home_3", {"cash": 60, "bread_need": 1, "missed_meals": 0, "bought": 0})
        for name, workplace in (("Mely", "fuel_yard"), ("Luca", "parts_shop")):
            if not any(person.get("name") == name for person in self.citizens):
                self.citizens.append({"name": name, "home": "home_3", "workplace": workplace, "wage": 4})
        for person in self.citizens:
            prepare(person)
        if not isinstance(self.history, list):
            self.history = []
        if not self.history:
            self.bread = sum(firm["stock"].get("bread", 0) for firm in self.businesses.values())
            self.record_history()
        if not isinstance(self.trade_history, list):
            self.trade_history = []
        if not self.trade_history:
            self.trade_history = [{"day": self.day, "entries": []}]
        if not isinstance(self.daily_trades, list):
            self.daily_trades = []
        if not isinstance(self.offers, dict):
            self.offers = {}
        if not isinstance(self.licenses, dict):
            self.licenses = {}
        for key in ("pump", "sorter"):
            self.offers.pop(key, None) if self.offers.get(key, {}).get("status") == "waiting" else None
        for key, (business_id, machine, _) in CONTRACTS.items():
            if machine in self.businesses[business_id]["machines"]:
                self.offers.setdefault(key, {"status": "player", "posted_day": self.day,
                                             "reason": "Machine already installed."})
        for offer in self.offers.values():
            offer.setdefault("due_day", offer.get("posted_day", self.day) + 4)
            if offer.get("status") in ("player", "rival"):
                offer.setdefault("design_owner", "You" if offer["status"] == "player" else "Nell")
                offer.setdefault("delivery_mode", "install" if offer["status"] == "player" else "sell")
        self._post_offers()

    def _post_offers(self) -> None:
        """Post when projected avoided losses exceed the job's price."""
        if "mill" not in self.offers:
            missing = min(3, max(0, self.capacity("farm") - self.capacity("mill")))
            if missing * 2 * 8 > CONTRACTS["mill"][2]:
                self.offers["mill"] = {"status": "open", "posted_day": self.day,
                                       "due_day": self.day + 4,
                                       "reason": f"Grain supply exceeds mill capacity by {missing}/day."}
                self.last_contract_event = "Mill posted a controller job: grain exceeds flour capacity."
                self.journal.insert(0, self.last_contract_event)
        if "bakery" not in self.offers and self.mill_machine:
            missing = min(2, max(0, min(self.capacity("mill"),
                                          sum(h["bread_need"] for h in self.households.values()) + 2)
                                      - self.capacity("bakery")))
            if missing * 4 * 8 > CONTRACTS["bakery"][2]:
                self.offers["bakery"] = {"status": "open", "posted_day": self.day,
                                         "due_day": self.day + 4,
                                         "reason": f"Flour and customers exceed ovens by {missing}/day."}
                self.last_contract_event = "Bakery posted a selector job: ovens limit bread supply."
                self.journal.insert(0, self.last_contract_event)
        if "vent" not in self.offers and self.bakery_machine:
            avoided_loss = min(self.capacity("bakery"), self.capacity("mill")) * 6
            if avoided_loss > CONTRACTS["vent"][2]:
                self.offers["vent"] = {"status": "open", "posted_day": self.day,
                                       "due_day": self.day + 4,
                                       "reason": "Boiler shutdowns cost a day's bread every seventh day."}
                self.last_contract_event = "Bakery posted a safety vent job to avoid boiler shutdowns."
                self.journal.insert(0, self.last_contract_event)
        if "market" not in self.offers and self.bakery_machine:
            avoided_loss = self.bread_price * 4
            if avoided_loss > CONTRACTS["market"][2]:
                self.offers["market"] = {"status": "open", "posted_day": self.day,
                                         "due_day": self.day + 4,
                                         "reason": "Uncooled bread spoils every sixth day."}
                self.last_contract_event = "Market posted a cooling job to prevent bread spoilage."
                self.journal.insert(0, self.last_contract_event)
        if "pump" not in self.offers and self.mill_machine:
            self.offers["pump"] = {"status": "open", "posted_day": self.day,
                                    "due_day": self.day + 4,
                                    "reason": "The farm wants irrigation without interrupting mill water."}
        if "pump" in self.offers and "farm_pump" in self.businesses["farm"]["machines"]:
            self.offers["pump"].setdefault("status", "player")
        if "sorter" not in self.offers and self.market_machine:
            self.offers["sorter"] = {"status": "open", "posted_day": self.day,
                                     "due_day": self.day + 4,
                                     "reason": "The merchant needs a flexible signal for two busy streets."}
        if "sorter" in self.offers and "market_sorter" in self.businesses["market"]["machines"]:
            self.offers["sorter"].setdefault("status", "player")
        self.journal = self.journal[:5]

    def _resolve_deadlines(self) -> None:
        for key, offer in self.offers.items():
            if offer["status"] not in ("open", "bid") or self.day <= offer["due_day"]:
                continue
            if offer["status"] == "bid":
                if offer.get("missed_deadline"):
                    continue
                offer["missed_deadline"] = True
                event = f"Day {self.day}: {key.title()} missed its deadline; the owner chose to wait for Nell."
            else:
                offer["missed_deadline"] = True
                offer["due_day"] = self.day + 3
                event = f"Day {self.day}: {key.title()} postponed expansion and renewed its offer."
            self.last_contract_event = event
            self.journal.insert(0, event)
        self.journal = self.journal[:5]

    def _advance_rival(self) -> None:
        for key, offer in list(self.offers.items()):
            if offer["status"] == "bid" and self.day >= offer["finish_day"]:
                business_id, machine, reward = CONTRACTS[key]
                firm = self.businesses[business_id]
                if firm["cash"] < reward:
                    offer["status"] = "open"
                    offer["posted_day"] = self.day
                    offer["due_day"] = self.day + 3
                    offer.pop("finish_day", None)
                    self.last_contract_event = f"Day {self.day}: {firm['name']} could not afford Nell; expansion postponed."
                    self.journal.insert(0, self.last_contract_event)
                    continue
                if machine not in firm["machines"]:
                    firm["machines"].append(machine)
                    firm["cash"] -= reward
                    self.rival_cash += reward
                setattr(self, f"{key}_machine", True)
                offer["status"] = "rival"
                offer["design_owner"] = "Nell"
                offer["copy_owner"] = firm["owner"]
                offer["delivery_mode"] = "sell"
                self.last_contract_event = f"Day {self.day}: Nell installed the {key} machine for {reward} coins."
                self.journal.insert(0, self.last_contract_event)
                self._post_offers()
        if self.day < self.rival_busy_until:
            return
        for key, offer in self.offers.items():
            if offer["status"] == "open" and self.day - offer["posted_day"] >= 3:
                offer["status"] = "bid"
                offer["finish_day"] = self.day + 2
                self.rival_busy_until = offer["finish_day"]
                self.last_contract_event = f"Day {self.day}: Nell bid on the {key} job; delivery day {offer['finish_day']}."
                self.journal.insert(0, self.last_contract_event)
                break
        self.journal = self.journal[:5]

    def buy_bread(self) -> str:
        market = self.businesses["market"]
        if market["stock"].get("bread", 0) < 1:
            return "No bread yet. Advance a day for the next delivery."
        if self.coins < self.bread_price:
            return f"You need {self.bread_price} coins for a loaf."
        market["stock"]["bread"] -= 1
        market["cash"] += self.bread_price
        self.coins -= self.bread_price
        self.player_bread += 1
        self.bread -= 1
        self._record_trade("Copperside Market", "You", "bread", 1, self.bread_price)
        if self.trade_history and self.trade_history[-1]["day"] == self.day:
            self.trade_history[-1]["entries"].append(self.daily_trades[-1])
        return f"Bought one loaf. Your pantry holds {self.player_bread} bread."

    def _record_trade(self, seller, buyer, good, units, coins):
        self.daily_trades.append({"from": seller, "to": buyer, "good": good,
                                  "units": units, "coins": coins})

    def record_history(self) -> None:
        self.history.append({
            "day": self.day, "population": len(self.citizens), "bread_price": self.bread_price,
            "bread": self.bread, "missed_meals": sum(h["missed_meals"] for h in self.households.values()),
            "business_cash": {key: firm["cash"] for key, firm in self.businesses.items()},
            "player_coins": self.coins,
        })
        self.history = self.history[-120:]

    def toggle_service(self) -> str:
        if not self.service_active and not any(offer.get("status") == "player" for offer in self.offers.values()):
            return "Deliver a working design before offering workshop service."
        self.service_active = not self.service_active
        return "Workshop service opened for daily customers." if self.service_active else "Workshop service paused."

    def talk_to(self, name: str, topic: str) -> None:
        person = next((p for p in self.citizens if p["name"] == name), None)
        if person is None or person.get("last_talk_day") == self.day:
            return
        person["last_talk_day"] = self.day
        person["relationships"]["You"] = min(100, person["relationships"].get("You", 20) + 2)
        person["memories"].append(f"Day {self.day}: spoke with you about {topic}.")
        person["memories"] = person["memories"][-6:]

    def _run_service(self) -> None:
        if not self.service_active:
            return
        fuel = self.businesses["fuel_yard"]
        parts = self.businesses["parts_shop"]
        customers = [self.businesses[business_id] for key, (business_id, _, _) in CONTRACTS.items()
                     if self.offers.get(key, {}).get("status") == "player"]
        customer = next((firm for firm in customers if firm["cash"] >= 7), None)
        if customer is None or fuel["stock"].get("fuel", 0) < 1 or parts["stock"].get("parts", 0) < 1:
            self.journal.insert(0, f"Day {self.day}: workshop service had no funded customer or lacked fuel/parts.")
            return
        if self.coins < 5:
            self.journal.insert(0, f"Day {self.day}: workshop service needed 5 coins for fuel and parts.")
            return
        fuel["stock"]["fuel"] -= 1
        fuel["cash"] += 3
        self._record_trade(fuel["name"], "Your Workshop", "fuel", 1, 3)
        parts["stock"]["parts"] -= 1
        parts["cash"] += 2
        self._record_trade(parts["name"], "Your Workshop", "parts", 1, 2)
        customer["cash"] -= 7
        self.coins += 2
        self._record_trade("Your Workshop", customer["name"], "service", 1, 7)
        self.service_customer = next(key for key, firm in self.businesses.items() if firm is customer)
        self.service_paid_day = self.day
        self.service_earned += 2
        self.service_days += 1
        self.journal.insert(0, f"Day {self.day}: serviced {customer['name']} (+1 capacity); earned 2c net.")

    def capacity(self, business_id: str) -> int:
        firm = self.businesses[business_id]
        recipe = BUSINESS_TYPES[firm["kind"]]
        machine_bonus = sum(MACHINE_EFFECTS.get(machine, {}).get("capacity", 0)
                            for machine in firm["machines"] if self.machine_ready(business_id, machine))
        service_bonus = int(self.service_paid_day == self.day and self.service_customer == business_id)
        planning_bonus = int(firm.get("compute_day") in (self.day, self.day - 1))
        worker_limit = 8 if firm["kind"] == "fuel" else 6
        return max(0, min(recipe["capacity"] + machine_bonus + service_bonus + planning_bonus, firm["workers"] * worker_limit))

    def _supply_steam(self, firm: dict) -> None:
        if not any(self.machine_active(machine) for machine in firm["machines"]):
            return
        fuel = self.businesses["fuel_yard"]
        if fuel is firm:
            return
        if fuel["stock"].get("fuel", 0) < 1 or firm["cash"] < 2:
            event = f"Day {self.day}: {firm['name']} lacked fuel; its steam machine paused."
            self.journal.insert(0, event)
            if not self.last_contract_event:
                self.last_contract_event = event
            return
        fuel["stock"]["fuel"] -= 1
        fuel["cash"] += 2
        firm["cash"] -= 2
        firm["powered_day"] = self.day
        self._record_trade(fuel["name"], firm["name"], "fuel", 1, 2)

    def machine_active(self, machine: str) -> bool:
        license_key = next((key for key, (_, installed, _) in CONTRACTS.items() if installed == machine), None)
        license_info = self.licenses.get(license_key)
        return license_info is None or license_info.get("paid_day") == self.day

    def machine_ready(self, business_id: str, machine: str) -> bool:
        firm = self.businesses[business_id]
        return (machine in firm["machines"] and self.machine_active(machine)
                and (self.power_checked_day != self.day or firm.get("powered_day") == self.day))

    def _pay_royalties(self) -> None:
        for key, license_info in self.licenses.items():
            if license_info.get("paid_day") == self.day:
                continue
            firm = self.businesses[CONTRACTS[key][0]]
            if firm["cash"] >= LICENSE_RATE:
                firm["cash"] -= LICENSE_RATE
                self.coins += LICENSE_RATE
                license_info["paid_day"] = self.day
                license_info["total_paid"] = license_info.get("total_paid", 0) + LICENSE_RATE
                event = f"Day {self.day}: {firm['name']} paid {LICENSE_RATE} coins to license your design."
            else:
                event = f"Day {self.day}: {firm['name']} could not pay; its licensed machine paused."
            if not self.last_contract_event or "could not pay" in event:
                self.last_contract_event = event
            self.journal.insert(0, event)
        self.journal = self.journal[:5]

    def fulfill_job(self, key: str, mode: str = "install") -> bool:
        if mode not in ("install", "sell", "license"):
            raise ValueError("Unknown delivery mode")
        business_id, machine, reward = CONTRACTS[key]
        offer = self.offers.get(key)
        firm = self.businesses[business_id]
        if offer is None or offer["status"] not in ("open", "bid") or machine in firm["machines"]:
            return False
        if (key == "bakery" and not self.mill_machine or
                key in ("vent", "market") and not self.bakery_machine or
                key == "pump" and not self.mill_machine or
                key == "sorter" and not self.market_machine):
            return False
        payout = (reward if mode == "install" else
                  reward + max(6, reward // 3) if mode == "sell" else reward // 2)
        if firm["cash"] < payout:
            return False
        firm["machines"].append(machine)
        firm["cash"] -= payout
        self.coins += payout
        setattr(self, f"{key}_machine", True)
        offer["status"] = "player"
        offer["design_owner"] = "You"
        offer["delivery_mode"] = mode
        if mode == "sell":
            offer["copy_owner"] = firm["owner"]
        elif mode == "license":
            offer["licensee"] = firm["owner"]
            self.licenses[key] = {"paid_day": self.day, "total_paid": 0}
        action = {"install": "installed your machine", "sell": "bought a copy of your design",
                  "license": "licensed your design"}[mode]
        self.journal.insert(0, f"{firm['name']} {action} for {payout} coins.")
        self.journal = self.journal[:5]
        self._post_offers()
        return True

    def complete_mill_job(self, mode: str = "install") -> bool:
        return self.fulfill_job("mill", mode)

    def complete_bakery_job(self, mode: str = "install") -> bool:
        return self.fulfill_job("bakery", mode)

    def complete_vent_job(self, mode: str = "install") -> bool:
        return self.fulfill_job("vent", mode)

    def complete_market_job(self, mode: str = "install") -> bool:
        return self.fulfill_job("market", mode)

    def _buy_input(self, buyer: dict, good: str, needed: int, unit_price: int) -> int:
        bought = 0
        for supplier in self.businesses.values():
            if supplier is buyer:
                continue
            available = supplier["stock"].get(good, 0)
            count = min(available, needed - bought, max(0, buyer["cash"] // unit_price))
            if count <= 0:
                continue
            supplier["stock"][good] -= count
            supplier["cash"] += count * unit_price
            buyer["cash"] -= count * unit_price
            self._record_trade(supplier["name"], buyer["name"], good, count, count * unit_price)
            bought += count
            if bought == needed:
                break
        return bought

    def _sell_traveler_parts(self) -> None:
        # A passing mechanic provides Luca a small regular buyer even before
        # the player opens a service; the external payment is explicit trade.
        firm = self.businesses["parts_shop"]
        if self.day < 7 or firm["stock"].get("parts", 0) < 1:
            return
        firm["stock"]["parts"] -= 1
        firm["cash"] += 8
        self._record_trade(firm["name"], "Traveling Mechanic", "parts", 1, 8)

    def advance_day(self) -> None:
        self.day += 1
        self.power_checked_day = self.day
        self.daily_trades = []
        self.last_contract_event = ""
        self._resolve_deadlines()
        self._advance_rival()
        self._pay_royalties()
        self._run_service()
        produced = {"grain": 0, "flour": 0, "bread": 0}
        demand = sum(home["bread_need"] for home in self.households.values())
        for kind in ("fuel", "farm", "mill", "bakery", "market", "parts"):
            for business_id, firm in self.businesses.items():
                if firm["kind"] != kind:
                    continue
                recipe = BUSINESS_TYPES[kind]
                self._supply_steam(firm)
                amount = self.capacity(business_id)
                if kind in ("fuel", "parts"):
                    buffer_target = 12 if kind == "fuel" else 6
                    amount = min(amount, max(0, buffer_target - firm["stock"].get(recipe["output"], 0)))
                if kind == "bakery" and "bakery_selector" in firm["machines"] and not (
                    self.machine_ready(business_id, "bakery_vent")
                ) and self.day % 7 == 0:
                    amount = 0
                    self.last_contract_event = f"Day {self.day}: bakery boiler shut down; no bread was baked."
                    self.journal.insert(0, self.last_contract_event)
                if kind == "market":
                    amount = min(amount, max(0, demand + 2 - firm["stock"].get("bread", 0)))
                if kind == "farm" and "farm_pump" in firm["machines"] and self.day % 2 == 0:
                    amount += 1
                if recipe["input"]:
                    amount = self._buy_input(firm, recipe["input"], amount, recipe["input_price"])
                firm["stock"][recipe["output"]] = firm["stock"].get(recipe["output"], 0) + amount
                if kind != "market" and recipe["output"] in produced:
                    produced[recipe["output"]] += amount

        self._sell_traveler_parts()

        # Wages and purchases transfer existing money between firms and homes.
        for citizen in self.citizens:
            employer = self.businesses.get(citizen["workplace"])
            if employer is None:
                continue
            wage = min(citizen["wage"], max(0, employer["cash"]))
            employer["cash"] -= wage
            self.households[citizen["home"]]["cash"] += wage
        sold = 0
        homes = list(self.households.values())
        offset = self.day % len(homes)
        for home in homes[offset:] + homes[:offset]:
            home["bought"] = 0
            for firm in self.businesses.values():
                if firm["kind"] != "market":
                    continue
                # Keep one loaf on the public counter for the player.
                count = min(max(0, firm["stock"].get("bread", 0) - 1),
                            home["bread_need"] - home["bought"], home["cash"] // self.bread_price)
                firm["stock"]["bread"] -= count
                firm["cash"] += count * self.bread_price
                home["cash"] -= count * self.bread_price
                home["bought"] += count
                sold += count
                if count:
                    home_id = next(key for key, value in self.households.items() if value is home)
                    self._record_trade(firm["name"], home_id.replace("_", " ").title(),
                                       "bread", count, count * self.bread_price)
            home["missed_meals"] += home["bread_need"] - home["bought"]

        for business_id, firm in self.businesses.items():
            if (firm["kind"] == "market" and self.day % 6 == 0
                    and firm["stock"].get("bread", 0) > 0
                    and not self.machine_ready(business_id, "market_cooler")):
                firm["stock"]["bread"] -= 1
                event = f"Day {self.day}: {firm['name']} lost one loaf to spoilage."
                if not self.last_contract_event:
                    self.last_contract_event = event
                self.journal.insert(0, event)

        for person in self.citizens:
            decide(person, self.households[person["home"]], self, day=self.day)

        self.grain = sum(firm["stock"].get("grain", 0) for firm in self.businesses.values())
        self.flour = sum(firm["stock"].get("flour", 0) for firm in self.businesses.values())
        self.bread = sum(firm["stock"].get("bread", 0) for firm in self.businesses.values())
        # Keep a small village's first shopping trip affordable while still
        # letting one additional loaf of output move the displayed price.
        self.bread_price = 8 + max(0, demand + 1 - produced["bread"]) // 2 + max(0, 2 - self.bread)
        if produced["bread"] < demand + 1:
            self.market_note = f"Bread pressure: {produced['bread']} made for {demand + 1} wanted."
        elif self.bread < 2:
            self.market_note = "Bread price pressure: little stock remains."
        else:
            self.market_note = "Bread supply meets today's demand."
        self.journal.insert(0, f"Day {self.day}: mill sent {produced['flour']} flour; market sold {sold} bread.")
        self.journal = self.journal[:5]
        self._post_offers()
        self.record_history()
        self.trade_history.append({"day": self.day, "entries": list(self.daily_trades)})
        self.trade_history = self.trade_history[-120:]
