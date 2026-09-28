# -*- coding:utf-8 -*-
# Author:zzhh225
# Edited by: 银河远征(20260922)
# env:py38
# 希佩尔海军上将-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""当敌方存在小型船时，自身装甲值增加40点，火力值、鱼雷值和回避值增加20点。
自身优先攻击小型船，攻击小型船时必定命中且伤害提高30%。"""


class Skill_110361_1(Skill):
    """当敌方存在小型船时，自身装甲值增加40点，火力值、鱼雷值和回避值增加20点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=40,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            )
        ]

    def is_active(self, friend, enemy):
        target = TypeTarget(side=0, shiptype=SmallShip
                            ).get_target(friend, enemy)
        return len(target)


class Skill_110361_2(Skill):
    """自身优先攻击小型船，攻击小型船时必定命中且伤害提高30%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            PriorTargetBuff(
                timer=timer,
                name='prior_type_target',
                phase=AllPhase,
                target=TypeTarget(side=0, shiptype=SmallShip),
                ordered=False
            ),
            SpecialBuff(
                timer=timer,
                name='must_hit',
                phase=AllPhase,
                atk_request=[ATKRequest_1]
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.3,
                atk_request=[ATKRequest_1]
            )
        ]


class ATKRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, SmallShip)


name = '伪装奇袭'
skill = [Skill_110361_1, Skill_110361_2]
