# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 21工程-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""全队舰船火力值增加自身火力值的8%，全队S国舰船火力值再额外增加自身火力值的8%。
自身炮击战阶段40%概率同时攻击2个目标，队伍中每有1艘S国舰船都会增加10%发动概率。"""


class Skill_106411_1(Skill):
    """全队舰船火力值增加自身火力值的8%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=0.08,
                bias_or_weight=0
            )
        ]

    def activate(self, friend, enemy):
        fire = self.master.get_final_status('fire')  # 获取自身的火力值
        target = self.target.get_target(friend, enemy)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_buff.value *= fire
                tmp_target.add_buff(tmp_buff)


class Skill_106411_2(Skill):
    """全队S国舰船火力值再额外增加自身火力值的8%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CountryTarget(side=1, country='S')
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=0.08,
                bias_or_weight=0
            )
        ]

    def activate(self, friend, enemy):
        fire = self.master.get_final_status('fire')  # 获取自身的火力值
        target = self.target.get_target(friend, enemy)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_buff.value *= fire
                tmp_target.add_buff(tmp_buff)


class Skill_106411_3(Skill):
    """自身炮击战阶段40%概率同时攻击2个目标，
    队伍中每有1艘S国舰船都会增加10%发动概率。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            MultipleAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=ShellingPhase,
                num=2,
                rate=0.4
            )
        ]

    def activate(self, friend, enemy):
        num = len(CountryTarget(side=1, country='S'
                                ).get_target(friend, enemy))
        buff_0 = copy.copy(self.buff[0])
        buff_0.rate += 0.1 * num
        self.master.add_buff(buff_0)


name = '炮台守望'
skill = [Skill_106411_1, Skill_106411_2, Skill_106411_3]
