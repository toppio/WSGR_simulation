# -*- coding:utf-8 -*-
# Author:huan_yp
# env:py38
# 鲃鱼

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""首轮炮击阶段敌方要塞、机场、港口无法行动。先制鱼雷阶段自身60%概率额外发射一枚鱼雷"""


class Skill_114081_1(Skill):
    """首轮炮击阶段敌方要塞、机场、港口无法行动"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=0, shiptype=LandUnit)
        self.buff = [
            ActPhaseBuff(
                timer=timer,
                name='not_act_phase',
                phase=FirstShellingPhase,
            )
        ]
class Skill_114081_2(Skill):
    def __init__(self, timer, master):
        """先制鱼雷阶段自身60%概率额外发射一枚鱼雷"""
        self.target = SelfTarget(master=master, side=1)
        self.buff = [
            MultipleAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=FirstTorpedoPhase,
                num=2,
                rate=.6,
            )
        ]
skill = [Skill_114081_1,]

