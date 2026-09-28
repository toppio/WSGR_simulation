# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 伊丽莎白女王-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""队伍中每有1艘E国舰船，都会增加全队舰船4点火力值和命中值，提高全队E国舰船4%暴击率。
队伍中存在E国小型船时，全队舰船火力值和回避值增加10点；
队伍中存在E国中型船时，全队舰船火力值和装甲值增加10点；
队伍中只存在E国舰船时，全队E国舰船攻击威力和暴击伤害提高15%。"""


class Skill_106441_1(Skill):
    """队伍中每有1艘E国舰船，都会增加全队舰船4点火力值和命中值。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=4,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=4,
                bias_or_weight=0
            )
        ]

    def activate(self, friend, enemy):
        num_e = len(CountryTarget(side=1, country='E'
                                  ).get_target(friend, enemy))
        target = self.target.get_target(friend, enemy)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_buff.value *= num_e
                tmp_target.add_buff(tmp_buff)


class Skill_106441_2(Skill):
    """队伍中每有1艘E国舰船，都会提高全队E国舰船4%暴击率。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CountryTarget(side=1, country='E')
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.04,
                bias_or_weight=0
            )
        ]

    def activate(self, friend, enemy):
        num_e = len(CountryTarget(side=1, country='E'
                                  ).get_target(friend, enemy))
        target = self.target.get_target(friend, enemy)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_buff.value *= num_e
                tmp_target.add_buff(tmp_buff)


class Skill_106441_3(Skill):
    """队伍中存在E国小型船时，全队舰船火力值和回避值增加10点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
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
                name='evasion',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            )
        ]

    def is_active(self, friend, enemy):
        target = CombinedTarget(
            side=1,
            target_list=[CountryTarget(side=1, country='E'),
                         TypeTarget(side=1, shiptype=SmallShip)]
        ).get_target(friend, enemy)
        return len(target) > 0


class Skill_106441_4(Skill):
    """队伍中存在E国中型船时，全队舰船火力值和装甲值增加10点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
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
            )
        ]

    def is_active(self, friend, enemy):
        target = CombinedTarget(
            side=1,
            target_list=[CountryTarget(side=1, country='E'),
                         TypeTarget(side=1, shiptype=MidShip)]
        ).get_target(friend, enemy)
        return len(target) > 0


class Skill_106441_5(Skill):
    """队伍中只存在E国舰船时，全队E国舰船攻击威力和暴击伤害提高15%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CountryTarget(side=1, country='E')
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='power_buff',
                phase=AllPhase,
                value=0.15,
                bias_or_weight=2
            ),
            CoeffBuff(
                timer=timer,
                name='crit_coef',
                phase=AllPhase,
                value=0.15,
                bias_or_weight=0
            )
        ]

    def is_active(self, friend, enemy):
        if isinstance(friend, Fleet):
            friend = friend.ship
        return all(tmp_ship.status['country'] == 'E' for tmp_ship in friend)


name = '女王'
skill = [Skill_106441_1, Skill_106441_2, Skill_106441_3, Skill_106441_4, Skill_106441_5]
