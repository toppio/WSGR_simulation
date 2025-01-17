# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# G14-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""海平面突袭：队伍中每有1艘J国舰船都会增加自身6%的舰载机威力。
首轮炮击战阶段40%概率同时攻击两个目标且必定命中，队伍中每有1艘装甲航母都会增加15%发动概率"""


class Skill_105101(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.buff = [
            CoeffBuff(
                timer=self.timer,
                name='air_atk_buff',
                phase=(AllPhase,),
                value=0.06,
                bias_or_weight=2
            ),
            MultipleAtkBuff(
                timer=self.timer,
                name='multi_attack',
                phase=FirstShellingPhase,
                num=2,
                rate=0.4,
                coef={'must_hit': True}
            )
        ]

    def activate(self, friend, enemy):
        # 队伍中每有1艘J国舰船都会增加自身6%的舰载机威力
        buff_0 = copy.copy(self.buff[0])
        target_j = CountryTarget(side=1, country='J').get_target(friend, enemy)  # 获取J国
        buff_0.value *= len(target_j)
        self.master.add_buff(buff_0)

        # 队伍中每有1艘装甲航母都会增加15%发动概率
        buff_1 = copy.copy(self.buff[1])
        target_av = TypeTarget(side=1, shiptype=AV).get_target(friend, enemy)  # 获取装母
        buff_1.rate = min(1., buff_1.rate + 0.15 * len(target_av))
        self.master.add_buff(buff_1)


name = '海平面突袭'
skill = [Skill_105101]
