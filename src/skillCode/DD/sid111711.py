# -*- coding:utf-8 -*-
# Author:huan_yp
# env:py38
# Z46

from src.wsgr.formulas import TorpedoAtk
from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""在先制鱼雷、鱼雷战、夜战降低己方所受到 65% 的鱼雷伤害，
降低我方旗舰 18% 被攻击概率，
鱼雷战阶段命中敌方主力舰时造成20%的额外伤害"""


class Skill_111711_1(Skill):
    """在先制鱼雷、鱼雷战、夜战降低己方所受到 65% 的鱼雷伤害，
    """
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = LocTarget(side=1, loc=[1, 2, 3, 4, 5, 6])
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_debuff',
                phase=AllPhase,
                value=-0.65,
                atk_request=[ATK_Request1]
            ),
        ]


class Skill_111711_2(Skill):
    """降低我方旗舰 18% 被攻击概率
    """
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = LocTarget(side=1, loc=[1])
        self.buff = [
            UnMagnetBuff(
                timer,
                phase=AllPhase,
                rate=.18
            )
        ]

class Skill_111711_3(Skill):
    """鱼雷战阶段命中敌方主力舰时造成20%的额外伤害
    """
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                value=.2,
                atk_request=[ATK_Request2]
            )
        ]

class ATK_Request1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk, TorpedoAtk)
        
class ATK_Request2(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, MainShip)

name = '驱逐先锋'
skill = [Skill_111711_1, Skill_111711_2, Skill_111711_3]
