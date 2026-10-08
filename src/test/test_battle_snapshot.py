# -*- coding: utf-8 -*-
# Author:银河远征(Agent supported)
# env:py38

"""战斗状态复位（mark_snapshot/rewind_snapshot，替代每局 copy.deepcopy）的回归测试。

覆盖四类断言：
1. rewind_snapshot() 后对象图必须与「刚 load_config 完」逐字段一致；
2. 固定种子下 deepcopy 版与 reset 版的战报序列逐位相同；
3. 连跑多局后技能模板 / 常驻 buff / 环境技能不得累积；
4. 类属性与模块级可变全局不得被就地修改。

注：固定种子只用于测试；正式运行由 WebUI 侧 np.random.seed(None) 取随机种子。
"""

import copy
import importlib
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.loadConfig import load_yaml, load_config
from src.utils.loadDataset import Dataset
from src.utils.runUtil import set_supply
from src.wsgr.wsgrTimer import timer

MAP_DIR = os.path.join(ROOT, 'depend/map')
DATASET_PATH = os.path.join(ROOT, 'depend/ship/database.xlsx')
SEED = 20240601
SKIP_KEYS = ('timer', 'master', '_snapshot')


def freeze(value, depth=0, seen=None):
    """把状态递归转成可比较结构；跳过 timer/master 反向引用以免成环。"""
    if seen is None:
        seen = set()
    if isinstance(value, (int, float, bool, str)) or value is None:
        return value
    if isinstance(value, np.ndarray):
        return ('ndarray', value.shape, value.tobytes())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return ('list', [freeze(item, depth + 1, seen) for item in value])
    if isinstance(value, (set, frozenset)):
        return ('set', sorted(repr(freeze(item, depth + 1, seen)) for item in value))
    if isinstance(value, dict):
        return ('dict', sorted((str(key), freeze(item, depth + 1, seen))
                               for key, item in value.items()))
    if depth > 4:
        return ('deep', type(value).__qualname__)
    if id(value) in seen:
        return ('cycle', type(value).__qualname__)
    seen = seen | {id(value)}
    if hasattr(value, '__dict__'):
        return ('obj', type(value).__qualname__,
                {key: freeze(item, depth + 1, seen)
                 for key, item in vars(value).items() if key not in SKIP_KEYS})
    return ('other', type(value).__qualname__)


def dump_state(battle):
    """战斗对象（含海图）的可比较状态快照。"""
    state = {'timer': freeze(battle.timer),
             'friend': [freeze(ship) for ship in battle.friend.ship]}
    if hasattr(battle, 'enemy'):
        state['enemy'] = [freeze(ship) for ship in battle.enemy.ship]
    else:
        # 海图：MapUtil 自身的配置字段也须保持初始值；节点只比较需要保持不变的字段
        # —— round_request 与 battle 是每次访问都会重写的临时字段，刻意不做复位。
        state['map'] = freeze({key: value for key, value in vars(battle).items()
                               if key not in ('point', 'friend', 'timer', '_snapshot')})
        state['points'] = sorted(
            (name, freeze({key: value for key, value in vars(point).items()
                           if key not in ('user_rules', 'battle', 'round_request')}))
            for name, point in battle.point.items()
        )
    return state


def report_signature(log):
    """一局战报的完整签名（数组取字节、其余取结构化 repr）。"""
    return {key: value.tobytes() if isinstance(value, np.ndarray) else repr(value)
            for key, value in log.items()}


class EpochResetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = Dataset(DATASET_PATH)
        cls.single_config = load_yaml(os.path.join(ROOT, 'config', 'config_test.yaml'), MAP_DIR)

    def build(self, config=None, mapid=None):
        config = copy.deepcopy(config if config is not None else self.single_config)
        if mapid is not None:
            config['map'] = {'mapid': mapid}
            config.pop('user_rules', None)
        battle = load_config(config, MAP_DIR, self.dataset, timer(), log_func=lambda _: None)
        set_supply(battle, 1)
        return battle

    def build_map(self, mapid='normal/2-1'):
        return self.build(load_yaml(os.path.join(ROOT, 'config', 'config_map_test.yaml'), MAP_DIR),
                          mapid=mapid)

    # ---- 断言 1：复位后与初始状态一致 -------------------------------------
    def test_reset_restores_pristine_state(self):
        for label, battle in (('单点', self.build()), ('地图', self.build_map())):
            with self.subTest(target=label):
                battle.rewind_snapshot()          # 与真实循环一致：开局先复位
                pristine = dump_state(battle)
                for round_index in range(3):
                    battle.start()
                    battle.report()
                    battle.rewind_snapshot()
                    self.assertEqual(
                        pristine, dump_state(battle),
                        f'{label} 第 {round_index + 1} 轮复位后与初始状态不一致')
                    # 复位必须彻底到「还能被 deepcopy」：战斗中产生的动态类型实例
                    # （如 ConfigEffectType）如果残留，这里会直接抛错。
                    copy.deepcopy(battle)

    # ---- 断言 1b：首次调用只记录、不复位 --------------------------------
    def test_first_rewind_only_records(self):
        """首次调用时对象本就是初始状态，不必刷新时统或回滚自身。"""
        battle = self.build()
        log_before = battle.timer.log
        battle.rewind_snapshot()                     # 首次：只记快照
        self.assertIs(battle.timer.log, log_before, '首次调用不该刷新时统')
        battle.start()
        battle.report()
        log_after_battle = battle.timer.log
        battle.rewind_snapshot()                     # 之后：真正复位
        self.assertIsNot(battle.timer.log, log_after_battle, '复位应当刷新时统')

    # ---- 断言 2：固定种子下与 deepcopy 版逐位相同 --------------------------
    def _sequence(self, battle, epoch, use_deepcopy):
        np.random.seed(SEED)
        signatures = []
        for _ in range(epoch):
            if use_deepcopy:
                current = copy.deepcopy(battle)
            else:
                battle.rewind_snapshot()
                current = battle
            current.start()
            signatures.append(report_signature(current.report()))
        return signatures

    def _assert_sequences_equal(self, label, battle, epoch):
        reference = self._sequence(battle, epoch, True)
        candidate = self._sequence(battle, epoch, False)
        self.assertEqual(len(reference), len(candidate))
        for index, (expected, actual) in enumerate(zip(reference, candidate)):
            self.assertEqual(
                expected, actual,
                f'{label} 第 {index + 1} 局：reset 版与 deepcopy 版战报不一致')

    def test_single_battle_reset_matches_deepcopy(self):
        self._assert_sequences_equal('单点', self.build(), 30)

    def test_map_battle_reset_matches_deepcopy(self):
        self._assert_sequences_equal('地图', self.build_map(), 15)

    # ---- 断言 3：技能模板等不得累积 ---------------------------------------
    def test_skill_template_and_buff_do_not_accumulate(self):
        battle = self.build()
        battle.rewind_snapshot()
        initial = {
            'skill': [len(ship._skill) for ship in battle.friend.ship],
            'common': [len(ship.common_buff) for ship in battle.friend.ship],
            'env': len(battle.timer.env_skill),
        }
        for _ in range(12):
            battle.start()
            battle.report()
        battle.rewind_snapshot()
        self.assertEqual(initial['skill'], [len(ship._skill) for ship in battle.friend.ship],
                         '技能模板 _skill 被消费后没有还原')
        self.assertEqual(initial['common'], [len(ship.common_buff) for ship in battle.friend.ship],
                         '常驻 buff 数量发生变化')
        self.assertEqual(initial['env'], len(battle.timer.env_skill),
                         '环境技能列表在 epoch 之间累积')

    # ---- 断言 3b：战术模板不得被就地改写 ---------------------------------
    def test_strategy_instances_are_never_mutated(self):
        """战术是纯模板：`Strategy.activate()` 注册进 `strategy_buff` 的是
        `copy.copy(self.buff[0])` 的副本，战斗中的 is_active/activate/change_value
        都作用在副本上，因此战术实例本身不应被任何就地改写触碰（这正是它不需要
        参与每局复位的原因）。"""
        battle = self.build()
        battle.rewind_snapshot()
        before = [freeze(strategy) for ship in battle.friend.ship for strategy in ship.strategy]
        self.assertTrue(before, '该配置应至少带一个战术，否则这条断言没有意义')
        for epoch in range(3):
            battle.start()
            after = [freeze(strategy) for ship in battle.friend.ship for strategy in ship.strategy]
            self.assertEqual(before, after, f'第 {epoch + 1} 局战术实例被就地改写了')
            battle.report()
            battle.rewind_snapshot()

    # ---- 断言 4：类属性 / 模块级全局不得被就地修改 -------------------------
    def test_no_class_or_module_level_state_leak(self):
        battle = self.build()
        classes = sorted({cls for ship in battle.friend.ship for cls in ship._skill}
                         | {base for ship in battle.friend.ship for cls in ship._skill
                            for base in type(cls).__mro__ if base.__module__.startswith('src')},
                         key=lambda cls: cls.__qualname__)

        def class_state():
            return {
                cls.__qualname__: {
                    key: (len(value) if isinstance(value, (list, dict, set)) else value)
                    for key, value in vars(cls).items()
                    if not callable(value) and not isinstance(value, (staticmethod, classmethod, property))
                }
                for cls in classes
            }

        modules = ('src.wsgr.ship', 'src.wsgr.skill', 'src.wsgr.formulas',
                   'src.wsgr.phase', 'src.wsgr.wsgrTimer', 'src.utils.envBuffUtil')

        def module_state():
            state = {}
            for name in modules:
                module = importlib.import_module(name)
                for key, value in vars(module).items():
                    if isinstance(value, (list, dict, set)) and not key.startswith('__'):
                        state[f'{name}.{key}'] = len(value)
            return state

        before_classes, before_modules = class_state(), module_state()
        battle.rewind_snapshot()
        battle.start()
        battle.report()
        self.assertEqual(before_classes, class_state(), '存在类级属性被就地修改')
        self.assertEqual(before_modules, module_state(), '存在模块级可变全局被修改')

        # 同一种子、各自从初始状态开跑两次，结果必须完全一致（不借助 deepcopy）
        self.assertEqual(
            self._sequence(battle, 2, False), self._sequence(battle, 2, False),
            '两次独立运行结果不一致，说明存在跨局状态泄漏')


if __name__ == '__main__':
    unittest.main()
