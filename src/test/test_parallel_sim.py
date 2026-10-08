# -*- coding:utf-8 -*-
# Author:银河远征(Agent supported)
# env:py38
"""模拟并行化：分片调度、增量合并、WebUI 统计与设置。"""

import copy
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml

from src.utils.loadConfig import load_config, load_yaml
from src.utils.loadDataset import Dataset
from src.utils.runUtil import resolve_workers, split_epochs
from src.webui import service
from src.webui.service import (
    DEFAULT_SIMULATION_WORKERS,
    MapSimulationManager,
    SimulationManager,
    WebUIService,
    load_simulation_workers,
    normalise_simulation_workers,
    read_user_settings,
    write_user_settings,
)
from src.wsgr.wsgrTimer import timer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = str(PROJECT_ROOT / "depend" / "map")


class WorkerResolutionTest(unittest.TestCase):
    def test_threshold_keeps_small_runs_serial(self):
        self.assertEqual(resolve_workers(8, 999), 1)
        self.assertEqual(resolve_workers(1, 100000), 1)

    def test_worker_count_is_capped(self):
        self.assertEqual(resolve_workers(4, 1200), 4)
        self.assertLessEqual(resolve_workers(64, 100000), os.cpu_count() or 1)

    def test_split_covers_every_epoch(self):
        self.assertEqual(split_epochs(1000, 4), [(0, 250), (250, 250), (500, 250), (750, 250)])
        self.assertEqual(split_epochs(1003, 4), [(0, 251), (251, 251), (502, 251), (753, 250)])
        self.assertEqual(sum(count for _, count in split_epochs(97, 5)), 97)


class SimulationSettingsTest(unittest.TestCase):
    def test_normalise_bounds(self):
        self.assertEqual(normalise_simulation_workers(None), DEFAULT_SIMULATION_WORKERS)
        self.assertEqual(normalise_simulation_workers("6"), 6)
        for bad in (0, 33, "abc"):
            with self.assertRaises(ValueError):
                normalise_simulation_workers(bad)

    def test_simulation_workers_read_from_user_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_settings.yaml"
            original = service.user_settings_file
            service.user_settings_file = str(path)
            try:
                self.assertEqual(load_simulation_workers(), DEFAULT_SIMULATION_WORKERS)
                write_user_settings({"recon": None, "simulation": {"workers": 7}})
                self.assertEqual(load_simulation_workers(), 7)
                self.assertIn("recon", read_user_settings())
                write_user_settings({"simulation": {"workers": 99}})
                self.assertEqual(load_simulation_workers(), DEFAULT_SIMULATION_WORKERS)
                path.write_text("不是对象", encoding="utf-8")
                self.assertEqual(load_simulation_workers(), DEFAULT_SIMULATION_WORKERS)
            finally:
                service.user_settings_file = original

    def test_simulation_and_environment_share_one_file(self):
        service_instance = WebUIService()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_settings.yaml"
            original_settings = service.user_settings_file
            original_root = service.PROJECT_ROOT
            service.user_settings_file = str(path)
            service.PROJECT_ROOT = Path(directory)
            try:
                # 全局增益设定不再包含模拟设置，两者是独立入口
                environment_payload = service_instance.environment_settings()
                self.assertNotIn("simulation", environment_payload["settings"])
                self.assertEqual(
                    service_instance.simulation_settings()["settings"]["workers"],
                    DEFAULT_SIMULATION_WORKERS,
                )

                # 保存模拟设置：写在文件最前
                saved = service_instance.update_simulation_settings({"workers": 6})
                self.assertEqual(saved["settings"]["workers"], 6)
                self.assertTrue(saved["path"].endswith("user_settings.yaml"))
                stored = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertEqual(list(stored)[0], "simulation")
                self.assertEqual(stored["simulation"]["workers"], 6)

                # 保存全局增益不会动 simulation，且仍排在最前
                settings = copy.deepcopy(environment_payload["settings"])
                service_instance.update_environment_settings(settings)
                stored = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIn("recon", stored)
                self.assertIn("car", stored)
                self.assertEqual(list(stored)[0], "simulation")
                self.assertEqual(stored["simulation"]["workers"], 6)

                # 反过来先存模拟设置再存环境设置，两边同样互不覆盖
                service_instance.update_environment_settings(settings)
                service_instance.update_simulation_settings({"workers": 7})
                stored = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIn("recon", stored)
                self.assertEqual(stored["simulation"]["workers"], 7)
                self.assertEqual(list(stored)[0], "simulation")

                # 非法并行度被拒绝
                with self.assertRaises(ValueError):
                    service_instance.update_simulation_settings({"workers": 99})
            finally:
                service.user_settings_file = original_settings
                service.PROJECT_ROOT = original_root


class ParallelSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = Dataset(str(PROJECT_ROOT / "depend" / "ship" / "database.xlsx"))
        with (PROJECT_ROOT / "config" / "config_test.yaml").open(encoding="utf-8") as file:
            cls.battle_config = yaml.safe_load(file)
        cls.battle = load_config(
            cls.battle_config, MAP_DIR, cls.dataset, timer(), log_func=lambda _: None,
        )
        cls.friend_names = [ship.status["name"] for ship in cls.battle.friend.ship]
        cls.enemy_names = [ship.status["name"] for ship in cls.battle.enemy.ship]

    def _manager(self):
        return SimulationManager(self.dataset)

    def test_parallel_merge_matches_serial_shape(self):
        manager = self._manager()
        prebattle = manager._prebattle_info(self.battle)
        epoch = 600
        serial_done, serial_state = manager._run_serial_epochs(
            self.battle, epoch, epoch, "", self.friend_names, self.enemy_names, prebattle,
        )
        parallel_done, parallel_state = manager._run_parallel_epochs(
            self.battle_config, epoch, 1, 4, epoch // 4, "",
            self.friend_names, self.enemy_names, prebattle,
        )

        self.assertEqual(serial_done, epoch)
        self.assertEqual(parallel_done, epoch)
        self.assertEqual(sum(parallel_state["result_counts"].values()), epoch)
        self.assertEqual(len(parallel_state["damage_samples"]), epoch)
        self.assertEqual(
            parallel_state["ship_damage_phase_totals"].shape,
            serial_state["ship_damage_phase_totals"].shape,
        )
        self.assertTrue(parallel_state["battle_detail"])
        # 统计量在容差内一致（随机种子不固定，只看量级）
        serial_mean = np.mean(serial_state["damage_samples"])
        parallel_mean = np.mean(parallel_state["damage_samples"])
        self.assertLess(abs(parallel_mean - serial_mean) / serial_mean, 0.15)

    def test_empty_epoch_plan_does_not_create_processes(self):
        plan = split_epochs(10, 4)
        self.assertEqual(sum(count for _, count in plan), 10)
        self.assertTrue(all(count > 0 for _, count in plan))


if __name__ == "__main__":
    unittest.main()
