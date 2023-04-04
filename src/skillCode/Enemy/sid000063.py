# -*- coding:utf-8 -*-
# Author:KS Mist*
# env:py38
# 深海大和（雾化）

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""无视战损。炮击战阶段受到伤害后，免疫下一次受到的伤害。每一个阶段开始时，免疫本阶段受到的第一次伤害（支援阶段与炮击战除外）。"""


class Skill_000063(Skill):
    """无视战损。炮击战中，受到伤害后，为自身提供一个可抵御一次攻击的护盾。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            SpecialBuff(
                timer=timer,
                name='ignore_damaged',
                phase=FirstShellingPhase
            ),
            SpecialBuff(
                timer=timer,
                name='shield',
                phase=AirPhase,
                exhaust=1),
            SpecialBuff(
                timer=timer,
                name='shield',
                phase=FirstMissilePhase,
                exhaust=1),
            SpecialBuff(
                timer=timer,
                name='shield',
                phase=FirstTorpedoPhase,
                exhaust=1),
            SpecialBuff(
                timer=timer,
                name='shield',
                phase=SecondTorpedoPhase,
                exhaust=1),
            SpecialBuff(
                timer=timer,
                name='shield',
                phase=SecondMissilePhase,
                exhaust=1),
            SpecialBuff(
                timer=timer,
                name='shield',
                phase=NightPhase,
                exhaust=1),
            AtkHitBuff(
                timer=timer,
                name='atk_be_hit',
                phase=ShellingPhase,
                buff=[
                    SpecialBuff(
                        timer=timer,
                        name='shield',
                        phase=AllPhase,
                        exhaust=1)
                ],
                side=1  # 这里side填0还是1
            )
        ]


name = '逆转反击·克莱因力场'
skill = [Skill_000063]

