# -*- coding:utf-8 -*-
# Author:zzhh225
# Edited by: 银河远征(20260922)
# env:py38
# 光辉-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""先驱首战(3级)：提升自身所携带的鱼雷机鱼雷值5点。
全队航母、装母、轻母命中值和回避值增加15点，炮击战阶段攻击威力提高20%。
夜战阶段自身可进行攻击，攻击必定暴击且不受耐久损失影响。"""


class Skill_103701_1(CommonSkill):
    """提升自身所携带的鱼雷机鱼雷值5点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = EquipTarget(
            side=1,
            target=SelfTarget(master),
            equiptype=DiveBomber
        )
        self.buff = [
            CommonBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            )
        ]


class Skill_103701_2(Skill):
    """全队航母、装母、轻母命中值和回避值增加15点，炮击战阶段攻击威力提高20%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1, shiptype=(CV, CVL, AV))
        self.buff = [
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='power_buff',
                phase=ShellingPhase,
                value=0.2,
                bias_or_weight=2
            )
        ]


class Skill_103701_3(Skill):
    """夜战阶段自身可进行攻击，攻击必定暴击且不受耐久损失影响。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            ActPhaseBuff(
                timer=timer,
                name='act_phase',
                phase=NightPhase,
            ),
            SpecialBuff(
                timer=timer,
                name='must_crit',
                phase=NightPhase
            ),
            SpecialBuff(
                timer=timer,
                name='ignore_damaged',
                phase=NightPhase
            ),
        ]


name = '先驱首战'
skill = [Skill_103701_1, Skill_103701_2, Skill_103701_3]
