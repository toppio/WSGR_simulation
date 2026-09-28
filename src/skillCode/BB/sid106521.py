# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 俄亥俄-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""全队大型船火力值和装甲值增加15点，U国大型船再额外提高15%暴击率和暴击伤害。
全队蒙大拿级舰船攻击威力不会因耐久损伤而降低。
当蒙大拿存在于队伍中时，首轮炮击阶段，俄亥俄同时攻击3个目标，该次攻击必中且提高30%伤害。"""


class Skill_106521_1(Skill):
    """全队大型船火力值和装甲值增加15点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1, shiptype=LargeShip)
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


class Skill_106521_2(Skill):
    """U国大型船再额外提高15%暴击率和暴击伤害。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CombinedTarget(
            side=1,
            target_list=[CountryTarget(side=1, country='U'),
                         TypeTarget(side=1, shiptype=LargeShip)]
        )
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.15,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit_coef',
                phase=AllPhase,
                value=0.15,
                bias_or_weight=0
            )
        ]


class Skill_106521_3(Skill):
    """全队蒙大拿级舰船攻击威力不会因耐久损伤而降低。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TagTarget(side=1, tag='montana')
        self.buff = [
            SpecialBuff(
                timer=timer,
                name='ignore_damaged',
                phase=AllPhase
            )
        ]


class Skill_106521_4(Skill):
    """当蒙大拿存在于队伍中时，首轮炮击阶段，俄亥俄同时攻击3个目标，
    该次攻击必中且提高30%伤害。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            MultipleAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=FirstShellingPhase,
                num=3,
                rate=1,
                coef={'must_hit': True,
                      'final_damage_buff': 0.3}
            )
        ]

    def is_active(self, friend, enemy):
        # 仅俄亥俄可用(防止让巴尔复制技能)
        if self.master.cid not in ['10652', '11652']:
            return False
        # 队伍中存在蒙大拿
        montana = CidTarget(side=1, cid_list=['10520', '11520']
                            ).get_target(friend, enemy)
        return len(montana) > 0


name = '重装合击'
skill = [Skill_106521_1, Skill_106521_2, Skill_106521_3, Skill_106521_4]
