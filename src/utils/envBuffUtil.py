# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 环境加成

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *


class AllTarget(Target):
    """针对双方全体(可指定筛选类型)"""

    def __init__(self, side=None, target: Target = None):
        super().__init__(side)
        self.target = target

    def get_target(self, friend, enemy):
        if self.target is not None:
            target_1 = self.target.get_target(friend, enemy)
            target_0 = self.target.get_target(enemy, friend)
            return target_1 + target_0
        else:
            if isinstance(friend, Fleet):
                friend = friend.ship
            if isinstance(enemy, Fleet):
                enemy = enemy.ship
            return friend + enemy


class EnvSkill_1(Skill):
    """猪飞：大型船伤害+60%"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=LargeShip)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.6
            )
        ]


class EnvSkill_2(Skill):
    """猪飞：中型船伤害+60%"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=MidShip)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.1,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.6
            )
        ]


class EnvSkill_3(Skill):
    """猪飞：小型船伤害+60%"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=SmallShip)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.1,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.6
            )
        ]


class EnvSkill_4(Skill):
    """航巡全阶段必中"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=CAV)
        self.buff = [
            SpecialBuff(
                timer=timer,
                name='must_hit',
                phase=AllPhase
            )
        ]

# 以下buff为通过情报局购买的海雾压制词条
class BuffRequest_FogDD(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, (DD, ASDG)) and \
               self.atk.target.status['tag'] == 'fog'

class EnvSkill_AtkFogDDMustHit(Skill):
    """以海雾驱逐、导驱为攻击目标时必中"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = Target(side=1)
        self.buff = [
            SpecialBuff(
                timer=timer,
                name='must_hit',
                phase=AllPhase,
                atk_request=[BuffRequest_FogDD]
            )
        ]

class EnvSkill_PriorAtkFogDD(Skill):
    """全阶段优先攻击海雾驱逐、导驱"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = Target(side=1)

        self.buff = [
            PriorTargetBuff(
                timer=timer,
                name='prior_type_target',
                phase=AllPhase,
                target=CombinedTarget(
                    side=0,
                    target_list=[TypeTarget(side=0, shiptype=(DD, ASDG)),
                                 TagTarget(side=0, tag='fog')]
                ),
                ordered=False
            )
        ]

class EnvSkill_AtkFogDDDmgBuff(Skill):
    """以海雾驱逐、导驱为攻击目标时造成的伤害增加40%"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = Target(side=1)
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.4,
                atk_request=[BuffRequest_FogDD]
            )
        ]

class EnvSkill_FogDDHitDebuff(Skill):
    """降低海雾驱逐、导驱40%命中率"""

    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = CombinedTarget(
                    side=0,
                    target_list=[TypeTarget(side=0, shiptype=(DD, ASDG)),
                                 TagTarget(side=0, tag='fog')])

        self.buff = [
            CoeffBuff(
                timer=timer,
                name='hit_rate',
                phase=AllPhase,
                value=-0.4,
                bias_or_weight=0
            )
        ]

env = [EnvSkill_AtkFogDDMustHit]
