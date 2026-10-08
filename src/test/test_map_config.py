# -*- coding:utf-8 -*-
# Author:银河远征(Agent supported)
# env:py38

import copy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import yaml

from src.utils import battleUtil
from src.utils.battleUtil import BattleUtil
from src.utils.loadConfig import load_config, load_yaml
from src.utils.loadDataset import Dataset
from src.utils.mapUtil import DefaultUserRules, Point, UserRules
from src.skillCode.MapEnv import load_map_effect, map_effect_options
from src.webui.service import (
    MapSimulationManager,
    _accumulate_map_epoch,
    _merge_map_delta,
    _new_map_state,
    calculate_map_enemy_fleet_summary,
)
import src.wsgr.ship as rship
from src.wsgr.wsgrTimer import timer as BattleTimer
from src.wsgr.wsgrTimer import timer


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MapBattleConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = Dataset(str(PROJECT_ROOT / "depend" / "ship" / "database.xlsx"))
        with (PROJECT_ROOT / "config" / "config_map_test.yaml").open(
            encoding="utf-8"
        ) as file:
            cls.config = yaml.safe_load(file)

    def test_complete_map_battle_runs_from_config(self):
        loaded = load_yaml(
            str(PROJECT_ROOT / "config" / "config_map_test.yaml"),
            str(PROJECT_ROOT / "depend" / "map"),
        )
        self.assertEqual(loaded["map"], {"mapid": "normal/2-1"})
        config = copy.deepcopy(self.config)
        config.pop("user_rules", None)
        battle_map = load_config(
            config,
            str(PROJECT_ROOT / "depend" / "map"),
            self.dataset,
            timer(),
            log_func=lambda _: None,
        )
        battle_map.start()
        report = battle_map.report()

        self.assertEqual(report["map_path"][0], "入口")
        self.assertEqual(report["map_path"][-1], "F")
        self.assertGreaterEqual(report["map_battle_count"], 2)
        self.assertTrue(report["map_node_events"])
        self.assertIn("recon_rate", report["map_node_events"][0])
        self.assertTrue(report["end_with_boss"])

    def test_top_level_user_rules_stop_at_an_unselected_node(self):
        config = copy.deepcopy(self.config)
        config.pop("user_rules", None)
        config.update({
            "selected_nodes": ["入口"],
            "node_defaults": {"formation": 2},
        })
        battle_map = load_config(
            config,
            str(PROJECT_ROOT / "depend" / "map"),
            self.dataset,
            timer(),
            log_func=lambda _: None,
        )

        battle_map.start()
        report = battle_map.report()

        self.assertEqual(report["map_path"][0], "入口")
        self.assertEqual(len(report["map_path"]), 2)
        self.assertEqual(report["end_with"], report["map_path"][-1])
        self.assertEqual(report["map_battle_count"], 0)

    def test_resource_points_adjust_map_supply_without_creating_battles(self):
        map_document = {
            "mapid": "resource-point-test",
            "nodes": [
                {
                    "name": "入口", "kind": "entrance", "level": 0,
                    "battle": {"type": "Entrance", "roundabout": False, "support": False},
                    "enemy_fleets": [],
                },
                {
                    "name": "补给", "kind": "resource_gain", "level": 1,
                    "battle": {
                        "type": "ResourcePoint", "resource": "oil", "amount": 120,
                        "roundabout": False, "support": False,
                    },
                    "enemy_fleets": [],
                },
                {
                    "name": "损耗", "kind": "resource_loss", "level": 4,
                    "battle": {
                        "type": "ResourcePoint", "resource": "oil", "amount": 35,
                        "roundabout": False, "support": False,
                    },
                    "enemy_fleets": [],
                },
            ],
            "routes": [
                {"from": "入口", "to": "补给", "weight": 1, "relation": "all", "conditions": []},
                {"from": "补给", "to": "损耗", "weight": 1, "relation": "all", "conditions": []},
            ],
        }
        config = {
            "battle_type": "Map",
            "friend_fleet": copy.deepcopy(self.config["friend_fleet"]),
            "map": {"mapid": "resource-point-test"},
            "_map_document": map_document,
        }
        battle_map = load_config(
            config, str(PROJECT_ROOT / "depend" / "map"), self.dataset,
            timer(), log_func=lambda _: None,
        )

        battle_map.start()
        report = battle_map.report()

        self.assertEqual(report["map_path"], ["入口", "补给", "损耗"])
        self.assertEqual(report["map_battle_count"], 0)
        self.assertEqual(report["supply"]["oil"], -85)


class MapUserRulesTest(unittest.TestCase):
    def setUp(self):
        self.point = Point('A', 2)
        self.point.set_type(battleUtil.NormalBattle)
        self.point.set_roundabout(True)

    @staticmethod
    def _fleet(*ship_types):
        ships = [ship_type.__new__(ship_type) for ship_type in ship_types]
        return SimpleNamespace(ship=ships)

    def test_node_arguments_override_defaults_and_first_rule_wins(self):
        rules = UserRules({
            'selected_nodes': ['A'],
            'node_defaults': {
                'formation': 3,
                'long_missile': True,
                'round': False,
                'proceed_stop': [1, 2, 2, 2, 2, 2],
                'rules': [
                    ['(SS >= 2) or (DD >= 3) and (CL >= 1)', '5'],
                    ['(SS >= 2)', 'retreat'],
                ],
            },
            'node_args': {'A': {'night': 'flag_alive', 'long_missile': False}},
        }, ['A'])
        self.point.set_user_rules(rules)
        self.point.round_request = rules.settings_for(self.point)['round']
        friend = self._fleet()
        friend.set_form = lambda value: setattr(friend, 'formation', value)
        enemy = self._fleet(rship.SS, rship.SS)
        enemy.ship[0].damaged = 0
        battle_timer = SimpleNamespace(recon_flag=True, map_retreat=False, info=lambda _: None)

        rules.select_initial_formation(self.point, friend)
        rules.apply_recon_decision(self.point, friend, enemy, battle_timer)

        self.assertEqual(friend.formation, 5)
        self.assertFalse(battle_timer.map_retreat)
        self.assertTrue(rules.should_run_night(self.point, enemy))
        self.assertFalse(rules.should_run_long_missile(self.point))
        self.assertEqual(rules.settings_for(self.point)['proceed_stop'][0], 1)

    def test_recon_and_damage_retreat_decisions(self):
        rules = UserRules({
            'selected_nodes': 'all',
            'node_defaults': {
                'formation_if_recon_fails': 4,
                'retreat_if_recon_fails': True,
                'proceed_stop': [1, -1, -1, -1, -1, -1],
            },
        }, ['A'])
        self.point.set_user_rules(rules)
        friend = self._fleet(rship.SS)
        friend.set_form = lambda value: setattr(friend, 'formation', value)
        friend.ship[0].loc = 1
        friend.ship[0].damaged = 2
        battle_timer = SimpleNamespace(recon_flag=False, map_retreat=False, info=lambda _: None)

        rules.apply_recon_decision(self.point, friend, self._fleet(), battle_timer)

        self.assertEqual(friend.formation, 4)
        self.assertTrue(battle_timer.map_retreat)
        self.assertFalse(rules.should_proceed(self.point, friend))

    def test_default_rules_preserve_the_legacy_formation_and_flagship_guard(self):
        rules = DefaultUserRules(['A'])
        self.point.set_user_rules(rules)
        friend = self._fleet(rship.SS, rship.DD)
        friend.set_form = lambda value: setattr(friend, 'formation', value)
        friend.ship[0].loc, friend.ship[0].damaged = 1, 0
        friend.ship[1].loc, friend.ship[1].damaged = 2, 3

        rules.select_initial_formation(self.point, friend)

        self.assertEqual(friend.formation, 2)
        self.assertTrue(rules.should_proceed(self.point, friend))
        self.assertTrue(rules.should_run_long_missile(self.point))

    def test_non_map_battle_always_keeps_long_missile_phase(self):
        battle = BattleUtil(BattleTimer(), None, None)

        self.assertTrue(battle.should_run_long_missile())


class MapEffectTest(unittest.TestCase):
    def test_map_effect_registry_exposes_module_name_and_label(self):
        self.assertIn(
            {
                "id": "map090102",
                "name": "9图封锁战况(削弱后)",
                "effect": "敌方舰队旗舰存活时，为所有非旗舰单位提供10%减伤",
            },
            map_effect_options(),
        )

    def test_point_effect_is_added_once_and_persists_on_timer(self):
        point = Point('A', 2)
        point.add_map_effect(
            'map090102', '9图封锁战况(削弱后)',
            load_map_effect('map090102')[1],
        )
        battle_timer = BattleTimer()

        point.apply_map_effects(battle_timer)
        point.apply_map_effects(battle_timer)

        self.assertEqual(len(battle_timer.env_skill), 1)
        self.assertEqual(battle_timer.map_env_effect_ids, {'map090102'})
        self.assertIn('【地图效果】9图封锁战况(削弱后)', battle_timer.log['record'])

    def test_unknown_map_effect_node_is_rejected(self):
        map_document = {
            "mapid": "invalid-buffs",
            "nodes": [
                {"name": "入口", "kind": "entrance", "level": 0,
                 "battle": {"type": "Entrance"}, "enemy_fleets": []},
            ],
            "routes": [],
            "buffs": {"不存在": ["map090102"]},
        }
        with self.assertRaisesRegex(ValueError, 'Unknown map buff node'):
            from src.utils.mapUtil import MapUtil
            MapUtil(BattleTimer(), map_document, None, SimpleNamespace(ship=[]), log_func=lambda _: None)

    def test_map_effect_yaml_binds_the_effect_to_its_node(self):
        map_document = {
            "mapid": "map-effects",
            "nodes": [
                {"name": "入口", "kind": "entrance", "level": 0,
                 "battle": {"type": "Entrance"}, "enemy_fleets": []},
                {"name": "终点", "kind": "no_battle", "level": 4,
                 "battle": {"type": "MidPoint"}, "enemy_fleets": []},
            ],
            "routes": [{"from": "入口", "to": "终点", "weight": 1}],
            "buffs": {"终点": "map090102"},
        }
        from src.utils.mapUtil import MapUtil
        battle_map = MapUtil(
            BattleTimer(), map_document, None, SimpleNamespace(ship=[]),
            log_func=lambda _: None,
        )

        self.assertEqual(battle_map.point['终点'].map_effects[0][0], 'map090102')


class MapResultStatisticsTest(unittest.TestCase):
    @staticmethod
    def _statistics(visits, battles):
        return {
            "visits": visits,
            "battles": battles,
            "result_counts": {
                "SS": battles, "S": 0, "A": 0, "B": 0, "C": 0, "D": 0,
            },
            "mid_damage": battles,
            "heavy_damage": 0,
            "mid_damage_by_ship": np.array([battles], dtype=float),
            "heavy_damage_by_ship": np.array([0], dtype=float),
            "recon_rate_total": 80.0 * visits,
            "recon_rate_count": visits,
            "roundabout_rate_total": 60.0 * visits,
            "roundabout_rate_count": visits,
        }

    def test_visits_and_battles_use_separate_denominators(self):
        summary = MapSimulationManager._build_map_summary(
            completed=10,
            boss_battles=0,
            boss_flagship_sinks=0,
            node_statistics={"A": self._statistics(visits=5, battles=2)},
            friend_ship_names=["测试舰"],
            supply_totals={
                "oil": 0, "ammo": 0, "steel": 0, "almn": 0, "repeat": 0,
            },
            first_record="",
        )
        statistics = summary["node_statistics"][0]

        self.assertEqual(statistics["visits"], 5)
        self.assertEqual(statistics["battles"], 2)
        self.assertEqual(statistics["roundabout_rate"], 60.0)
        self.assertEqual(statistics["result_rates"]["SS"], 100.0)
        self.assertEqual(statistics["mid_damage_rate"], 100.0)

    def test_battle_statistics_are_empty_when_every_visit_roundabouts(self):
        summary = MapSimulationManager._build_map_summary(
            completed=10,
            boss_battles=0,
            boss_flagship_sinks=0,
            node_statistics={"A": self._statistics(visits=5, battles=0)},
            friend_ship_names=["测试舰"],
            supply_totals={
                "oil": 0, "ammo": 0, "steel": 0, "almn": 0, "repeat": 0,
            },
            first_record="",
        )
        statistics = summary["node_statistics"][0]

        self.assertEqual(statistics["visits"], 5)
        self.assertEqual(statistics["roundabout_rate"], 60.0)
        self.assertIsNone(statistics["result_rates"]["SS"])
        self.assertIsNone(statistics["mid_damage_rate"])
        self.assertEqual(statistics["mid_damage_ship_rates"], [None])

    def test_multiple_bosses_keep_independent_history_statistics(self):
        supply_keys = ("oil", "ammo", "steel", "almn", "repeat", "dcitem")
        boss_statistics = {
            "B1": {
                "simulations": 4,
                "result_counts": {
                    "SS": 2, "S": 1, "A": 1, "B": 0, "C": 0, "D": 0,
                },
                "flagship_sinks": 3,
                "supply_totals": {
                    "oil": 40, "ammo": 32, "steel": 8, "almn": 4,
                    "repeat": 2, "dcitem": 1,
                },
            },
            "B2": {
                "simulations": 2,
                "result_counts": {
                    "SS": 0, "S": 1, "A": 0, "B": 0, "C": 0, "D": 1,
                },
                "flagship_sinks": 1,
                "supply_totals": {
                    "oil": 24, "ammo": 20, "steel": 4, "almn": 2,
                    "repeat": 2, "dcitem": 2,
                },
            },
        }
        node_statistics = {
            "B1": self._statistics(visits=4, battles=4),
            "B2": self._statistics(visits=2, battles=2),
        }
        node_statistics["B1"]["mid_damage_by_ship"] = np.array([2], dtype=float)
        node_statistics["B1"]["heavy_damage_by_ship"] = np.array([1], dtype=float)
        node_statistics["B2"]["mid_damage_by_ship"] = np.array([1], dtype=float)
        node_statistics["B2"]["heavy_damage_by_ship"] = np.array([1], dtype=float)
        summary = MapSimulationManager._build_map_summary(
            completed=10,
            boss_battles=6,
            boss_flagship_sinks=4,
            node_statistics=node_statistics,
            friend_ship_names=["测试舰"],
            supply_totals={key: 0 for key in supply_keys},
            first_record="",
            boss_statistics=boss_statistics,
            boss_result_counts={"SS": 3, "S": 2, "A": 1, "B": 0, "C": 0, "D": 0},
            boss_end_counts={"B1": 4, "B2": 2},
        )
        bosses = {entry["name"]: entry for entry in summary["boss_statistics"]}

        # Boss 综合胜率按「Boss 战斗场次」聚合：5/6
        self.assertAlmostEqual(summary["boss_win_rate"], 500 / 6)
        # Boss 旗舰击沉率按「Boss 战斗场次」：4/6
        self.assertAlmostEqual(summary["boss_flagship_sink_rate"], 400 / 6)
        # 完成率 = 各 Boss 终点局数之和 / 总局数：(4 + 2) / 10
        self.assertEqual(summary["completion_rate"], 60.0)
        # 旧的「到终点且击沉旗舰」口径已移除
        self.assertNotIn("clear_rate", summary)

        self.assertEqual(bosses["B1"]["simulations"], 4)
        self.assertEqual(bosses["B1"]["clear_rate"], 75.0)
        self.assertEqual(bosses["B1"]["flagship_sink_rate"], 75.0)
        self.assertEqual(bosses["B1"]["completion_rate"], 40.0)
        self.assertEqual(bosses["B1"]["result_rates"]["SS"], 50.0)
        self.assertEqual(bosses["B1"]["average_bucket"], 0.5)
        self.assertEqual(bosses["B1"]["average_dcitem"], 0.25)
        self.assertEqual(bosses["B1"]["friend_mid_damage_rates"], [50.0])
        self.assertEqual(bosses["B1"]["friend_heavy_damage_rates"], [25.0])
        self.assertEqual(bosses["B2"]["clear_rate"], 50.0)
        self.assertEqual(bosses["B2"]["completion_rate"], 20.0)
        self.assertEqual(bosses["B2"]["average_dcitem"], 1.0)
        self.assertEqual(bosses["B2"]["friend_mid_damage_rates"], [50.0])
        self.assertEqual(bosses["B2"]["friend_heavy_damage_rates"], [50.0])


class MapCaliberAccumulationTest(unittest.TestCase):
    """完成率 / Boss 综合胜率 / 旗舰击沉率的累加口径。"""

    NODES = ["入口", "道中", "B1", "B2"]
    BOSSES = ["B1", "B2"]
    SHIPS = ["舰1"]

    @staticmethod
    def _battle(name, result, boss=False, sunk=False):
        return {
            "name": name,
            "result": result,
            "boss": boss,
            "boss_flagship_sunk": sunk,
            "friend_damaged_state": [],
        }

    @classmethod
    def _report(cls, ending, battles, *, end_with_boss=False, oil=10, dcitem=0):
        return {
            "end_with": ending,
            "end_with_boss": end_with_boss,
            "map_battles": battles,
            "supply": {"oil": oil, "ammo": 8, "steel": 2, "almn": 4, "repeat": 1},
            "dcitem": dcitem,
            "record": f"{ending}-record",
        }

    def _collect(self):
        state = _new_map_state(self.NODES, self.BOSSES, self.SHIPS)
        reports = [
            # 打到终点 B1，SS 且击沉旗舰
            self._report(
                "B1",
                [self._battle("道中", "A"), self._battle("B1", "SS", boss=True, sunk=True)],
                end_with_boss=True, oil=12, dcitem=1,
            ),
            # 打到终点 B1，S 但未击沉旗舰：计入完成率，不计入旗舰击沉
            self._report(
                "B1",
                [self._battle("B1", "S", boss=True, sunk=False)],
                end_with_boss=True, oil=10,
            ),
            # 道中结束，未到终点
            self._report("道中", [self._battle("道中", "D")], oil=4),
            # 以 B2 结束但不是 Boss 终点（策略撤退未开打）：不计入任何完成率
            self._report("B2", [], oil=2),
        ]
        for report in reports:
            _accumulate_map_epoch(state, report, self.SHIPS)
        return state

    def test_boss_rates_use_boss_battle_denominator(self):
        state = self._collect()

        self.assertEqual(state["boss_battles"], 2)
        self.assertEqual(state["boss_flagship_sinks"], 1)
        self.assertEqual(state["boss_result_counts"]["SS"], 1)
        self.assertEqual(state["boss_result_counts"]["S"], 1)
        self.assertEqual(
            {flag: count for flag, count in state["boss_result_counts"].items() if count},
            {"SS": 1, "S": 1},
        )

        summary = MapSimulationManager._build_map_summary(
            completed=4,
            boss_battles=state["boss_battles"],
            boss_flagship_sinks=state["boss_flagship_sinks"],
            node_statistics=state["node_statistics"],
            friend_ship_names=self.SHIPS,
            supply_totals=state["supply_totals"],
            first_record=state["first_record"],
            boss_statistics=state["boss_statistics"],
            boss_result_counts=state["boss_result_counts"],
            boss_end_counts=state["boss_end_counts"],
        )

        # Boss 综合胜率 = 所有 Boss 点 SS+S 场次 / Boss 战斗场次
        self.assertEqual(summary["boss_win_rate"], 100.0)
        # Boss 旗舰击沉率 = 旗舰击沉场次 / Boss 战斗场次
        self.assertEqual(summary["boss_flagship_sink_rate"], 50.0)
        # 完成率 = 抵达 Boss 终点的局数 / 总局数
        self.assertEqual(state["boss_end_counts"], {"B1": 2, "B2": 0})
        self.assertEqual(summary["completion_rate"], 50.0)

        bosses = {entry["name"]: entry for entry in summary["boss_statistics"]}
        # 以 B1 为终点结束 2 局（2 局都开打），B2 无人以终点结束
        self.assertEqual(bosses["B1"]["simulations"], 2)
        self.assertEqual(bosses["B1"]["clear_rate"], 100.0)
        self.assertEqual(bosses["B1"]["flagship_sink_rate"], 50.0)
        self.assertEqual(bosses["B1"]["completion_rate"], 50.0)
        self.assertEqual(bosses["B2"]["simulations"], 0)
        self.assertEqual(bosses["B2"]["completion_rate"], 0.0)
        # 各 Boss 完成率之和 = 总完成率
        self.assertEqual(
            bosses["B1"]["completion_rate"] + bosses["B2"]["completion_rate"],
            summary["completion_rate"],
        )
        # 资源消耗仍按整局累加
        self.assertEqual(state["supply_totals"]["oil"], 28)
        self.assertEqual(state["supply_totals"]["dcitem"], 1)

    def test_parallel_delta_merge_keeps_new_counters(self):
        target = _new_map_state(self.NODES, self.BOSSES, self.SHIPS)
        _accumulate_map_epoch(
            target,
            self._report(
                "B1",
                [self._battle("B1", "SS", boss=True, sunk=True)],
                end_with_boss=True,
            ),
            self.SHIPS,
        )
        delta = _new_map_state(self.NODES, self.BOSSES, self.SHIPS)
        _accumulate_map_epoch(
            delta,
            self._report(
                "B2",
                [self._battle("B2", "A", boss=True, sunk=False)],
                end_with_boss=True,
            ),
            self.SHIPS,
        )

        _merge_map_delta(target, delta)

        self.assertEqual(target["boss_battles"], 2)
        self.assertEqual(target["boss_flagship_sinks"], 1)
        self.assertEqual(target["boss_result_counts"]["SS"], 1)
        self.assertEqual(target["boss_result_counts"]["A"], 1)
        self.assertEqual(target["boss_end_counts"], {"B1": 1, "B2": 1})


class RoundaboutEndPhaseTest(unittest.TestCase):
    def test_successful_roundabout_skips_every_end_phase_settlement(self):
        battle = BattleUtil.__new__(BattleUtil)
        battle.timer = SimpleNamespace(round_flag=True)
        end_ship = SimpleNamespace(run_end_skill=MagicMock())
        battle.friend = SimpleNamespace(ship=[end_ship])
        battle.enemy = SimpleNamespace(ship=[end_ship])
        battle.supply_cost = MagicMock()

        BattleUtil.end_phase(battle)

        end_ship.run_end_skill.assert_not_called()
        battle.supply_cost.assert_not_called()


class MapEnemyFleetSummaryTest(unittest.TestCase):
    def test_summary_uses_direct_database_formulas(self):
        class PreviewDataset:
            ships = {
                "cv": {
                    "type": "CVL", "speed": 25, "recon": 40, "fire": 20,
                    "load": [10], "equip": ["fighter"],
                },
                "cl": {
                    "type": "CL", "speed": 35, "recon": 10, "fire": 0,
                    "equip": ["radar"],
                },
            }
            equipment = {
                "fighter": {
                    "type": "Fighter", "recon": 2, "fire": 0, "antiair": 5,
                },
                "radar": {
                    "type": "Radar", "recon": 3, "fire": 0,
                },
            }

            def get_enemy_ship_status(self, cid):
                return copy.deepcopy(self.ships[cid])

            def get_equip_status(self, eid):
                return copy.deepcopy(self.equipment[eid])

        summary = calculate_map_enemy_fleet_summary(
            PreviewDataset(),
            {"ships": [{"cid": "cv"}, {"cid": "cl"}]},
        )

        self.assertEqual(summary["recon"], 55.0)
        self.assertEqual(summary["speed"], 25.0)
        self.assertAlmostEqual(summary["aerial"], np.log(16) * 5)


if __name__ == "__main__":
    unittest.main()
