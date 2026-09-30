# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# I-400&I-402

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""若敌方索敌失败，自身可发动远程打击。开幕鱼雷攻击必定命中，无视护甲，被本舰开幕鱼雷命中并造成伤害的单位昼战阶段无法行动。"""


class Skill_030121(Skill):
    """开幕鱼雷攻击必定命中，无视护甲，被本舰开幕鱼雷命中并造成伤害的单位昼战阶段无法行动。"""

    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)

        self.buff = [
            SpecialBuff(
                timer=timer,
                name='must_hit',
                phase=FirstTorpedoPhase
            ),
            AtkHitBuff(
                timer=timer,
                name='atk_hit',
                phase=FirstTorpedoPhase,
                buff=[
                    ActPhaseBuff(
                        timer=timer,
                        name='not_act_phase',
                        phase=DaytimePhase
                    )
                ],
                side=0
            )
        ]


name = '海军法典的试炼-碧&桃'
skill = [Skill_030121]

