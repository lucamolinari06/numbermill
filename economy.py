"""Small, data-driven business economy for the first village."""

from dataclasses import dataclass, field

from citizens import decide, prepare


# Each firm is an instance; its kind supplies the production recipe.
BUSINESS_TYPES = {
    "farm": {"input": None, "output": "grain", "capacity": 4, "input_price": 0},
    "mill": {"input": "grain", "output": "flour", "capacity": 1, "input_price": 2},
    "bakery": {"input": "flour", "output": "bread", "capacity": 3, "input_price": 4},
    "market": {"input": "bread", "output": "bread", "capacity": 4, "input_price": 6},
    "fuel": {"input": None, "output": "fuel", "capacity": 7, "input_price": 0},
    "parts": {"input": "fuel", "output": "parts", "capacity": 2, "input_price": 3},
    "sawmill": {"input": None, "output": "timber", "capacity": 4, "input_price": 0},
    "foundry": {"input": "timber", "output": "metal", "capacity": 3, "input_price": 1},
    "toolmaker": {"input": "metal", "output": "fittings", "capacity": 2, "input_price": 2},
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

from commissions import EXTENDED_CONTRACTS
CONTRACTS.update(EXTENDED_CONTRACTS)
for _business, _machine, _reward in EXTENDED_CONTRACTS.values():
    MACHINE_EFFECTS[_machine] = {"passive": True, "buffer": 1,
                                 "capacity": int(_business in ("farm", "mill", "bakery", "market"))}

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
        "sawmill": {"kind": "sawmill", "name": "Iris's Timber Yard", "owner": "Iris", "parent_id": None,
                    "cash": 50, "workers": 0, "owner_operated": True, "stock": {"timber": 8}, "machines": []},
        "foundry": {"kind": "foundry", "name": "Otto's Foundry", "owner": "Otto", "parent_id": None,
                    "cash": 50, "workers": 0, "owner_operated": True, "stock": {"metal": 6}, "machines": []},
        "toolmaker": {"kind": "toolmaker", "name": "Tess's Toolworks", "owner": "Tess", "parent_id": None,
                      "cash": 50, "workers": 0, "owner_operated": True, "stock": {"fittings": 4}, "machines": []},
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
    inventor_profiles: dict = field(default_factory=dict)
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
    sequential_drafts: dict[str, dict] = field(default_factory=dict)
    sequential_records: dict[str, dict] = field(default_factory=dict)
    manufacturing: dict = field(default_factory=dict)
    daily_life: dict = field(default_factory=dict)
    last_day_report: dict = field(default_factory=dict)
    pump_machine: bool = False
    sorter_machine: bool = False
    service_open_day: int = 0
    migration: dict = field(default_factory=dict)
    migration_events: list[dict] = field(default_factory=list)
    migration_status: str = "Arrival reviews begin after completed days of food, savings and available work."
    material_inventory: dict[str, int] = field(default_factory=dict)
    material_reservations: dict[str, dict] = field(default_factory=dict)
    material_advances: dict[str, int] = field(default_factory=dict)
    competition: dict = field(default_factory=dict)
    competition_status: str = "Jun is considering a second bakery when population, paying demand, and spare flour can support it."
    competition_events: list[dict] = field(default_factory=list)
    character_projects: dict = field(default_factory=dict)
    character_project_review_day: int = 0

    def __post_init__(self):
        if not isinstance(self.businesses, dict) or not self.businesses:
            # Older saves only contain the village totals; seed firms from them.
            self.businesses = starting_businesses(self.grain, self.flour, self.bread, self.mill_machine,
                                                  self.bakery_machine, self.vent_machine, self.market_machine)
        elif "market" not in self.businesses:
            # Saves made before the market opened keep their original firms.
            self.businesses["market"] = starting_businesses(0, 0, 0, False, False)["market"]
        for key in ("fuel_yard", "parts_shop", "sawmill", "foundry", "toolmaker"):
            self.businesses.setdefault(key, starting_businesses(0, 0, 0, False, False)[key])
        for name in ("material_inventory", "material_reservations", "material_advances", "competition", "character_projects"):
            if not isinstance(getattr(self, name), dict):
                setattr(self, name, {})
        if not self.households:
            self.households = {key: {"cash": 40, "bread_need": 1, "missed_meals": 0, "bought": 0}
                               for key in ("home_1", "home_2")}
        if not self.citizens:
            self.citizens = [
                {"name": "Ada", "home": "home_1", "workplace": "farm", "wage": 4},
                {"name": "Bram", "home": "home_1", "workplace": "mill", "wage": 4},
                {"name": "Agnes", "home": "home_2", "workplace": "bakery", "wage": 4},
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
                setattr(self, f"{key}_machine", True)
                self.offers.setdefault(key, {"status": "player", "posted_day": self.day,
                                             "reason": "Machine already installed."})
        for offer in self.offers.values():
            offer.setdefault("due_day", offer.get("posted_day", self.day) + 4)
            if offer.get("status") in ("player", "rival"):
                offer.setdefault("design_owner", "Boole" if offer["status"] == "player" else "Grace")
                offer.setdefault("delivery_mode", "install" if offer["status"] == "player" else "sell")
        # Loading must not discard existing journal entries.
        self._post_offers()

    def _post_offers(self) -> None:
        """Post when projected avoided losses exceed the job's price."""
        if "mill" not in self.offers:
            missing = min(3, max(0, self.capacity("farm", nominal=True) - self.capacity("mill", nominal=True)))
            if missing * 2 * 8 > CONTRACTS["mill"][2]:
                self.offers["mill"] = {"status": "open", "posted_day": self.day,
                                       "due_day": self.day + 4,
                                       "reason": f"Grain supply exceeds mill capacity by {missing}/day."}
                self.last_contract_event = "Mill posted a controller job: grain exceeds flour capacity."
                self.journal.insert(0, self.last_contract_event)
        if "bakery" not in self.offers and self.mill_machine:
            missing = min(2, max(0, min(self.capacity("mill", nominal=True),
                                          sum(h["bread_need"] for h in self.households.values()) + 2)
                                      - self.capacity("bakery", nominal=True)))
            if missing * 4 * 8 > CONTRACTS["bakery"][2]:
                self.offers["bakery"] = {"status": "open", "posted_day": self.day,
                                         "due_day": self.day + 4,
                                         "reason": f"Flour and customers exceed ovens by {missing}/day."}
                self.last_contract_event = "Bakery posted a selector job: ovens limit bread supply."
                self.journal.insert(0, self.last_contract_event)
        if "vent" not in self.offers and self.bakery_machine:
            avoided_loss = min(self.capacity("bakery", nominal=True), self.capacity("mill", nominal=True)) * 6
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
        from commissions import post_extended_offers
        post_extended_offers(self)
        self.journal = self.journal[:8]

    def _resolve_deadlines(self) -> None:
        for key, offer in self.offers.items():
            if offer["status"] not in ("open", "bid") or self.day <= offer["due_day"]:
                continue
            if offer["status"] == "bid":
                if offer.get("missed_deadline"):
                    continue
                offer["missed_deadline"] = True
                event = f"Day {self.day}: {key.title()} missed its deadline; the owner chose to wait for Grace."
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
                    self.last_contract_event = f"Day {self.day}: {firm['name']} could not afford Grace; expansion postponed."
                    self.journal.insert(0, self.last_contract_event)
                    continue
                if machine not in firm["machines"]:
                    firm["machines"].append(machine)
                    firm["cash"] -= reward
                    self.rival_cash += reward
                    self._record_trade("Grace", firm["name"], "machine", 1, reward, contract=key)
                setattr(self, f"{key}_machine", True)
                offer["status"] = "rival"
                offer["design_owner"] = "Grace"
                offer["copy_owner"] = firm["owner"]
                offer["delivery_mode"] = "sell"
                self.last_contract_event = f"Day {self.day}: Grace installed the {key} machine for {reward} coins."
                self.journal.insert(0, self.last_contract_event)
                self._post_offers()
        if self.day < self.rival_busy_until:
            return
        for key, offer in self.offers.items():
            if offer["status"] == "open" and self.day - offer["posted_day"] >= 3:
                offer['inventor_id'] = 'grace'
                offer["status"] = "bid"
                offer["finish_day"] = self.day + 2
                self.rival_busy_until = offer["finish_day"]
                self.last_contract_event = f"Day {self.day}: Grace bid on the {key} job; delivery day {offer['finish_day']}."
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
        self._record_trade("Copperside Market", "Boole", "bread", 1, self.bread_price)
        return f"Bought one loaf. Your pantry holds {self.player_bread} bread."

    def _record_trade(self, seller, buyer, good, units, coins, **details):
        entry = {"from": seller, "to": buyer, "good": good, "units": units, "coins": coins, **details}
        self.daily_trades.append(entry)
        if self.trade_history and self.trade_history[-1]["day"] == self.day:
            self.trade_history[-1]["entries"].append(entry.copy())

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
        if self.service_active:
            self.service_open_day = self.day
        return "Workshop service opened for daily customers." if self.service_active else "Workshop service paused."

    def talk_to(self, name: str, topic: str) -> None:
        person = next((p for p in self.citizens if p["name"] == name), None)
        if person is None or topic not in ("work", "family", "town", "hopes"):
            return
        if person.get("conversation_day") != self.day:
            person["conversation_day"] = self.day
            person["conversation_topics"] = []
        if topic in person["conversation_topics"]:
            return
        person["conversation_topics"].append(topic)
        person["last_talk_day"] = self.day
        person["relationships"]["Boole"] = min(100, person["relationships"].get("Boole", 20) + 2)
        person["memories"].append(f"Day {self.day}: spoke with you about {topic}.")
        person["memories"] = person["memories"][-6:]

    def operating_reserve(self, firm):
        """Keep operating cash and the next planned controller affordable."""
        planned = [reward + 16 for business_id, machine, reward in CONTRACTS.values()
                   if self.businesses[business_id] is firm and machine not in firm["machines"]]
        return max([48] + planned)

    def _run_service(self) -> None:
        if not self.service_active or self.day <= self.service_open_day or self.service_paid_day == self.day:
            return
        fuel = self.businesses["fuel_yard"]
        parts = self.businesses["parts_shop"]
        customers = [self.businesses[business_id] for key, (business_id, _, _) in CONTRACTS.items()
                     if self.offers.get(key, {}).get("status") == "player"]
        # Maintenance is optional: share appointments and retain operating
        # funds instead of repeatedly draining the first customer to zero.
        customers = list({id(firm): firm for firm in customers}.values())
        customers.sort(key=lambda firm: firm.get("last_service_day", 0))
        customer = next((firm for firm in customers if firm["cash"] >= self.operating_reserve(firm) + 8), None)
        if customer is None or fuel["stock"].get("fuel", 0) < 1 or parts["stock"].get("parts", 0) < 1:
            self.journal.insert(0, f"Day {self.day}: workshop service had no funded customer or lacked fuel/parts.")
            return
        if self.coins < 6:
            self.journal.insert(0, f"Day {self.day}: workshop service needed 6 coins for fuel and parts.")
            return
        fuel["stock"]["fuel"] -= 1
        fuel["cash"] += 3
        self._record_trade(fuel["name"], "Your Workshop", "fuel", 1, 3)
        parts["stock"]["parts"] -= 1
        parts["cash"] += 3
        self._record_trade(parts["name"], "Your Workshop", "parts", 1, 3)
        customer["cash"] -= 8
        customer["last_service_day"] = self.day
        self.coins += 2
        self._record_trade("Your Workshop", customer["name"], "service", 1, 8)
        self.service_customer = next(key for key, firm in self.businesses.items() if firm is customer)
        self.service_paid_day = self.day
        self.service_earned += 2
        self.service_days += 1
        self.journal.insert(0, f"Day {self.day}: serviced {customer['name']} (+1 capacity); earned 2c net.")

    def capacity(self, business_id: str, *, nominal=False) -> int:
        firm = self.businesses[business_id]
        if firm.get('operating_state') == 'paused' and not nominal:
            return 0
        recipe = BUSINESS_TYPES[firm["kind"]]
        machine_bonus = sum(MACHINE_EFFECTS.get(machine, {}).get("capacity", 0)
                            for machine in firm["machines"] if nominal or self.machine_ready(business_id, machine))
        service_bonus = int(self.service_paid_day == self.day and self.service_customer == business_id)
        planning_bonus = int(firm.get("compute_day") in (self.day, self.day - 1))
        from manufacturing import capacity_bonus
        factory_bonus = capacity_bonus(self, business_id)
        worker_limit = 8 if firm["kind"] == "fuel" else 6
        if firm.get("owner_operated"):
            return max(0, firm.get("capacity_override", recipe["capacity"]) + factory_bonus)
        return max(0, min(recipe["capacity"] + machine_bonus + service_bonus + planning_bonus + factory_bonus, firm["workers"] * worker_limit))

    def stock_buffer_bonus(self, business_id):
        firm = self.businesses[business_id]
        return min(2, sum(MACHINE_EFFECTS.get(machine, {}).get("buffer", 0)
                          for machine in firm["machines"] if self.machine_active(machine)))

    def _supply_steam(self, firm: dict) -> None:
        if not any(self.machine_active(machine) and not MACHINE_EFFECTS.get(machine, {}).get("passive")
                   for machine in firm["machines"]):
            return
        fuel = self.businesses["fuel_yard"]
        if fuel is firm:
            return
        if fuel["stock"].get("fuel", 0) < 1 or firm["cash"] < 2:
            event = f"Day {self.day}: {firm['name']} lacked fuel; its steam machine paused."
            if firm.get("fuel_shortage_noted_day") != self.day:
                self.journal.insert(0, event)
                firm["fuel_shortage_noted_day"] = self.day
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
                and (MACHINE_EFFECTS.get(machine, {}).get("passive") or
                     self.power_checked_day != self.day or firm.get("powered_day") == self.day))

    def _pay_royalties(self) -> None:
        for key, license_info in self.licenses.items():
            if license_info.get("paid_day") == self.day:
                continue
            firm = self.businesses[CONTRACTS[key][0]]
            if firm["cash"] >= self.operating_reserve(firm) + LICENSE_RATE:
                firm["cash"] -= LICENSE_RATE
                self.coins += LICENSE_RATE
                self._record_trade("Boole", firm["name"], "license", 1, LICENSE_RATE, contract=key)
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
        from commissions import COMMISSIONS
        prerequisite = COMMISSIONS[key].prerequisite
        if prerequisite and self.offers.get(prerequisite, {}).get("status") not in ("player", "rival"):
            return False
        payout = (reward if mode == "install" else
                  reward + max(6, reward // 3) if mode == "sell" else reward // 2)
        if firm["cash"] < payout:
            return False
        firm["machines"].append(machine)
        firm["cash"] -= payout
        self.coins += payout
        self._record_trade("Boole", firm["name"], "machine", 1, payout, contract=key, mode=mode)
        setattr(self, f"{key}_machine", True)
        offer["status"] = "player"
        offer["design_owner"] = "Boole"
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

    def complete_pump_job(self, mode: str = "install") -> bool:
        return self.fulfill_job("pump", mode)

    def complete_sorter_job(self, mode: str = "install") -> bool:
        return self.fulfill_job("sorter", mode)

    def _buy_input(self, buyer: dict, good: str, needed: int, unit_price: int) -> int:
        if "east_bakery" in self.businesses:
            from competition import buy_competitive_input
            return buy_competitive_input(self, buyer, good, needed, unit_price)
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
        self._record_trade(firm["name"], "Traveling Mechanic", "parts", 1, 8, external=True)

    def _sell_surplus_fuel(self) -> None:
        """One regional fuel order; village steam and repair work have priority."""
        if self.day < 7:
            return
        firm = self.businesses["fuel_yard"]
        if firm["stock"].get("fuel", 0) <= 6:
            return
        firm["stock"]["fuel"] -= 1
        firm["cash"] += 3
        self._record_trade(firm["name"], "Regional Fuel Cart", "fuel", 1, 3,
                           external=True, purpose="Surplus after six local fuel reserves")

    def _review_working_capital(self) -> None:
        """A finite inter-business credit line can restart a stalled old save.

        No money is created: established firms lend spare retained cash, and
        each distressed food producer can take this startup advance only once.
        Repayment waits until the borrower has a useful operating reserve.
        """
        for firm in self.businesses.values():
            credit = firm.get("working_credit")
            if not credit or credit.get("repaid_day") == self.day:
                continue
            creditor = self.businesses.get(credit["lender"])
            if not creditor:
                continue
            repayment = min(4, credit["owed"], max(0, firm["cash"] - 64))
            if repayment:
                firm["cash"] -= repayment
                creditor["cash"] += repayment
                credit["owed"] -= repayment
                credit["repaid_day"] = self.day
                self._record_trade(creditor["name"], firm["name"], "credit repayment", 1, repayment)
        distressed = [key for key in ("farm", "mill", "bakery", "market")
                      if self.businesses[key]["cash"] < 12 and not self.businesses[key].get("working_credit")]
        if len(distressed) < 2:
            return
        for key in distressed:
            borrower = self.businesses[key]
            lenders = [(name, firm) for name, firm in self.businesses.items()
                       if name != key and not firm.get("opened_day") and firm["cash"] >= 156]
            if not lenders:
                break
            name, lender = max(lenders, key=lambda pair: pair[1]["cash"])
            lender["cash"] -= 36
            borrower["cash"] += 36
            borrower["working_credit"] = {"lender": name, "owed": 36, "issued_day": self.day}
            self._record_trade(lender["name"], borrower["name"], "working capital advance", 1, 36,
                               purpose="Repay from cash above 64c; one startup advance per firm")
            self.journal.insert(0, f"Day {self.day}: {lender['name']} lent {borrower['name']} 36c to restart trading.")

    def _sell_regional_kits(self) -> None:
        """Controller-backed standing orders turn real local stock into kits.

        Owners prepare initial orders; a resident hired for the packing bench
        must actually finish their shift before that day's order can leave.
        """
        from daily_life import SHIFT_SECONDS
        orders = (("parts_selector", "sawmill", "timber", 4, 10, "timber packing kit"),
                  ("parts_priority", "foundry", "metal", 3, 12, "precision metal kit"))
        for key, shop, good, reserve, price, product in orders:
            if self.offers.get(key, {}).get("status") not in ("player", "rival"):
                continue
            firm = self.businesses[shop]
            if firm["stock"].get(good, 0) <= reserve or firm.get("regional_order_day") == self.day:
                continue
            staff = [person for person in self.citizens if person["workplace"] == shop]
            if firm.get("workers", 0) > 0 and (not staff or
                    max(self.daily_life.get("worked", {}).get(p["name"], 0) for p in staff) < SHIFT_SECONDS):
                continue
            firm["stock"][good] -= 1
            firm["cash"] += price
            firm["regional_order_day"] = self.day
            self._record_trade(firm["name"], "Regional Workshops", product, 1, price,
                               external=True, materials={good: 1}, purpose="Prepared order; local reserve protected")

    def update_life(self, town, dt):
        from daily_life import update
        update(self, town, dt)

    def record_visit(self, person, dt):
        from daily_life import record_visit
        record_visit(self, person, dt)

    def advance_day(self, town=None) -> None:
        from daily_life import advance
        advance(self, town)
