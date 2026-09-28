# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 密西西比改-2

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from src.wsgr.equipment import Missile

"""自身携带的导弹装备增加10点火力值。
全队U国大型船火力值和装甲值增加15点。
全队导战、防战、大巡回避率和护甲穿透提高20%。
闭幕导弹和夜战阶段，全队舰船伤害提高20%，防战和大巡伤害额外提高20%。"""


class Skill_116022_1(CommonSkill):
    """自身携带的导弹装备增加10点火力值。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = EquipTarget(
            side=1,
            target=SelfTarget(master),
            equiptype=Missile
        )
        self.buff = [
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            )
        ]


class Skill_116022_2(Skill):
    """全队U国大型船火力值和装甲值增加15点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CombinedTarget(
            side=1,
            target_list=[
                CountryTarget(side=1, country='U'),
                TypeTarget(side=1, shiptype=LargeShip)
            ]
        )
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            )
        ]


class Skill_116022_3(Skill):
    """全队导战、防战、大巡回避率和护甲穿透提高20%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1, shiptype=(BBG, BG, CBG))
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='miss_rate',
                phase=AllPhase,
                value=0.2,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='pierce_coef',
                phase=AllPhase,
                value=0.2,
                bias_or_weight=0
            )
        ]


class Skill_116022_4(Skill):
    """闭幕导弹和夜战阶段，全队舰船伤害提高20%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=(SecondMissilePhase, NightPhase),
                value=0.2
            )
        ]


class Skill_116022_5(Skill):
    """闭幕导弹和夜战阶段，防战和大巡伤害额外提高20%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1, shiptype=(BG, CBG))
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=(SecondMissilePhase, NightPhase),
                value=0.2
            )
        ]


name = '换装试航'
skill = [Skill_116022_1, Skill_116022_2, Skill_116022_3,
         Skill_116022_4, Skill_116022_5]
