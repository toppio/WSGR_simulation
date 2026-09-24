# -*- coding: utf-8 -*-
# Author:银河远征(Edited at 20260922)
# env:py38
# 重庆-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from src.wsgr.formulas import AirAtk

"""自身免疫受到的航空攻击伤害。
编队中每有1艘C国舰船，都会增加自身20点制空值、15点火力值、10点回避值和5点命中值。"""


class Skill_110541_1(Skill):
    """自身免疫受到的航空攻击伤害。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_debuff',
                phase=AllPhase,
                value=-1,
                atk_request=[BuffRequest_1]
            )
        ]


class BuffRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk, AirAtk)


class Skill_110541_2(Skill):
    """编队中每有1艘C国舰船，都会增加自身20点制空值、15点火力值、10点回避值和5点命中值。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_ctrl_buff',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=10,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            )
        ]

    def activate(self, friend, enemy):
        count = len(CountryTarget(side=1, country='C'
                                  ).get_target(friend, enemy))
        if count == 0:
            return
        target = self.target.get_target(friend, enemy)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_buff.value *= count
                tmp_target.add_buff(tmp_buff)


name = '防空伪装'
skill = [Skill_110541_1, Skill_110541_2]
