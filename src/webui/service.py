# -*- coding: utf-8 -*-
# Author:银河远征(AI supported)
"""Application service used by the browser WebUI.

The module deliberately contains no HTTP or DOM code.  It adapts the existing
dataset/configuration loaders and battle engine into JSON-friendly metadata and
simulation snapshots.
"""

from __future__ import annotations

import copy
import multiprocessing as mp
from queue import Empty
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from src import skillCode
from src.utils.loadConfig import (
    load_config, load_friend_ship, load_map_yaml, map_yaml_path, load_xml,
    normalize_map_ref,
)
from src.utils.loadDataset import Dataset
from src.utils.runUtil import set_supply, resolve_workers, split_epochs
from src.utils.battleUtil import CustomBattle
from src.utils.envBuffUtil import (
    data_file as environment_data_file,
    environment_options,
    load_user_settings,
    normalise_user_settings,
    reload_env_buffs,
    user_settings_file,
)
from src.skillCode.MapEnv import map_effect_options
from src.wsgr.ship import Fleet, SHIP_LABELS
from src.wsgr.wsgrTimer import PHASE_LABELS, timer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SAVE_DIR = CONFIG_DIR / "save"
DEPEND_DIR = PROJECT_ROOT / "depend"
MAP_DIR = DEPEND_DIR / "map"
DATA_FILE = DEPEND_DIR / "ship" / "database.xlsx"
# 用户设置（环境加成 + 模拟并行度）统一保存在 depend/user_settings.yaml，见 envBuffUtil。
DEFAULT_SIMULATION_WORKERS = 4
MAX_SIMULATION_WORKERS = 32

FORMATIONS = [
    {"id": 1, "name": "单纵"},
    {"id": 2, "name": "复纵"},
    {"id": 3, "name": "轮形"},
    {"id": 4, "name": "梯形"},
    {"id": 5, "name": "单横"},
]

BATTLE_TYPES = [
    {"id": "NormalBattle", "name": "常规战"},
    {"id": "DaytimeBattle", "name": "昼战"},
    {"id": "NightBattle", "name": "夜战"},
    {"id": "AirBattle", "name": "航空战"},
    {"id": "OnlyAirBattle", "name": "仅航空战"},
    {"id": "CustomBattle", "name": "自定义"},
]

STRATEGIES = {
    "attack": {
        "label": "攻击",
        "items": {
            "雷击熟练": "111", "炮击训练": "112", "拦阻射击": "113",
            "效力射": "211", "数据交互": "212", "弹跳攻击": "213",
            "穿甲航弹": "311", "全甲板突击": "312", "穿甲榴弹": "313",
        },
    },
    "defense": {
        "label": "防御",
        "items": {
            "对海警戒哨": "121", "前哨援护": "122", "过穿": "123",
            "硬化装甲": "221", "编队援护": "222", "防空弹幕": "223",
            "探照灯警戒": "321", "护航援护": "322", "装甲甲板": "323",
        },
    },
    "special": {
        "label": "特殊",
        "items": {
            "大角度规避": "131", "雁行雷击": "132", "交互射击": "231",
            "硬被帽": "232", "炮塔后备弹": "233", "改良被帽弹": "331",
            "照明弹校正": "332", "对空预警": "333",
        },
    },
}

RESULT_FLAGS = ("SS", "S", "A", "B", "C", "D")

_SPEED_MAIN_SHIP_TYPES = frozenset({
    "CV", "CVL", "AV", "BB", "BC", "BBV", "BBV0", "ASDG", "AADG", "KP",
    "CG", "BBG", "BG", "CBG", "Elite", "Fortness", "Airfield", "Port",
})
_SPEED_COVER_SHIP_TYPES = frozenset({
    "CAV", "CA", "CL", "CLT", "CLT0", "DD", "BM", "AP", "Tuning",
})
_SPEED_SUBMARINE_TYPES = frozenset({"SS", "SC", "SSG"})
_AIRCRAFT_FLIGHT_PARAMS = {
    "CV": 5,
    "CVL": 5,
    "AV": 5,
    "BBV": 10,
    "BBV0": 10,
    "CAV": 5,
    "Elite": 10,
    "Fortness": 10,
    "Airfield": 10,
    "Tuning": 10,
}
_AERIAL_EQUIPMENT_TYPES = frozenset({"Fighter", "Bomber", "DiveBomber"})


def calculate_map_enemy_fleet_summary(
    dataset: Dataset,
    fleet_config: dict[str, Any],
) -> dict[str, float]:
    """Calculate editor preview values directly from enemy database records."""
    ship_configs = fleet_config.get("ships")
    if not isinstance(ship_configs, list) or not ship_configs:
        return {"recon": 0.0, "aerial": 0.0, "speed": 0.0}

    ships = []
    for ship_config in ship_configs:
        cid = str(ship_config.get("cid", "")).strip()
        if not cid:
            continue
        status = dataset.get_enemy_ship_status(cid)
        equipment = [
            dataset.get_equip_status(eid) if eid else None
            for eid in status.get("equip", [])
        ]
        ships.append((status, equipment))

    if not ships:
        return {"recon": 0.0, "aerial": 0.0, "speed": 0.0}

    recon = sum(
        float(status.get("recon", 0))
        + sum(float(item.get("recon", 0)) for item in equipment if item)
        for status, equipment in ships
    )

    surface_ships = [
        (status, equipment)
        for status, equipment in ships
        if status["type"] not in _SPEED_SUBMARINE_TYPES
    ]
    if surface_ships:
        main_speeds = [
            float(status["speed"])
            for status, _ in surface_ships
            if status["type"] in _SPEED_MAIN_SHIP_TYPES
        ]
        cover_speeds = [
            float(status["speed"])
            for status, _ in surface_ships
            if status["type"] in _SPEED_COVER_SHIP_TYPES
        ]
        if main_speeds and cover_speeds:
            speed = min(np.floor(np.mean(main_speeds)), np.floor(np.mean(cover_speeds)))
        elif main_speeds:
            speed = np.mean(main_speeds)
        elif cover_speeds:
            speed = np.mean(cover_speeds)
        else:
            raise ValueError("敌方舰队不存在可计算航速的水面舰种")
    else:
        speed = np.floor(np.mean([float(status["speed"]) for status, _ in ships]))

    aerial = 0.0
    for status, equipment in ships:
        flight_param = _AIRCRAFT_FLIGHT_PARAMS.get(status["type"])
        if flight_param is None:
            continue
        fire = float(status.get("fire", 0)) + sum(
            float(item.get("fire", 0)) for item in equipment if item
        )
        flight_limit = np.floor(max(fire, 0) / flight_param) + 3
        loads = status.get("load", [])
        for index, item in enumerate(equipment):
            if (
                not item
                or item["type"] not in _AERIAL_EQUIPMENT_TYPES
                or index >= len(loads)
                or loads[index] <= 0
            ):
                continue
            actual_flight = min(float(loads[index]), flight_limit)
            aerial += np.log(2 * (actual_flight + 1)) * float(item.get("antiair", 0))

    return {"recon": float(recon), "aerial": float(aerial), "speed": float(speed)}


def _skill_options(skill_ids: list[str]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = [{"id": 0, "name": "无技能"}]
    for index, sid in enumerate(skill_ids, start=1):
        if not sid:
            continue
        try:
            name = getattr(skillCode, f"sid{sid}").name
        except (AttributeError, ImportError):
            name = f"技能 {sid}"
        options.append({"id": index, "sid": sid, "name": name})
    return options


def _serializable_number(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


class SimulationBusyError(RuntimeError):
    pass


class SimulationManager:
    """Run one simulation job at a time and expose polling-friendly snapshots."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self._simulation_kind = "battle"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._process: mp.Process | None = None
        self._collector_thread: threading.Thread | None = None
        self._state_sink: mp.Queue | None = None
        self._active_job_id = 0
        self._completed = 0
        self._target = 0
        self._stop_requested_completed: int | None = None
        self._state = self._initial_state()

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        return {
            "state": "idle",
            "progress": 0,
            "completed": 0,
            "live_completed": 0,
            "live_progress": 0,
            "stop_requested_completed": None,
            "target": 0,
            "message": "等待开始模拟",
            "log": "等待开始模拟",
            "summary": None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = copy.deepcopy(self._state)
        if state["state"] in ("running", "stopping"):
            state["live_completed"] = self._completed
            state["live_progress"] = self._completed / max(self._target, 1) * 100
        return state

    def reset(self) -> dict[str, Any]:
        """Discard the current job and forget its result snapshot."""
        with self._lock:
            process = self._process
            running = process is not None and process.is_alive()
        if running:
            self.stop()
        with self._lock:
            self._active_job_id += 1
            self._process = None
            self._completed = 0
            self._target = 0
            self._stop_requested_completed = None
            self._state = self._initial_state()
            return copy.deepcopy(self._state)

    def start(self, battle_config: dict[str, Any], epoch: int, battle_num: int) -> dict[str, Any]:
        epoch = max(1, min(int(epoch), 1_000_000))
        battle_num = max(1, min(int(battle_num), 5))
        with self._lock:
            if self._process is not None and self._process.is_alive():
                raise SimulationBusyError("已有模拟正在运行")
            self._stop_event = threading.Event()
            self._completed = 0
            self._target = epoch
            self._stop_requested_completed = None
            self._active_job_id += 1
            job_id = self._active_job_id
            self._state = {
                "state": "running",
                "progress": 0,
                "completed": 0,
                "live_completed": 0,
                "live_progress": 0,
                "stop_requested_completed": None,
                "target": epoch,
                "message": "正在建立战斗状态",
                "log": "正在建立战斗状态…",
                "summary": None,
            }
            state = copy.deepcopy(self._state)

        context = self._process_context()
        state_queue = context.Queue()
        # 模拟进程必须是非守护进程：守护进程不允许再创建子进程，而并行模式要由它
        # 拉起 epoch 分片子进程。父进程消失时它靠 _parent_alive() 自行退出。
        if context.get_start_method() == "fork":
            process = context.Process(
                target=_run_forked_simulation,
                args=(self, copy.deepcopy(battle_config), epoch, battle_num, state_queue),
                daemon=False,
                name="wsgr-webui-simulation",
            )
        else:
            spawned_target = (
                _run_spawned_map_simulation
                if self._simulation_kind == "map"
                else _run_spawned_simulation
            )
            process = context.Process(
                target=spawned_target,
                # Windows uses ``spawn`` and would otherwise reopen and parse
                # database.xlsx for every click on “开始模拟”.  Dataset only
                # contains compact pandas frames, so passing the already-loaded
                # instance is substantially cheaper than another Excel parse.
                args=(self.dataset, copy.deepcopy(battle_config), epoch, battle_num, state_queue),
                daemon=False,
                name="wsgr-webui-simulation",
            )
        process.start()
        with self._lock:
            self._process = process
        self._collector_thread = threading.Thread(
            target=self._collect_process_updates,
            args=(job_id, state_queue, process),
            daemon=True,
            name="wsgr-webui-state-collector",
        )
        self._collector_thread.start()
        return state

    def stop(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            requested_completed = self._completed
            # The terminated child no longer owns the active job.  This lets a
            # new simulation start immediately instead of waiting for process
            # reaping to finish.
            self._process = None
            self._stop_requested_completed = requested_completed
            self._active_job_id += 1
            self._state["state"] = "stopped"
            self._state["message"] = "模拟已停止"
            self._state["live_completed"] = requested_completed
            self._state["live_progress"] = requested_completed / max(self._target, 1) * 100
            self._state["stop_requested_completed"] = requested_completed
            self._state["completed"] = requested_completed
            self._state["progress"] = self._state["live_progress"]
            state = copy.deepcopy(self._state)
        if process is not None and process.is_alive():
            process.terminate()
            threading.Thread(
                target=self._reap_stopped_process,
                args=(process,),
                daemon=True,
                name="wsgr-webui-process-reaper",
            ).start()
        return state

    @staticmethod
    def _reap_stopped_process(process: mp.Process) -> None:
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)

    @staticmethod
    def _process_context() -> mp.context.BaseContext:
        if sys.platform != "win32" and "fork" in mp.get_all_start_methods():
            return mp.get_context("fork")
        return mp.get_context("spawn")

    def _collect_process_updates(self, job_id: int, state_queue: mp.Queue, process: mp.Process) -> None:
        while process.is_alive() or not state_queue.empty():
            try:
                state = state_queue.get(timeout=0.05)
            except Empty:
                continue
            with self._lock:
                if job_id != self._active_job_id:
                    continue
                self._state = state
                self._completed = state.get("live_completed", state.get("completed", 0))

    def _send_state_to_parent(self) -> None:
        if self._state_sink is None:
            return
        try:
            self._state_sink.put_nowait(copy.deepcopy(self._state))
        except Exception:
            pass

    def _run(self, battle_config: dict[str, Any], epoch: int, battle_num: int) -> None:
        try:
            # On POSIX the WebUI starts simulations with ``fork``.  Without
            # reseeding here, each child inherits the parent's unchanged
            # NumPy RNG state, so repeated runs with the same fleet can replay
            # the exact same first battle and detail log.
            np.random.seed(None)
            skill_messages: list[str] = []
            battle_timer = timer()
            battle = load_config(
                battle_config, str(MAP_DIR), self.dataset, battle_timer,
                log_func=skill_messages.append,
            )
            if self._stop_event.is_set():
                with self._lock:
                    self._state.update({
                        "state": "stopped",
                        "message": "模拟已停止",
                        "log": "模拟已停止",
                    })
                return
            set_supply(battle, battle_num)
            prebattle_info = self._prebattle_info(battle)
            log_prefix = "\n".join([
                "【技能读取】",
                *(skill_messages or ["未配置可读取的技能"]),
                "",
                "【运行信息】",
                "模拟已启动，正在收集运行结果",
                "",
            ])

            friend_names = [ship.status["name"] for ship in battle.friend.ship]
            enemy_names = [ship.status["name"] for ship in battle.enemy.ship]
            publish_every = max(1, epoch // 100)
            workers = self._resolve_workers(epoch)
            if workers > 1:
                completed, state = self._run_parallel_epochs(
                    battle_config, epoch, battle_num, workers, publish_every,
                    log_prefix, friend_names, enemy_names, prebattle_info,
                )
            else:
                completed, state = self._run_serial_epochs(
                    battle, epoch, publish_every, log_prefix,
                    friend_names, enemy_names, prebattle_info,
                )

            final_state_name = "stopped" if self._stop_event.is_set() and completed < epoch else "complete"
            summary = self._summary_from_state(
                state, completed, friend_names, enemy_names, prebattle_info,
            )
            self._publish(final_state_name, completed, epoch, summary, log_prefix)
        except Exception as exc:  # keep the HTTP service alive and report the actual failure
            with self._lock:
                self._state.update({
                    "state": "error",
                    "message": str(exc),
                    "log": f"模拟失败：{exc}",
                })
            self._send_state_to_parent()

    def _resolve_workers(self, epoch: int) -> int:
        """按模拟设置里的并行度决定子进程数；1 表示串行。"""
        return resolve_workers(load_simulation_workers(), epoch)

    def _summary_from_state(
        self, state: dict[str, Any], completed: int,
        friend_names: list[str], enemy_names: list[str], prebattle_info: dict[str, Any],
    ) -> dict[str, Any]:
        """用累加器状态生成摘要（串行与并行共用同一份统计逻辑）。"""
        return self._build_summary(
            completed, state["result_counts"], state["flagship_sink_count"],
            state["damage_total"], state["damage_samples"], state["phase_totals"],
            state["ship_damage_totals"], state["ship_damage_phase_totals"],
            state["supply_totals"], friend_names, enemy_names,
            state["friend_mid_damage_hits"], state["friend_heavy_damage_hits"],
            state["enemy_sink_hits"], state["enemy_remaining_health_totals"],
            state["battle_detail"], state["battle_detail_info"], prebattle_info,
        )

    def _run_serial_epochs(
        self, battle, epoch: int, publish_every: int, log_prefix: str,
        friend_names: list[str], enemy_names: list[str], prebattle_info: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        """串行路径：行为与历史实现一致，累加逻辑抽到 _accumulate_battle_epoch。"""
        state = _new_battle_state()
        completed = 0
        for index in range(epoch):
            if self._stop_event.is_set():
                break
            battle.rewind_snapshot()
            battle.start()
            report = battle.report()
            completed = index + 1
            self._completed = completed
            if completed % 25 == 0 and not _parent_alive():
                # 父进程（WebUI）已消失：自行结束，避免非守护进程残留。
                self._stop_event.set()
                break
            _accumulate_battle_epoch(state, battle, report, friend_names, enemy_names)

            if self._stop_event.is_set():
                break

            # Let the HTTP worker acquire the GIL and set a pending stop event
            # before this simulation thread starts another battle.
            time.sleep(0)
            if self._stop_event.is_set():
                break

            if completed == 1 or completed % publish_every == 0 or completed == epoch:
                self._publish(
                    "running", completed, epoch,
                    self._summary_from_state(
                        state, completed, friend_names, enemy_names, prebattle_info,
                    ),
                    log_prefix,
                )
        return completed, state

    def _run_parallel_epochs(
        self, battle_config: dict[str, Any], epoch: int, battle_num: int, workers: int,
        publish_every: int, log_prefix: str,
        friend_names: list[str], enemy_names: list[str], prebattle_info: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        """并行路径：epoch 分片给子进程，子进程只回传增量，本进程合并并按原节奏发布。"""
        context = self._process_context()
        progress_sink = context.Queue()
        shared_stop = context.Event()
        processes = []
        for index, (_, count) in enumerate(split_epochs(epoch, workers)):
            process = context.Process(
                target=_run_battle_epoch_worker,
                args=(self.dataset, battle_config, battle_num, index, count,
                      progress_sink, shared_stop),
                daemon=True,
                name=f"wsgr-battle-epochs-{index}",
            )
            process.start()
            processes.append(process)
        self._install_parallel_stop(shared_stop)

        state = _new_battle_state()
        completed = 0
        pending = len(processes)
        try:
            while pending > 0:
                if not _parent_alive():
                    shared_stop.set()
                    break
                if self._stop_event.is_set():
                    shared_stop.set()
                try:
                    message = progress_sink.get(timeout=0.1)
                except Empty:
                    if not any(process.is_alive() for process in processes):
                        break
                    continue
                if message[0] == "delta":
                    _, count, delta = message
                    _merge_battle_delta(state, delta)
                    completed += count
                    self._completed = completed
                    if completed == 1 or completed % publish_every == 0 or completed >= epoch:
                        self._publish(
                            "running", completed, epoch,
                            self._summary_from_state(
                                state, completed, friend_names, enemy_names, prebattle_info,
                            ),
                            log_prefix,
                        )
                elif message[0] == "done":
                    pending -= 1
                elif message[0] == "error":
                    shared_stop.set()
                    raise RuntimeError(f"并行模拟子进程失败：\n{message[1]}")
        finally:
            shared_stop.set()
            for process in processes:
                process.join(timeout=2)
                if process.is_alive():
                    process.terminate()
            progress_sink.close()
        return completed, state

    def _install_parallel_stop(self, shared_stop) -> None:
        """父进程 terminate 本进程时先广播停止信号，避免把子进程留成孤儿。"""
        def handler(signum, frame):
            shared_stop.set()
            self._stop_event.set()

        try:
            signal.signal(signal.SIGTERM, handler)
        except (ValueError, OSError):
            pass

    @staticmethod
    def _build_summary(
        completed: int,
        result_counts: dict[str, int],
        flagship_sink_count: int,
        damage_total: float,
        damage_samples: list[float],
        phase_totals: np.ndarray,
        ship_damage_totals: np.ndarray,
        ship_damage_phase_totals: np.ndarray,
        supply_totals: dict[str, float],
        friend_names: list[str],
        enemy_names: list[str],
        friend_mid_damage_hits: np.ndarray,
        friend_heavy_damage_hits: np.ndarray,
        enemy_sink_hits: np.ndarray,
        enemy_remaining_health_totals: np.ndarray,
        battle_detail: str,
        battle_detail_info: dict[str, Any] | None,
        prebattle_info: dict[str, Any],
    ) -> dict[str, Any]:
        divisor = max(completed, 1)
        supply = {key: value / divisor for key, value in supply_totals.items()}
        return {
            "result_counts": result_counts.copy(),
            "win_rate": (result_counts["SS"] + result_counts["S"]) / divisor * 100,
            "flagship_sink_rate": flagship_sink_count / divisor * 100,
            "average_damage": damage_total / divisor,
            "damage_floor_5": float(np.percentile(damage_samples, 5, method="lower")) if damage_samples else 0.0,
            "average_bucket": supply["repeat"],
            "resource_total": supply["oil"] + supply["ammo"] + supply["steel"] + 3 * supply["almn"],
            "phase_damage": [
                {"index": index, "name": PHASE_LABELS.get(phase, phase), "value": float(phase_totals[index] / divisor)}
                for index, phase in enumerate(PHASE_LABELS.keys())
                if phase_totals[index] > 0
            ],
            "ship_damage": [
                {"name": friend_names[index], "value": float(ship_damage_totals[index] / divisor)}
                for index in range(len(friend_names))
            ],
            "ship_damage_by_phase": [
                {
                    "name": PHASE_LABELS.get(phase, phase),
                    "value": float(phase_totals[index] / divisor),
                    "ships": [
                        {"name": friend_names[ship_index], "value": float(ship_damage_phase_totals[index, ship_index] / divisor)}
                        for ship_index in range(len(friend_names))
                    ],
                }
                for index, phase in enumerate(PHASE_LABELS.keys())
            ],
            "supply": supply,
            "friend_mid_damage_rates": [
                {"name": name, "rate": float(friend_mid_damage_hits[index] / divisor * 100)}
                for index, name in enumerate(friend_names)
            ],
            "friend_heavy_damage_rates": [
                {"name": name, "rate": float(friend_heavy_damage_hits[index] / divisor * 100)}
                for index, name in enumerate(friend_names)
            ],
            "enemy_sink_rates": [
                {"name": name, "rate": float(enemy_sink_hits[index] / divisor * 100)}
                for index, name in enumerate(enemy_names)
            ],
            "enemy_remaining_health": [
                {"name": name, "value": float(enemy_remaining_health_totals[index] / divisor)}
                for index, name in enumerate(enemy_names)
            ],
            "prebattle": copy.deepcopy(prebattle_info),
            "battle_detail": battle_detail,
            "battle_detail_info": copy.deepcopy(battle_detail_info),
        }

    @staticmethod
    def _detail_battle_info(battle, report: dict[str, Any]) -> dict[str, Any]:
        """Return the compact status values belonging to the exported detail battle."""
        air_con_flag = report.get("aerial", [None])[0]
        recon_flag = battle.timer.recon_flag
        direction_flag = battle.timer.direction_flag
        return {
            "result": report.get("result"),
            "recon_success": None if recon_flag is None else bool(recon_flag),
            "direction": None if direction_flag is None else int(direction_flag),
            "air_con": None if air_con_flag is None else int(air_con_flag),
        }

    def _publish(
        self,
        state: str,
        completed: int,
        target: int,
        summary: dict[str, Any],
        log_prefix: str,
    ) -> None:
        progress = completed / max(target, 1) * 100
        counts = summary["result_counts"]
        log = log_prefix + (
            f"已完成 {completed:,} / {target:,} 次模拟（{progress:.1f}%）\n"
            + "战果分布："
            + "  ".join(f"{flag} {counts[flag]:,}" for flag in RESULT_FLAGS)
            + f"\n综合胜率：{summary['win_rate']:.2f}%"
            + f"  旗舰击沉：{summary['flagship_sink_rate']:.2f}%"
            + f"  平均伤害：{summary['average_damage']:.1f}"
        )
        if state == "stopped" and self._stop_requested_completed is not None:
            log += (
                f"\n停止请求接收时：{self._stop_requested_completed:,} 次"
                f"  最终完成：{completed:,} 次"
            )
        message = {
            "running": "正在模拟",
            "complete": "模拟完成",
            "stopped": "模拟已停止",
        }[state]
        with self._lock:
            self._state.update({
                "state": state,
                "progress": progress,
                "completed": completed,
                "live_completed": completed,
                "live_progress": progress,
                "target": target,
                "message": message,
                "log": log,
                "summary": summary,
            })
        self._send_state_to_parent()

    @staticmethod
    def _prebattle_info(battle) -> dict[str, Any]:
        """Collect recon and aerial values for the compact result cards."""
        preview_battle = copy.deepcopy(battle)
        preview_battle.start()
        report = preview_battle.report()
        recon_rate, friend_recon, recon_request = report["recon"]
        air_con_flag, aerial_friend, aerial_enemy = report["aerial"]
        if air_con_flag is None:
            air_con_text = "无"
        else:
            air_con_info = ["空确", "空优", "均势", "劣势", "丧失"]
            air_con_text = air_con_info[int(air_con_flag) - 1]
        return {
            "recon_rate": int(recon_rate),
            "friend_recon": float(friend_recon),
            "recon_request": float(recon_request),
            "air_con": air_con_text,
            "friend_aerial": float(aerial_friend),
            "enemy_aerial": float(aerial_enemy),
        }


class MapSimulationManager(SimulationManager):
    """Run standalone-map simulations independently from single-battle jobs."""

    def __init__(self, dataset: Dataset):
        super().__init__(dataset)
        self._simulation_kind = "map"

    def _run(self, battle_config: dict[str, Any], epoch: int, battle_num: int) -> None:
        try:
            np.random.seed(None)
            skill_messages: list[str] = []
            battle_timer = timer()
            battle = load_config(
                battle_config, str(MAP_DIR), self.dataset, battle_timer,
                log_func=skill_messages.append,
            )
            map_config = battle.map_config
            if not isinstance(map_config, dict):
                raise ValueError("地图模拟需要独立 YAML 地图")
            node_order, boss_node_names, friend_ship_names = _map_accumulator_shape(battle)
            publish_every = max(1, epoch // 100)
            log_prefix = "\n".join([
                "【技能读取】",
                *(skill_messages or ["未配置可读取的技能"]),
                "",
                "【地图运行】",
                f"海图：{map_config.get('name', '未命名海图')}",
                "",
            ])

            workers = self._resolve_workers(epoch)
            if workers > 1:
                completed, state = self._run_parallel_map_epochs(
                    battle_config, epoch, workers, publish_every, log_prefix,
                    node_order, boss_node_names, friend_ship_names,
                )
            else:
                completed, state = self._run_serial_map_epochs(
                    battle, epoch, publish_every, log_prefix,
                    node_order, boss_node_names, friend_ship_names,
                )

            final_state_name = "stopped" if self._stop_event.is_set() and completed < epoch else "complete"
            summary = self._summary_from_map_state(state, completed, friend_ship_names)
            self._publish_map(final_state_name, completed, epoch, summary, log_prefix)
        except Exception as exc:
            with self._lock:
                self._state.update({
                    "state": "error",
                    "message": str(exc),
                    "log": f"地图模拟失败：{exc}",
                })
            self._send_state_to_parent()

    def _summary_from_map_state(
        self, state: dict[str, Any], completed: int, friend_ship_names: list[str],
    ) -> dict[str, Any]:
        """用累加器状态生成地图摘要（串行与并行共用同一份统计逻辑）。"""
        return self._build_map_summary(
            completed, state["boss_battles"], state["boss_flagship_sinks"],
            state["node_statistics"], friend_ship_names, state["supply_totals"],
            state["first_record"], state["boss_statistics"],
            boss_result_counts=state["boss_result_counts"],
            boss_end_counts=state["boss_end_counts"],
        )

    def _run_serial_map_epochs(
        self, battle, epoch: int, publish_every: int, log_prefix: str,
        node_order: list[str], boss_node_names: list[str], friend_ship_names: list[str],
    ) -> tuple[int, dict[str, Any]]:
        state = _new_map_state(node_order, boss_node_names, friend_ship_names)
        completed = 0
        for index in range(epoch):
            if self._stop_event.is_set():
                break
            battle.rewind_snapshot()
            battle.start()
            report = battle.report()
            completed = index + 1
            self._completed = completed
            if completed % 25 == 0 and not _parent_alive():
                self._stop_event.set()
                break
            _accumulate_map_epoch(state, report, friend_ship_names)

            time.sleep(0)
            if self._stop_event.is_set():
                break
            if completed == 1 or completed % publish_every == 0 or completed == epoch:
                self._publish_map(
                    "running", completed, epoch,
                    self._summary_from_map_state(state, completed, friend_ship_names),
                    log_prefix,
                )
        return completed, state

    def _run_parallel_map_epochs(
        self, battle_config: dict[str, Any], epoch: int, workers: int, publish_every: int,
        log_prefix: str, node_order: list[str], boss_node_names: list[str],
        friend_ship_names: list[str],
    ) -> tuple[int, dict[str, Any]]:
        """并行路径：epoch 分片给子进程，子进程只回传增量，本进程合并并按原节奏发布。"""
        context = self._process_context()
        progress_sink = context.Queue()
        shared_stop = context.Event()
        processes = []
        for index, (_, count) in enumerate(split_epochs(epoch, workers)):
            process = context.Process(
                target=_run_map_epoch_worker,
                args=(self.dataset, battle_config, index, count, progress_sink, shared_stop),
                daemon=True,
                name=f"wsgr-map-epochs-{index}",
            )
            process.start()
            processes.append(process)
        self._install_parallel_stop(shared_stop)

        state = _new_map_state(node_order, boss_node_names, friend_ship_names)
        completed = 0
        pending = len(processes)
        try:
            while pending > 0:
                if not _parent_alive():
                    shared_stop.set()
                    break
                if self._stop_event.is_set():
                    shared_stop.set()
                try:
                    message = progress_sink.get(timeout=0.1)
                except Empty:
                    if not any(process.is_alive() for process in processes):
                        break
                    continue
                if message[0] == "delta":
                    _, count, delta = message
                    _merge_map_delta(state, delta)
                    completed += count
                    self._completed = completed
                    if completed == 1 or completed % publish_every == 0 or completed >= epoch:
                        self._publish_map(
                            "running", completed, epoch,
                            self._summary_from_map_state(state, completed, friend_ship_names),
                            log_prefix,
                        )
                elif message[0] == "done":
                    pending -= 1
                elif message[0] == "error":
                    shared_stop.set()
                    raise RuntimeError(f"并行地图模拟子进程失败：\n{message[1]}")
        finally:
            shared_stop.set()
            for process in processes:
                process.join(timeout=2)
                if process.is_alive():
                    process.terminate()
            progress_sink.close()
        return completed, state

    @staticmethod
    def _build_map_summary(
        completed: int,
        boss_battles: int,
        boss_flagship_sinks: int,
        node_statistics: dict[str, dict[str, Any]],
        friend_ship_names: list[str],
        supply_totals: dict[str, float],
        first_record: str,
        boss_statistics: dict[str, dict[str, Any]] | None = None,
        boss_result_counts: dict[str, int] | None = None,
        boss_end_counts: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        divisor = max(completed, 1)
        boss_statistics = boss_statistics or {}
        boss_result_counts = boss_result_counts or {}
        boss_end_counts = boss_end_counts or {}

        def boss_ship_damage_rates(name: str, key: str) -> list[float | None]:
            statistics = node_statistics.get(name, {})
            battle_count = int(statistics.get("battles", 0))
            values = statistics.get(key, np.zeros(len(friend_ship_names), dtype=float))
            return [
                float(rate / battle_count * 100) if battle_count else None
                for rate in values
            ]

        return {
            # Boss 综合胜率：所有 Boss 点战斗中取得 SS/S 的场次 / Boss 战斗场次
            "boss_win_rate": (
                boss_result_counts.get("SS", 0) + boss_result_counts.get("S", 0)
            ) / max(boss_battles, 1) * 100,
            # Boss 旗舰击沉率：所有 Boss 点战斗中击沉敌方旗舰的场次 / Boss 战斗场次
            "boss_flagship_sink_rate": boss_flagship_sinks / max(boss_battles, 1) * 100,
            # 完成率：抵达 Boss 终点节点的局数 / 总局数（等于各 Boss 完成率之和）
            "completion_rate": sum(boss_end_counts.values()) / divisor * 100,
            "simulation_count": completed,
            "resource_total": (
                supply_totals["oil"] + supply_totals["ammo"]
                + supply_totals["steel"] + 3 * supply_totals["almn"]
            ) / divisor,
            "supply": {
                key: value / divisor
                for key, value in supply_totals.items()
            },
            "friend_ship_names": friend_ship_names.copy(),
            "boss_statistics": [
                {
                    "name": name,
                    "simulations": values["simulations"],
                    "clear_rate": (
                        (values["result_counts"]["SS"] + values["result_counts"]["S"])
                        / values["simulations"] * 100
                        if values["simulations"] else None
                    ),
                    "result_rates": {
                        flag: (
                            values["result_counts"][flag] / values["simulations"] * 100
                            if values["simulations"] else None
                        )
                        for flag in RESULT_FLAGS
                    },
                    "flagship_sink_rate": (
                        values["flagship_sinks"] / values["simulations"] * 100
                        if values["simulations"] else None
                    ),
                    # 以该 Boss 点为终点的局数 / 总局数
                    "completion_rate": boss_end_counts.get(name, 0) / divisor * 100,
                    "resource_total": (
                        values["supply_totals"]["oil"]
                        + values["supply_totals"]["ammo"]
                        + values["supply_totals"]["steel"]
                        + 3 * values["supply_totals"]["almn"]
                    ) / max(values["simulations"], 1),
                    "supply": {
                        key: value / max(values["simulations"], 1)
                        for key, value in values["supply_totals"].items()
                    },
                    "average_bucket": (
                        values["supply_totals"]["repeat"]
                        / max(values["simulations"], 1)
                    ),
                    "average_dcitem": (
                        values["supply_totals"]["dcitem"]
                        / max(values["simulations"], 1)
                    ),
                    "friend_mid_damage_rates": boss_ship_damage_rates(
                        name, "mid_damage_by_ship",
                    ),
                    "friend_heavy_damage_rates": boss_ship_damage_rates(
                        name, "heavy_damage_by_ship",
                    ),
                }
                for name, values in boss_statistics.items()
            ],
            "node_statistics": [
                {
                    "name": name,
                    "visits": values["visits"],
                    "battles": values["battles"],
                    "result_rates": {
                        flag: (
                            values["result_counts"][flag] / values["battles"] * 100
                            if values["battles"] else None
                        )
                        for flag in RESULT_FLAGS
                    },
                    "mid_damage_rate": (
                        values["mid_damage"] / values["battles"] * 100
                        if values["battles"] else None
                    ),
                    "heavy_damage_rate": (
                        values["heavy_damage"] / values["battles"] * 100
                        if values["battles"] else None
                    ),
                    "recon_rate": (
                        values["recon_rate_total"] / values["recon_rate_count"]
                        if values["recon_rate_count"] else None
                    ),
                    "roundabout_rate": (
                        values["roundabout_rate_total"] / values["roundabout_rate_count"]
                        if values["roundabout_rate_count"] else None
                    ),
                    "mid_damage_ship_rates": [
                        float(rate / values["battles"] * 100)
                        if values["battles"] else None
                        for rate in values["mid_damage_by_ship"]
                    ],
                    "heavy_damage_ship_rates": [
                        float(rate / values["battles"] * 100)
                        if values["battles"] else None
                        for rate in values["heavy_damage_by_ship"]
                    ],
                }
                for name, values in node_statistics.items()
            ],
            "battle_detail": first_record,
        }

    def _publish_map(
        self,
        state: str,
        completed: int,
        target: int,
        summary: dict[str, Any],
        log_prefix: str,
    ) -> None:
        progress = completed / max(target, 1) * 100
        log = log_prefix + (
            f"已完成 {completed:,} / {target:,} 次模拟（{progress:.1f}%）\n"
            f"Boss综合胜率：{summary['boss_win_rate']:.2f}%"
            f"  Boss旗舰击沉：{summary['boss_flagship_sink_rate']:.2f}%"
            f"  完成率：{summary['completion_rate']:.2f}%"
            f"  资源消耗：{summary['resource_total']:.1f}"
        )
        with self._lock:
            self._state.update({
                "state": state,
                "progress": progress,
                "completed": completed,
                "live_completed": completed,
                "live_progress": progress,
                "target": target,
                "message": {"running": "正在模拟", "stopped": "模拟已停止"}.get(state, "模拟完成"),
                "log": log,
                "summary": summary,
            })
        self._send_state_to_parent()


def normalise_simulation_workers(value: Any) -> int:
    """校验模拟并行度（子进程数）；1 表示串行。"""
    if value is None or value == '':
        return DEFAULT_SIMULATION_WORKERS
    try:
        workers = int(value)
    except (TypeError, ValueError):
        raise ValueError('模拟并行度必须是整数')
    if workers < 1 or workers > MAX_SIMULATION_WORKERS:
        raise ValueError(f'模拟并行度必须在 1 到 {MAX_SIMULATION_WORKERS} 之间')
    return workers


def read_user_settings() -> dict[str, Any]:
    """原样读出 depend/user_settings.yaml（保留未知字段，保存时不丢）。"""
    settings_path = Path(user_settings_file)
    if not settings_path.is_file():
        return {}
    try:
        data = yaml.safe_load(settings_path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def write_user_settings(settings: dict[str, Any]) -> None:
    """写回 depend/user_settings.yaml；simulation 固定排在最前。"""
    ordered: dict[str, Any] = {}
    if 'simulation' in settings:
        ordered['simulation'] = settings['simulation']
    ordered.update({key: value for key, value in settings.items() if key != 'simulation'})
    settings_path = Path(user_settings_file)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = settings_path.with_name(settings_path.name + '.tmp')
    with temporary_path.open('w', encoding='utf-8') as file:
        yaml.safe_dump(ordered, file, allow_unicode=True, sort_keys=False)
    temporary_path.replace(settings_path)


def load_simulation_workers(settings: dict[str, Any] | None = None) -> int:
    """从用户设置里读模拟并行度；缺失或非法时回退默认值。"""
    if settings is None:
        settings = read_user_settings()
    simulation = settings.get('simulation')
    if not isinstance(simulation, dict):
        return DEFAULT_SIMULATION_WORKERS
    try:
        return normalise_simulation_workers(simulation.get('workers'))
    except ValueError:
        return DEFAULT_SIMULATION_WORKERS


def _new_battle_state() -> dict[str, Any]:
    """单点模拟的可合并累加器：串行直接累积，并行由子进程累积增量后合并。"""
    return {
        "result_counts": {flag: 0 for flag in RESULT_FLAGS},
        "flagship_sink_count": 0,
        "damage_total": 0.0,
        "damage_samples": [],
        "phase_totals": np.zeros(len(PHASE_LABELS), dtype=float),
        "ship_damage_totals": np.zeros(6, dtype=float),
        "ship_damage_phase_totals": np.zeros((len(PHASE_LABELS), 6), dtype=float),
        "friend_mid_damage_hits": np.zeros(6, dtype=float),
        "friend_heavy_damage_hits": np.zeros(6, dtype=float),
        "enemy_sink_hits": np.zeros(6, dtype=float),
        "enemy_remaining_health_totals": np.zeros(6, dtype=float),
        "supply_totals": {
            key: 0.0 for key in ("oil", "ammo", "steel", "almn", "repeat", "dcitem")
        },
        "battle_detail": "",
        "battle_detail_info": None,
    }


def _accumulate_battle_epoch(target, current_battle, report, friend_names, enemy_names) -> None:
    """把一次战斗结果累加进 target（串行用总累加器，并行用子进程的增量）。"""
    flag = report.get("result", "D")
    if flag not in target["result_counts"]:
        flag = "D"
    target["result_counts"][flag] += 1

    created_damage = np.asarray(report["create_damage"], dtype=float)[:, :6]
    ship_damage = created_damage.sum(axis=0)
    target["ship_damage_totals"] += ship_damage
    target["ship_damage_phase_totals"] += created_damage
    current_total_damage = float(ship_damage.sum())
    target["damage_total"] += current_total_damage
    target["damage_samples"].append(current_total_damage)
    target["phase_totals"] += created_damage.sum(axis=1)

    final_state = np.asarray(report["damaged_state"])[-1]
    friend_state = final_state[:len(friend_names)]
    enemy_state = final_state[6:6 + len(enemy_names)]
    target["friend_mid_damage_hits"][:len(friend_names)] += friend_state >= 2
    target["friend_heavy_damage_hits"][:len(friend_names)] += friend_state >= 3
    target["enemy_sink_hits"][:len(enemy_names)] += enemy_state == 4
    target["enemy_remaining_health_totals"][:len(enemy_names)] += [
        ship.status["health"] for ship in current_battle.enemy.ship
    ]
    target["flagship_sink_count"] += int(len(enemy_state) > 0 and enemy_state[0] == 4)

    for key in target["supply_totals"]:
        value = report.get("dcitem", 0) if key == "dcitem" else report.get("supply", {}).get(key, 0)
        target["supply_totals"][key] += float(value)

    if not target["battle_detail"]:
        target["battle_detail"] = report.get("record", "")
        target["battle_detail_info"] = SimulationManager._detail_battle_info(current_battle, report)


def _merge_battle_delta(target, delta) -> None:
    """把子进程回传的增量并入累加器（样本追加，其余逐项相加）。"""
    for key, value in delta.items():
        if key == "battle_detail":
            if not target[key]:
                target[key] = value
        elif key == "battle_detail_info":
            if target[key] is None:
                target[key] = value
        elif isinstance(value, list):
            target[key].extend(value)
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                target[key][sub_key] += sub_value
        elif isinstance(value, np.ndarray):
            target[key] = target[key] + value
        else:
            target[key] += value


def _parent_alive() -> bool:
    """子进程判断协调进程是否还在，被 terminate 时能尽快自行退出。"""
    parent = mp.parent_process()
    return parent is None or parent.is_alive()


def _run_battle_epoch_worker(dataset, battle_config, battle_num, index, count,
                             progress_sink, shared_stop) -> None:
    """单点模拟分片进程：自己按配置重建战斗，只回传增量累加量。"""
    import traceback

    # 见 runUtil.epoch_worker_entry：缩短 GIL 切换间隔，否则 Queue 投递线程会被主循环
    # 饿死，实时进度要拖到分片结束才回传（同时还能提高整体吞吐）。
    sys.setswitchinterval(0.0005)

    try:
        np.random.seed(None)
        battle = load_config(battle_config, str(MAP_DIR), dataset, timer(), log_func=lambda _: None)
        set_supply(battle, battle_num)
        friend_names = [ship.status["name"] for ship in battle.friend.ship]
        enemy_names = [ship.status["name"] for ship in battle.enemy.ship]
        step = max(1, count // 100)
        delta = _new_battle_state()
        done = 0
        reported = 0
        for _ in range(count):
            if shared_stop.is_set() or not _parent_alive():
                break
            battle.rewind_snapshot()
            battle.start()
            report = battle.report()
            _accumulate_battle_epoch(delta, battle, report, friend_names, enemy_names)
            done += 1
            if done % step == 0:
                progress_sink.put(("delta", done - reported, delta))
                delta = _new_battle_state()
                reported = done
        if done > reported:
            progress_sink.put(("delta", done - reported, delta))
        progress_sink.put(("done", index, done))
    except Exception:
        progress_sink.put(("error", traceback.format_exc()))


def _map_accumulator_shape(battle) -> tuple[list[str], list[str], list[str]]:
    """从战斗对象推导地图累加器的节点/舰船结构（协调进程与子进程共用）。"""
    map_config = battle.map_config
    if not isinstance(map_config, dict):
        raise ValueError("地图模拟需要独立 YAML 地图")
    node_order = [str(node["name"]) for node in map_config["nodes"]]
    boss_node_names = [
        str(node["name"])
        for node in map_config["nodes"]
        if str(node.get("kind", "")) == "boss" or int(node.get("level", 0)) == 5
    ]
    friend_ship_names = [ship.status["name"] for ship in battle.friend.ship]
    return node_order, boss_node_names, friend_ship_names


def _new_map_state(node_order, boss_node_names, friend_ship_names) -> dict[str, Any]:
    """地图模拟的可合并累加器：串行直接累积，并行由子进程累积增量后合并。"""
    supply_keys = ("oil", "ammo", "steel", "almn", "repeat", "dcitem")
    return {
        "node_statistics": {
            name: {
                "visits": 0,
                "battles": 0,
                "result_counts": {flag: 0 for flag in RESULT_FLAGS},
                "mid_damage": 0,
                "heavy_damage": 0,
                "mid_damage_by_ship": np.zeros(len(friend_ship_names), dtype=float),
                "heavy_damage_by_ship": np.zeros(len(friend_ship_names), dtype=float),
                "recon_rate_total": 0.0,
                "recon_rate_count": 0,
                "roundabout_rate_total": 0.0,
                "roundabout_rate_count": 0,
            }
            for name in node_order
        },
        "supply_totals": {key: 0.0 for key in supply_keys},
        "boss_statistics": {
            name: {
                "simulations": 0,
                "result_counts": {flag: 0 for flag in RESULT_FLAGS},
                "flagship_sinks": 0,
                "supply_totals": {key: 0.0 for key in supply_keys},
            }
            for name in boss_node_names
        },
        "boss_battles": 0,
        "boss_flagship_sinks": 0,
        # 所有 Boss 点战斗的战果分布（综合胜率分子：SS + S）
        "boss_result_counts": {flag: 0 for flag in RESULT_FLAGS},
        # 以各 Boss 点为终点结束的局数（总完成率 = 各项之和）
        "boss_end_counts": {name: 0 for name in boss_node_names},
        "first_record": "",
    }


def _accumulate_map_epoch(target, report, friend_ship_names) -> None:
    """把一次地图出征结果累加进 target（串行用总累加器，并行用子进程的增量）。"""
    node_statistics = target["node_statistics"]
    supply_totals = target["supply_totals"]
    boss_statistics = target["boss_statistics"]
    boss_result_counts = target["boss_result_counts"]
    boss_end_counts = target["boss_end_counts"]
    ending_name = str(report.get("end_with", ""))

    if report.get("end_with_boss") and ending_name in boss_end_counts:
        # 抵达 Boss 终点节点即计入完成率，并记到对应的终点 Boss 名下
        boss_end_counts[ending_name] += 1

    for node_event in report.get("map_node_events", []):
        statistics = node_statistics.get(str(node_event.get("name", "")))
        if statistics is None:
            continue
        statistics["visits"] += 1
        recon_rate = node_event.get("recon_rate")
        if recon_rate is not None:
            statistics["recon_rate_total"] += float(recon_rate)
            statistics["recon_rate_count"] += 1
        roundabout_rate = node_event.get("roundabout_rate")
        if roundabout_rate is not None:
            statistics["roundabout_rate_total"] += float(roundabout_rate)
            statistics["roundabout_rate_count"] += 1

    for battle_result in report.get("map_battles", []):
        name = str(battle_result.get("name", ""))
        statistics = node_statistics.get(name)
        if statistics is None:
            continue
        statistics["battles"] += 1
        result = str(battle_result.get("result", "D"))
        if result not in RESULT_FLAGS:
            result = "D"
        statistics["result_counts"][result] += 1
        damaged_state = np.asarray(battle_result.get("friend_damaged_state", []))
        ship_count = min(len(damaged_state), len(friend_ship_names))
        friend_damage = damaged_state[:ship_count]
        statistics["mid_damage"] += int(np.count_nonzero(friend_damage >= 2))
        statistics["heavy_damage"] += int(np.count_nonzero(friend_damage >= 3))
        statistics["mid_damage_by_ship"][:ship_count] += friend_damage >= 2
        statistics["heavy_damage_by_ship"][:ship_count] += friend_damage >= 3
        if battle_result.get("boss", False):
            target["boss_battles"] += 1
            target["boss_flagship_sinks"] += int(battle_result.get("boss_flagship_sunk", False))
            boss_result_counts[result] += 1

    for key in supply_totals:
        value = (
            report.get("dcitem", 0)
            if key == "dcitem"
            else report.get("supply", {}).get(key, 0)
        )
        supply_totals[key] += float(value)

    ending_boss = boss_statistics.get(ending_name)
    if ending_boss is not None:
        boss_result = next((
            item for item in reversed(report.get("map_battles", []))
            if str(item.get("name", "")) == ending_name and item.get("boss", False)
        ), None)
        if boss_result is not None:
            result = str(boss_result.get("result", "D"))
            result = result if result in RESULT_FLAGS else "D"
            ending_boss["simulations"] += 1
            ending_boss["result_counts"][result] += 1
            ending_boss["flagship_sinks"] += int(boss_result.get("boss_flagship_sunk", False))
            for key in supply_totals:
                value = (
                    report.get("dcitem", 0)
                    if key == "dcitem"
                    else report.get("supply", {}).get(key, 0)
                )
                ending_boss["supply_totals"][key] += float(value)

    if not target["first_record"]:
        target["first_record"] = str(report.get("record", ""))


def _merge_map_delta(target, delta) -> None:
    """合并地图增量：节点与 Boss 统计逐项相加，首个战报文本保留。"""
    for name, values in delta["node_statistics"].items():
        node = target["node_statistics"].get(name)
        if node is None:
            continue
        for key, value in values.items():
            if key == "result_counts":
                for flag, count in value.items():
                    node["result_counts"][flag] += count
            elif isinstance(value, np.ndarray):
                node[key] = node[key] + value
            else:
                node[key] += value
    for key, value in delta["supply_totals"].items():
        target["supply_totals"][key] += value
    for name, values in delta["boss_statistics"].items():
        boss = target["boss_statistics"].get(name)
        if boss is None:
            continue
        boss["simulations"] += values["simulations"]
        boss["flagship_sinks"] += values["flagship_sinks"]
        for flag, count in values["result_counts"].items():
            boss["result_counts"][flag] += count
        for key, value in values["supply_totals"].items():
            boss["supply_totals"][key] += value
    for flag, count in delta["boss_result_counts"].items():
        target["boss_result_counts"][flag] += count
    for name, count in delta["boss_end_counts"].items():
        target["boss_end_counts"][name] += count
    for key in ("boss_battles", "boss_flagship_sinks"):
        target[key] += delta[key]
    if not target["first_record"]:
        target["first_record"] = delta["first_record"]


def _run_map_epoch_worker(dataset, battle_config, index, count,
                          progress_sink, shared_stop) -> None:
    """地图模拟分片进程：自己按配置重建战斗，只回传增量累加量。"""
    import traceback

    # 同 _run_battle_epoch_worker：保证实时进度能及时回传
    sys.setswitchinterval(0.0005)

    try:
        np.random.seed(None)
        battle = load_config(battle_config, str(MAP_DIR), dataset, timer(), log_func=lambda _: None)
        node_order, boss_node_names, friend_ship_names = _map_accumulator_shape(battle)
        step = max(1, count // 100)
        delta = _new_map_state(node_order, boss_node_names, friend_ship_names)
        done = 0
        reported = 0
        for _ in range(count):
            if shared_stop.is_set() or not _parent_alive():
                break
            battle.rewind_snapshot()
            battle.start()
            report = battle.report()
            _accumulate_map_epoch(delta, report, friend_ship_names)
            done += 1
            if done % step == 0:
                progress_sink.put(("delta", done - reported, delta))
                delta = _new_map_state(node_order, boss_node_names, friend_ship_names)
                reported = done
        if done > reported:
            progress_sink.put(("delta", done - reported, delta))
        progress_sink.put(("done", index, done))
    except Exception:
        progress_sink.put(("error", traceback.format_exc()))


def _run_forked_simulation(
    manager: SimulationManager,
    battle_config: dict[str, Any],
    epoch: int,
    battle_num: int,
    state_queue: mp.Queue,
) -> None:
    manager._state_sink = state_queue
    manager._run(battle_config, epoch, battle_num)


def _run_spawned_simulation(
    dataset: Dataset,
    battle_config: dict[str, Any],
    epoch: int,
    battle_num: int,
    state_queue: mp.Queue,
) -> None:
    manager = SimulationManager(dataset)
    manager._state_sink = state_queue
    manager._run(battle_config, epoch, battle_num)


def _run_spawned_map_simulation(
    dataset: Dataset,
    battle_config: dict[str, Any],
    epoch: int,
    battle_num: int,
    state_queue: mp.Queue,
) -> None:
    manager = MapSimulationManager(dataset)
    manager._state_sink = state_queue
    manager._run(battle_config, epoch, battle_num)


class WebUIService:
    def __init__(self):
        self.dataset = Dataset(str(DATA_FILE))
        self.simulations = SimulationManager(self.dataset)
        self.map_simulations = MapSimulationManager(self.dataset)
        self._bootstrap: dict[str, Any] | None = None
        self._environment_options: dict[str, list[dict[str, str]]] | None = None

    def bootstrap(self) -> dict[str, Any]:
        if self._bootstrap is None:
            self._bootstrap = {
                "formations": FORMATIONS,
                "ship_labels": copy.deepcopy(SHIP_LABELS),
                "battle_types": BATTLE_TYPES,
                "custom_phases": [
                    {"id": phase, "name": PHASE_LABELS[phase]}
                    for phase in CustomBattle.phase_names
                ],
                "friend_ships": self._friend_ship_metadata(),
                "enemy_ships": self._enemy_ship_metadata(),
                "equipment": [
                    {"eid": str(eid), "name": str(row["名称"])}
                    for eid, row in self.dataset.equip_data_friend.iterrows()
                ],
                "strategies": {
                    key: {
                        "label": group["label"],
                        "items": [
                            {"name": name, "stid": stid}
                            for name, stid in group["items"].items()
                        ],
                    }
                    for key, group in STRATEGIES.items()
                },
                "config": self.load_default_config(),
            }
        return copy.deepcopy(self._bootstrap)

    def environment_settings(self) -> dict[str, Any]:
        if self._environment_options is None:
            self._environment_options = environment_options(environment_data_file)
        return {
            "settings": load_user_settings(user_settings_file, environment_data_file),
            "options": copy.deepcopy(self._environment_options),
        }

    @staticmethod
    def simulation_settings() -> dict[str, Any]:
        """模拟设置（独立于全局增益设定，同存 user_settings.yaml）。"""
        return {
            "settings": {"workers": load_simulation_workers()},
            "path": str(Path(user_settings_file).relative_to(PROJECT_ROOT)),
        }

    @staticmethod
    def map_effects() -> dict[str, list[dict[str, str]]]:
        return {"effects": map_effect_options()}

    def update_environment_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        payload = dict(settings) if isinstance(settings, dict) else {}
        # 环境加成字段严格校验；文件里其它字段（如 simulation）原样保留后合并写回。
        saved_environment = normalise_user_settings(payload, environment_data_file)
        stored = read_user_settings()
        stored.update(saved_environment)
        write_user_settings(stored)
        reload_env_buffs()
        return {
            "settings": saved_environment,
            "path": str(Path(user_settings_file).relative_to(PROJECT_ROOT)),
        }

    @staticmethod
    def update_simulation_settings(settings: dict[str, Any]) -> dict[str, Any]:
        payload = settings if isinstance(settings, dict) else {}
        workers = normalise_simulation_workers(payload.get('workers'))
        stored = read_user_settings()
        stored['simulation'] = {'workers': workers}
        write_user_settings(stored)
        return {
            "settings": {"workers": workers},
            "path": str(Path(user_settings_file).relative_to(PROJECT_ROOT)),
        }

    def friend_health_limit(self, ship_config: dict[str, Any]) -> dict[str, int]:
        """Calculate a friendly ship's current maximum durability in isolation.

        Health-related effects are local to the ship, so a lightweight pair of
        temporary fleets is sufficient here; no battle phases are started.
        """
        if not isinstance(ship_config, dict):
            raise ValueError("舰船配置必须为对象")

        required = ("cid", "skill")
        missing = [key for key in required if key not in ship_config]
        if missing:
            raise ValueError(f"舰船配置缺少字段：{', '.join(missing)}")

        preview_config = {
            "cid": str(ship_config["cid"]),
            # Only the ship, its selected skill and equipment affect the durability cap.
            # Fixed neutral values keep this preview small and independent from unrelated editor fields.
            "loc": 1,
            "level": 110,
            "affection": 200,
            "skill": int(ship_config["skill"]),
            "equipment": list(ship_config.get("equipment") or []),
            "strategy": [],
        }
        preview_timer = timer()
        friend = Fleet(preview_timer)
        enemy = Fleet(preview_timer)
        friend.set_form(4)
        friend.set_side(1)
        enemy.set_form(4)
        enemy.set_side(0)

        try:
            ship = load_friend_ship(preview_config, self.dataset, preview_timer, log_func=lambda _: None)
            ship.set_master(friend)
            friend.set_ship([ship])
            friend.set_side(1)
            ship.init_skill(friend, enemy)
            ship.init_health()
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"无法计算该舰船的耐久上限：{exc}") from exc

        maximum = max(1, int(ship.status["standard_health"]))
        return {"max_health": maximum}

    def map_enemy_fleet_summary(self, fleet_config: dict[str, Any]) -> dict[str, float]:
        """Calculate enemy recon, aerial control, and fleet speed."""
        if not isinstance(fleet_config, dict):
            raise ValueError("敌方舰队配置无效")
        return calculate_map_enemy_fleet_summary(self.dataset, fleet_config)

    @staticmethod
    def map_exists(mapid: str) -> dict[str, Any]:
        """Check whether the standalone map referenced by a configuration exists."""
        normalized = normalize_map_ref(mapid)
        path = Path(map_yaml_path(normalized, str(MAP_DIR)))
        return {"mapid": normalized, "exists": path.is_file()}

    @staticmethod
    def load_map_document(mapid: str) -> dict[str, Any]:
        """Return a standalone map document for the editor without starting a run."""
        normalized = normalize_map_ref(mapid)
        return {"mapid": normalized, "map": load_map_yaml(normalized, str(MAP_DIR))}

    @staticmethod
    def list_maps() -> dict[str, Any]:
        """List every standalone map below depend/map as a relative map reference."""
        root = Path(MAP_DIR)
        maps: list[str] = []
        if not root.is_dir():
            return {"root": str(root), "maps": maps}
        for path in sorted(root.rglob("*.yaml")):
            # macOS AppleDouble sidecars are not map documents.
            if path.name.startswith("._"):
                continue
            relative = path.relative_to(root)
            try:
                maps.append(normalize_map_ref("/".join([*relative.parts[:-1], relative.stem])))
            except ValueError:
                # Names that cannot be referenced from a configuration are skipped.
                continue
        return {"root": str(root), "maps": maps}

    @staticmethod
    def validate_map_document(map_document: dict[str, Any]) -> str:
        """Validate the minimum standalone map document shape and return its id."""
        if not isinstance(map_document, dict):
            raise ValueError("地图内容必须为对象")
        mapid = str(map_document.get("mapid", "")).strip()
        if not mapid:
            raise ValueError("地图名称不能为空")
        if not isinstance(map_document.get("nodes"), list) or not isinstance(map_document.get("routes"), list):
            raise ValueError("地图必须包含 nodes 和 routes")
        return mapid

    @classmethod
    def load_uploaded_map_document(cls, content: str) -> dict[str, Any]:
        """Parse a map upload through the same YAML loader as configuration uploads."""
        map_document = cls.load_uploaded_config("map.yaml", content)
        cls.validate_map_document(map_document)
        return {"map": map_document}

    @classmethod
    def save_map_document(
        cls,
        map_document: dict[str, Any],
        *,
        mapid: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Persist a standalone map document below depend/map.

        ``mapid`` is the relative map path including its category folders
        (``活动/2024夏活/E5``); when omitted the document's own id is used, which
        writes to the map root.  The saved document always stores the leaf name
        in its ``mapid`` field so a map file stays independent from its folder.
        """
        cls.validate_map_document(map_document)
        target = normalize_map_ref(
            map_document.get("mapid", "") if mapid is None else mapid
        )
        leaf = target.rsplit("/", 1)[-1]
        document = dict(map_document)
        document["mapid"] = leaf
        path = Path(map_yaml_path(target, str(MAP_DIR)))
        existed = path.is_file()
        if existed and not overwrite:
            return {
                "mapid": target,
                "path": f"{target}.yaml",
                "filename": path.name,
                "saved": False,
                "requires_overwrite": True,
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(document, file, allow_unicode=True, sort_keys=False)
        return {
            "mapid": target,
            "path": f"{target}.yaml",
            "filename": path.name,
            "saved": True,
            "overwritten": existed,
        }

    def prepare_simulation_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Drop redundant full-health overrides before a simulation starts."""
        prepared = copy.deepcopy(config)
        friend_fleet = prepared.get("friend_fleet")
        if not isinstance(friend_fleet, dict):
            return prepared

        for ship in friend_fleet.get("ships", []):
            if not isinstance(ship, dict) or ship.get("input_health") is None:
                continue
            maximum = self.friend_health_limit(ship)["max_health"]
            input_health = max(1, int(ship["input_health"]))
            if input_health >= maximum:
                ship.pop("input_health", None)
            else:
                ship["input_health"] = input_health
        return prepared

    def _friend_ship_metadata(self) -> list[dict[str, Any]]:
        ships: list[dict[str, Any]] = []
        for remodeled, frame in ((False, self.dataset.ship_data_0), (True, self.dataset.ship_data_1)):
            for cid, row in frame.iterrows():
                name = str(row["名称"]) + ("-改" if remodeled else "")
                ships.append({
                    "cid": str(cid),
                    "name": name,
                    "type": str(row["舰种"]),
                    "country": str(row["国籍"]),
                    "equip_slots": _serializable_number(row["装备栏"], 4),
                    "skills": _skill_options([str(row["技能1"]), str(row["技能2"])]),
                })
        return ships

    def _enemy_ship_metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "cid": str(cid),
                "name": str(row["名称"]),
                "type": str(row["舰种"]),
                "level": _serializable_number(row["等级"], 110),
                "health": _serializable_number(row["耐久"]),
                "armor": _serializable_number(row["装甲"]),
                "antiair": _serializable_number(row["对空"]),
            }
            for cid, row in self.dataset.ship_data_enemy.iterrows()
        ]

    @staticmethod
    def load_default_config() -> dict[str, Any]:
        return {
            "battle_type": "NormalBattle",
            "friend_fleet": {"side": 1, "form": 4, "ships": []},
            "enemy_fleet": {"side": 0, "form": 4, "ships": []},
        }

    @staticmethod
    def load_uploaded_config(filename: str, content: str) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower()
        if suffix in (".yaml", ".yml"):
            config = yaml.safe_load(content)
            if not isinstance(config, dict):
                raise ValueError("YAML 配置的顶层必须为对象")
            return config
        if suffix == ".xml":
            import tempfile

            temporary_path: str | None = None
            try:
                # Windows cannot reopen a NamedTemporaryFile while its file
                # handle is still open.  Close it before load_xml reads it.
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".xml", encoding="utf-8", delete=False
                ) as file:
                    file.write(content)
                    temporary_path = file.name
                return load_xml(temporary_path, str(MAP_DIR))
            finally:
                if temporary_path:
                    Path(temporary_path).unlink(missing_ok=True)
        raise ValueError("仅支持 .yaml、.yml 或 .xml 配置文件")

    @staticmethod
    def dump_config(config: dict[str, Any]) -> str:
        return yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
