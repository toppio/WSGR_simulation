# -*- coding:utf-8 -*-
# Author:银河远征(Edited at 20260922)
# env:py38
# 列克星敦（cv-2)改-1、萨拉托加改-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""全阶段自身及编队相邻舰船的舰载机威力提高25%。
两艘持有该技能的舰船同时在队伍里时，自身舰载机威力和命中率提高25%，
攻击时降低敌方100%对空值（不包含装备）。"""


class Skill_110291_1(Skill):
    """全阶段自身及编队相邻舰船的舰载机威力提高25%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = NearestLocTarget(
            side=1,
            master=master,
            radius=1,
            direction='near',
            master_include=True,
            shiptype=Aircraft
        )

        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_atk_buff',
                phase=AllPhase,
                value=0.25,
                bias_or_weight=2
            )
        ]


class Skill_110291_2(Skill):
    """两艘持有该技能的舰船同时在队伍里时，自身舰载机威力和命中率提高25%，
    攻击时降低敌方100%对空值（不包含装备）。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_atk_buff',
                phase=AllPhase,
                value=0.25,
                bias_or_weight=2
            ),
            CoeffBuff(
                timer=timer,
                name='hit_rate',
                phase=AllPhase,
                value=0.25,
                bias_or_weight=0
            ),
            AtkBuff(
                timer=timer,
                name='ignore_antiair',
                phase=AllPhase,
                value=-1,
                bias_or_weight=1
            )
        ]

    def is_active(self, friend, enemy):
        sis_list = CidTarget(
            side=1,
            cid_list=['10029', '11029', '10030', '11030']
        ).get_target(friend, enemy)

        if self.master not in sis_list:  # master不是列克星敦改或萨拉托加改（让巴尔复制）
            return False

        sis_list.remove(self.master)
        if len(sis_list) == 0:  # 队伍内不同时存在列克星敦和萨拉托加
            return False

        # 队伍内只要还有至少一艘舰船同时使用本技能即可
        return any(type(tmp_skill).__module__ == type(self).__module__
                   for sister in sis_list
                   for tmp_skill in sister.skill)


name = '航空战术先驱'
skill = [Skill_110291_1, Skill_110291_2]
