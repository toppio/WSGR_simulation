# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38

import copy
import os
import sys
import time
import threading
import multiprocessing as mp
from queue import Empty

import numpy as np
from src.wsgr.wsgrTimer import PHASE_LABELS, timer
from src.wsgr.ship import Ship


# ---------------------------------------------------------------------------
# 并行模拟(AI supported)
#
# 每个 run_* 既可以串行运行（worker=1，与历史行为完全一致），也可以把 epoch
# 切分给多个子进程。子进程只回传"增量累加量"（delta），由主进程合并后调用本
# 文件内的 render() 打印，因此进度输出仍然由各 run_* 自己负责，main 不做输出。
#
# 战斗对象无法 pickle（装备 DSL 会在函数内部动态建类 ConfigEquipSkill），所以：
#   * fork：子进程直接继承父进程的 battle，不经过序列化；
#   * spawn（Windows）：子进程用 battle_source=(battleConfig, mapDir, dataset)
#     重新 load_config。dataset 约 0.25 MB，远好于重新解析 Excel。
# ---------------------------------------------------------------------------

MIN_PARALLEL_EPOCH = 1000    # 低于该次数不开子进程（启动开销会吃掉收益）
EPOCHS_PER_WORKER = 100      # 每个子进程至少分到的次数
PROGRESS_INTERVAL = 0.1      # 子进程两次上报之间的最长间隔（秒），保证进度行持续刷新
PROGRESS_TICKS = 100         # 每个子进程按局数计的上报次数上限


def resolve_workers(worker, epoch):
    """把并行度收敛成实际子进程数；返回 1 表示串行。"""
    try:
        worker = int(worker)
    except (TypeError, ValueError):
        worker = 1
    if worker <= 1 or epoch < MIN_PARALLEL_EPOCH:
        return 1
    return max(1, min(worker, os.cpu_count() or 1, epoch // EPOCHS_PER_WORKER))


def split_epochs(epoch, workers):
    """把 epoch 尽量均匀地切成 workers 份，返回 [(起始序号, 次数), ...]。"""
    base, extra = divmod(epoch, workers)
    plan = []
    start = 0
    for index in range(workers):
        count = base + (1 if index < extra else 0)
        if count:
            plan.append((start, count))
        start += count
    return plan


def start_method_context():
    """与 WebUI 保持一致：POSIX 优先 fork，其余平台用 spawn。"""
    if os.name != 'nt' and 'fork' in mp.get_all_start_methods():
        return mp.get_context('fork')
    return mp.get_context('spawn')


def rebuild_battle(battle_source):
    """spawn 子进程按配置重建战斗对象。

    battle_source = (battle_config, map_dir, dataset[, battle_num])
    带 battle_num 时会结算多点战斗的补给消耗，保证与单线程模拟的行为一致。
    """
    from src.utils.loadConfig import load_config   # 惰性导入，避免与加载链耦合
    battle_config, map_dir, dataset = battle_source[:3]
    battle = load_config(battle_config, map_dir, dataset, timer(), log_func=lambda _: None)
    if len(battle_source) > 3:
        set_supply(battle, battle_source[3])
    return battle


class _Metric:
    """一次 run_* 的可合并累加器：子进程回传 delta，主进程 merge 后 render。"""

    def __init__(self, battle=None):
        self.completed = 0

    def apply(self, battle):
        """跑完一次模拟并累加结果。子类可覆盖以保留各自的读取时机。"""
        battle.start()
        self.add(battle, battle.report())

    def add(self, battle, log):
        raise NotImplementedError

    def take_delta(self):
        raise NotImplementedError

    def merge(self, delta):
        raise NotImplementedError

    def render(self):
        """返回与串行模式完全相同的一行（不含首个 '\\r'）。"""
        raise NotImplementedError


class _VictoryMetric(_Metric):
    FLAGS = ['SS', 'S', 'A', 'B', 'C', 'D']

    def __init__(self, battle=None):
        self.state = [0] * 6
        self.completed = 0
        self._delta = [0] * 6

    def add(self, battle, log):
        index = self.FLAGS.index(log['result'])
        self.state[index] += 1
        self._delta[index] += 1

    def take_delta(self):
        delta, self._delta = self._delta, [0] * 6
        return delta

    def merge(self, delta):
        self.state = [total + part for total, part in zip(self.state, delta)]

    def render(self):
        result, done = self.state, self.completed
        return (f"第{done}次 - 战果分布: "
                f"SS {result[0] / done * 100:.2f}% "
                f"S {result[1] / done * 100:.2f}% "
                f"A {result[2] / done * 100:.2f}% "
                f"B {result[3] / done * 100:.2f}% "
                f"C {result[4] / done * 100:.2f}% "
                f"D {result[5] / done * 100:.2f}% ")


class _MapVictoryMetric(_Metric):
    FLAGS = ['SS', 'S', 'A', 'B', 'C', 'D', '']

    def __init__(self, battle=None):
        self.state = [0] * 8         # 0-6 战果（含撤退），7 终点旗舰击沉数
        self.completed = 0
        self._delta = [0] * 8

    def add(self, battle, log):
        if log.get('end_with_boss'):
            index = self.FLAGS.index(log['result'])
            self.state[index] += 1
            self._delta[index] += 1
            sink = int(log['damaged_state'][-1, 6] == 4)
            self.state[7] += sink
            self._delta[7] += sink
        else:
            self.state[6] += 1
            self._delta[6] += 1

    def take_delta(self):
        delta, self._delta = self._delta, [0] * 8
        return delta

    def merge(self, delta):
        self.state = [total + part for total, part in zip(self.state, delta)]

    def render(self):
        result, done = self.state, self.completed
        boss_total = done - result[6]
        sink_rate = result[7] / boss_total * 100 if boss_total > 0 else 0.0
        return (f"第{done}次 - 战果分布: "
                f"SS {result[0] / done * 100:.2f}% "
                f"S {result[1] / done * 100:.2f}% "
                f"A {result[2] / done * 100:.2f}% "
                f"B {result[3] / done * 100:.2f}% "
                f"C {result[4] / done * 100:.2f}% "
                f"D {result[5] / done * 100:.2f}% "
                f"撤退 {result[6] / done * 100:.2f}% "
                f"终点旗舰击沉率: {sink_rate:.2f}%")


class _HitRateMetric(_Metric):
    def __init__(self, battle=None, phase=None):
        self.phase = phase
        self.phase_id = next(
            (index for index, key in enumerate(PHASE_LABELS.keys()) if key == phase), None
        )
        self.total = 0.0
        self.completed = 0
        self._delta = 0.0

    def add(self, battle, log):
        if self.phase_id is not None:
            value = log['hit_rate'][self.phase_id, 1]
        else:
            value = log['hit_rate'][:, 1].mean()
        self.total += value
        self._delta += value

    def take_delta(self):
        delta, self._delta = self._delta, 0.0
        return delta

    def merge(self, delta):
        self.total += delta

    def render(self):
        return f"第{self.completed}次 - 命中率: {self.total / self.completed * 100:.4f}%"


class _AvgDamageMetric(_Metric):
    def __init__(self, battle=None, phase=None):
        self.phase = phase
        self.phase_id = next(
            (index for index, key in enumerate(PHASE_LABELS.keys()) if key == phase), None
        )
        self.samples = []
        self.avg_damage_phase = 0.0
        self.defeat_num = 0.0
        self.defeat_flag_num = 0
        self.completed = 0
        self._delta = self._empty_delta()

    @staticmethod
    def _empty_delta():
        return {
            'samples': [], 'avg_damage_phase': 0.0,
            'defeat_num': 0.0, 'defeat_flag_num': 0,
        }

    def add(self, battle, log):
        if self.phase_id is not None:
            phase_damage = float(log['create_damage'][self.phase_id, :6].sum())
            self.avg_damage_phase += phase_damage
            self._delta['avg_damage_phase'] += phase_damage
        damage = float(log['create_damage'][:, :6].sum())
        self.samples.append(damage)
        self._delta['samples'].append(damage)
        defeat = float(log['defeat_num'][:, :6].sum())
        self.defeat_num += defeat
        self._delta['defeat_num'] += defeat
        flagship = int(log['damaged_state'][-1, 6] == 4)
        self.defeat_flag_num += flagship
        self._delta['defeat_flag_num'] += flagship

    def take_delta(self):
        delta, self._delta = self._delta, self._empty_delta()
        return delta

    def merge(self, delta):
        self.samples.extend(delta['samples'])
        self.avg_damage_phase += delta['avg_damage_phase']
        self.defeat_num += delta['defeat_num']
        self.defeat_flag_num += delta['defeat_flag_num']

    def render(self):
        done = self.completed
        phase_info = ''
        if self.phase_id is not None:
            phase_info = f'{self.phase}平均伤害: {self.avg_damage_phase / done:.3f} '
        return (f"第{done}次 - 平均伤害: {np.mean(self.samples):.3f} "
                f"5%下限伤害: {int(np.percentile(self.samples, 5, method='lower')):d} "
                f"{phase_info}"
                f"平均击沉: {self.defeat_num / done:.3f} "
                f"旗舰击沉率: {self.defeat_flag_num / done * 100:.2f}%")


class _SupplyMetric(_Metric):
    KEYS = ('oil', 'ammo', 'steel', 'almn', 'repeat')

    def __init__(self, battle=None):
        self.state = dict.fromkeys(self.KEYS, 0)
        self.completed = 0
        self._delta = dict.fromkeys(self.KEYS, 0)

    def add(self, battle, log):
        for key in self.KEYS:
            value = log['supply'][key]
            self.state[key] += value
            self._delta[key] += value

    def take_delta(self):
        delta, self._delta = self._delta, dict.fromkeys(self.KEYS, 0)
        return delta

    def merge(self, delta):
        for key in self.KEYS:
            self.state[key] += delta[key]

    def render(self):
        supply, done = self.state, self.completed
        return (f"第{done}次 - 资源消耗: "
                f"油 {supply['oil'] / done:.1f}, "
                f"弹 {supply['ammo'] / done:.1f}, "
                f"钢 {supply['steel'] / done:.1f}, "
                f"铝 {supply['almn'] / done:.1f},"
                f"桶 {supply['repeat'] / done:.2f}.")


class _MapSupplyMetric(_SupplyMetric):
    """地图模拟额外汇总损管（dcitem 记在 report 顶层，不在 supply 里）。"""

    def __init__(self, battle=None):
        super().__init__(battle)
        self.state['dcitem'] = 0
        self._delta['dcitem'] = 0

    def add(self, battle, log):
        super().add(battle, log)
        value = log['dcitem']
        self.state['dcitem'] += value
        self._delta['dcitem'] += value

    def render(self):
        supply, done = self.state, self.completed
        return (f"第{done}次 - 资源消耗: "
                f"油 {supply['oil'] / done:.1f}, "
                f"弹 {supply['ammo'] / done:.1f}, "
                f"钢 {supply['steel'] / done:.1f}, "
                f"铝 {supply['almn'] / done:.1f},"
                f"桶 {supply['repeat'] / done:.2f}."
                f"损管 {supply['dcitem'] / done:.2f}.")


class _DamagedMetric(_Metric):
    def __init__(self, battle=None):
        ship_names = [ship.status['name'] for ship in battle.friend.ship]
        self.ship_names = ship_names
        self.size = len(ship_names)
        self.state = np.zeros((self.size, 2))
        self.completed = 0
        self._delta = np.zeros((self.size, 2))

    def apply(self, battle):
        # run_damaged 历史上不调用 report()：report 会把 ship.damaged 重置为 1，
        # 必须在重置前读取战损状态。
        battle.start()
        self.add(battle, None)

    def add(self, battle, log):
        for index in range(self.size):
            ship = battle.friend.ship[index]
            if ship.damaged >= 2:
                self.state[index, 0] += 1
                self._delta[index, 0] += 1
            if ship.damaged >= 3:
                self.state[index, 1] += 1
                self._delta[index, 1] += 1

    def take_delta(self):
        delta, self._delta = self._delta, np.zeros((self.size, 2))
        return delta

    def merge(self, delta):
        self.state = self.state + delta

    def render(self):
        done = self.completed
        names_str = ' '.join(self.ship_names)
        mid_str = ' '.join(f"{self.state[j, 0] / done * 100:.2f}%" for j in range(self.size))
        heavy_str = ' '.join(f"{self.state[j, 1] / done * 100:.2f}%" for j in range(self.size))
        return (f"第{done}次 - "
                f"船名: {names_str} "
                f"中破率: {mid_str} "
                f"大破率: {heavy_str} "
                f"(注：中破率包含大破率)")


def epoch_worker_entry(metric_cls, battle, battle_source, count, progress_sink,
                       shared_stop, metric_kwargs, rand_seed=None):
    """子进程入口（必须是模块级函数，spawn 才能按名字导入）。

    rand_seed 由主进程分配：fork 出来的子进程会继承同一个 numpy 随机状态，不重播种
    的话各分片会跑出完全相同的样本（有效样本数只剩 1/worker）。用主进程派生的种子既
    避免重复，又保证「在外部固定种子后整次运行可复现」。
    """
    import traceback

    # 这里的主循环由大量短 numpy 调用组成，默认 5ms 的 GIL 切换间隔会让
    # multiprocessing.Queue 的投递线程长期抢不到 GIL，进度消息要攒到进程退出才被送出
    # （表现为屏幕上数字长时间不动、最后一次性跳到终点）。缩短切换间隔后投递线程能及时
    # 送出消息；实测同时把整体吞吐提高了约 15%。
    sys.setswitchinterval(0.0005)

    try:
        if rand_seed is not None:
            np.random.seed(rand_seed)
        current = battle if battle is not None else rebuild_battle(battle_source)
        metric = metric_cls(current, **metric_kwargs)
        step = max(1, count // PROGRESS_TICKS)
        reported = 0
        reported_at = time.monotonic()
        for _ in range(count):
            if shared_stop.is_set():
                break
            current.rewind_snapshot()
            metric.apply(current)
            metric.completed += 1
            # 按局数或按时间，谁先到就上报：进度行不会因为次数多而变得半天不刷新
            now = time.monotonic()
            if now - reported_at >= PROGRESS_INTERVAL or metric.completed % step == 0:
                progress_sink.put(('delta', metric.completed - reported, metric.take_delta()))
                reported = metric.completed
                reported_at = now
        if metric.completed > reported:
            progress_sink.put(('delta', metric.completed - reported, metric.take_delta()))
        progress_sink.put(('done', metric.completed))
    except Exception:
        progress_sink.put(('error', traceback.format_exc()))


def _run_serial(metric, battle, epoch, stop_event):
    for _ in range(epoch):
        if stop_event is not None and stop_event.is_set():
            break
        battle.rewind_snapshot()
        metric.apply(battle)
        metric.completed += 1
        print('\r' + metric.render(), end='', flush=True)


def _run_parallel(metric, battle, epoch, workers, battle_source, stop_event, metric_kwargs):
    context = start_method_context()
    plan = split_epochs(epoch, workers)
    progress_sink = context.Queue()
    shared_stop = context.Event()
    # fork 时子进程直接继承 battle；spawn 时传 None，由子进程按配置重建。
    worker_battle = battle if context.get_start_method() == 'fork' else None
    # fork 会让各子进程共享同一个随机状态，必须给每个分片单独播种（由主进程派生，
    # 这样外部固定种子时整次运行仍可复现；不固定种子时主进程的状态本就来自熵）。
    worker_seeds = [int(seed) for seed in np.random.randint(0, 2 ** 32 - 1, size=len(plan))]
    processes = [
        context.Process(
            target=epoch_worker_entry,
            args=(type(metric), worker_battle, battle_source, count,
                  progress_sink, shared_stop, metric_kwargs, seed),
            daemon=True,
        )
        for (_, count), seed in zip(plan, worker_seeds)
    ]
    for process in processes:
        process.start()

    pending = len(processes)
    try:
        while pending > 0:
            if stop_event is not None and stop_event.is_set():
                shared_stop.set()
            try:
                message = progress_sink.get(timeout=0.1)
            except Empty:
                if not any(process.is_alive() for process in processes):
                    break
                continue
            if message[0] == 'delta':
                _, count, delta = message
                metric.merge(delta)
                metric.completed += count
                # 子进程已按 PROGRESS_INTERVAL 限频，这里直接渲染，保证刷新跟得上
                print('\r' + metric.render(), end='', flush=True)
            elif message[0] == 'done':
                pending -= 1
            elif message[0] == 'error':
                shared_stop.set()
                raise RuntimeError(f'并行模拟子进程失败:\n{message[1]}')
        if metric.completed:
            print('\r' + metric.render(), end='', flush=True)
    finally:
        shared_stop.set()
        for process in processes:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
        progress_sink.close()


def run_metrics(metric_cls, battle, epoch, worker=1, battle_source=None,
                stop_event=None, metric_kwargs=None):
    """串行/并行统一入口，返回合并完成的累加器。

    串行路径与历史实现逐字节一致（同样的一行、同样的刷新方式）；
    并行路径由主进程按 PROGRESS_INTERVAL 节流渲染同一行。
    """
    metric_kwargs = dict(metric_kwargs or {})
    metric = metric_cls(battle, **metric_kwargs)
    workers = resolve_workers(worker, epoch)
    if workers > 1 and start_method_context().get_start_method() != 'fork' \
            and battle_source is None:
        print('警告：当前平台无法把战斗对象交给子进程，已退回串行模拟')
        workers = 1
    if workers <= 1:
        _run_serial(metric, battle, epoch, stop_event)
    else:
        _run_parallel(metric, battle, epoch, workers, battle_source, stop_event, metric_kwargs)
    return metric


def run_victory(battle, epoch,
                stop_event:threading.Event=None,
                worker:int=1, battle_source:tuple=None):
    return run_metrics(_VictoryMetric, battle, epoch,
                       worker=worker, battle_source=battle_source,
                       stop_event=stop_event).state


def run_map_victory(battle, epoch,
                    stop_event:threading.Event=None,
                    worker:int=1, battle_source:tuple=None):
    return run_metrics(_MapVictoryMetric, battle, epoch,
                       worker=worker, battle_source=battle_source,
                       stop_event=stop_event).state


def run_hit_rate(battle, epoch, phase:str=None,
                 stop_event:threading.Event=None,
                 worker:int=1, battle_source:tuple=None):
    return run_metrics(_HitRateMetric, battle, epoch,
                       worker=worker, battle_source=battle_source,
                       stop_event=stop_event, metric_kwargs={'phase': phase}).total


def run_avg_damage(battle, epoch, phase:str=None,
                   stop_event:threading.Event=None,
                   worker:int=1, battle_source:tuple=None):
    metric = run_metrics(_AvgDamageMetric, battle, epoch,
                         worker=worker, battle_source=battle_source,
                         stop_event=stop_event, metric_kwargs={'phase': phase})
    return {
        'damage_list': metric.samples,
        'avg_damage_phase': metric.avg_damage_phase,
        'defeat_num': metric.defeat_num,
        'defeat_flag_num': metric.defeat_flag_num,
    }


def run_supply_cost(battle, epoch,
                    stop_event:threading.Event=None,
                    worker:int=1, battle_source:tuple=None):
    return run_metrics(_SupplyMetric, battle, epoch,
                       worker=worker, battle_source=battle_source,
                       stop_event=stop_event).state


def run_map_supply_cost(battle, epoch,
                        stop_event:threading.Event=None,
                        worker:int=1, battle_source:tuple=None):
    return run_metrics(_MapSupplyMetric, battle, epoch,
                       worker=worker, battle_source=battle_source,
                       stop_event=stop_event).state


def run_damaged(battle, epoch,
                stop_event:threading.Event=None,
                worker:int=1, battle_source:tuple=None):
    metric = run_metrics(_DamagedMetric, battle, epoch,
                         worker=worker, battle_source=battle_source,
                         stop_event=stop_event)
    return {'damaged_rate': metric.state, 'ship_names': metric.ship_names}


def run_battle_info(battle, *args, **kwargs):
    """战斗详报
    不论输入多少轮次，只运行一次并输出战斗细节"""
    tmp_battle = copy.deepcopy(battle)
    tmp_battle.start()
    log = tmp_battle.report()
    print(log['record'], end='',)


def new_hit_verify(value):
    """
    使用方法：
    ATK.outer_hit_verify = new_hit_verify(hit_rate)
    """
    def f(cls):
        if cls.source.side == 1:  # 只修改深海命中
            return False
        if cls.target.size != 1:
            return False

        verify = np.random.random()
        if verify <= value:
            cls.coef['hit_flag'] = True
            return True
        else:
            cls.coef['hit_flag'] = False
            return True
    return f


def set_supply(battle, battle_num):
    """设置弹损，battle_num输入第几战"""
    for ship in battle.friend.ship:
        ship.supply_oil -= 2 * (battle_num - 1)
        ship.supply_ammo -= 2 * (battle_num - 1)


def change_shiptype(ship, ShipType:type(Ship)):
    ship.__class__ = ShipType


def prebattle_info(battle):
    tmp_battle = copy.deepcopy(battle)
    tmp_battle.start()
    log = tmp_battle.report()

    # 索敌
    recon_rate = log['recon'][0]
    friend_recon = log['recon'][1]
    recon_request = log['recon'][2]
    print(f"我方索敌-{friend_recon}  "
          f"索敌要求-{recon_request}  "
          f"索敌成功率：{recon_rate:d}%")

    # 制空
    air_con_flag = log['aerial'][0]
    aerial_friend = log['aerial'][1]
    aerial_enemy = log['aerial'][2]
    air_con_info = ['空确', '空优', '均势', '劣势', '丧失']
    if air_con_flag is not None:
        print(f"我方制空-{aerial_friend:.2f}  "
              f"敌方制空-{aerial_enemy:.2f}  "
              f"制空结果：{air_con_info[air_con_flag - 1]}")
    else:
        print("未进行航空战\n")


if __name__ == '__main__':
    pass
