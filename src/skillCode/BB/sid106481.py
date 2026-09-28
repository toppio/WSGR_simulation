# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 阿尔汉格尔斯克-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""全队索敌值提高5点。
自身和全队小型船命中值和回避值增加20点，造成的伤害提高20%。
全队E国和S国舰船造成的伤害提高30%。
当队伍中只有E国和S国舰船时，战斗中我方航向只会出现T优势和同航战。"""


class Skill_106481_1(PrepSkill):
    """全队索敌值提高5点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='recon',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            )
        ]


class Skill_106481_2(Skill):
    """自身和全队小型船命中值和回避值增加20点，造成的伤害提高20%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1, shiptype=SmallShip)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='accuracy',
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
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.2
            )
        ]

    def activate(self, friend, enemy):
        target = self.target.get_target(friend, enemy)  # 全队小型船
        if self.master not in target:  # 加上自身
            target.append(self.master)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_target.add_buff(tmp_buff)


class Skill_106481_3(Skill):
    """全队E国和S国舰船造成的伤害提高30%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CountryTarget(side=1, country=('E', 'S'))
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.3
            )
        ]


class Skill_106481_4(PrepSkill):
    """当队伍中只有E国和S国舰船时，战斗中我方航向只会出现T优势和同航战。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            SpecialBuff(
                timer=timer,
                name='direction_limit',
                phase=AllPhase
            )
        ]

    def is_active(self, friend, enemy):
        if isinstance(friend, Fleet):
            friend = friend.ship
        return all(tmp_ship.status['country'] in ('E', 'S')
                   for tmp_ship in friend)


name = '协同援护'
skill = [Skill_106481_1, Skill_106481_2, Skill_106481_3, Skill_106481_4]
