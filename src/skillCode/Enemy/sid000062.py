# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 深海大和

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""无视战损。炮击战中，受到伤害后，为自身提供一个可抵御一次攻击的护盾。"""


class Skill_000062(Skill):
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
            AtkHitBuff(
                timer=timer,
                name='get_atk',
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


name = '逆转反击'
skill = [Skill_000062]

