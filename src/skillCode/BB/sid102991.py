# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 让巴尔-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""
Lv.1: 降低自身30%被攻击概率。
Lv.2: 战斗中随机选择我方任意一艘自身以外的中、大型船，获得其技能（战斗外增加属性效果及演习内战斗不生效）。
Lv.3:如果这个技能包含有概率发动的效果，则变为100%发动。
"""


class Skill_102991_1(Skill):
    """降低自身30%被攻击概率。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            UnMagnetBuff(
                timer=timer,
                phase=AllPhase,
                rate=0.3
            )
        ]


class Skill_102991_2(PrepSkill):
    """战斗中随机选择我方任意一艘自身以外的中、大型船，获得其技能
    如果这个技能包含有概率发动的效果，则变为100%发动。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.copy_skill = []  # 复制来的普通技能(每节点重算，见 activate)

    def activate(self, friend, enemy):
        # 清除上一战斗节点复制的技能
        for tmp_skill in self.copy_skill:
            if tmp_skill in self.master.skill:
                self.master.skill.remove(tmp_skill)
        self.copy_skill = []

        # 自身以外的中、大型船
        mid_large = TypeTarget(
            side=1,
            shiptype=(MidShip, LargeShip)
        ).get_target(friend, enemy)
        if self.master in mid_large:
            mid_large.remove(self.master)
        if not len(mid_large):  # 队伍中不存在自身以外的中、大型船
            return

        target = np.random.choice(mid_large)
        _skill = target.get_raw_skill()  # 获得其技能
        for skillClass in _skill:
            tmp_skill = skillClass(self.timer, self.master)
            if tmp_skill.is_end_skill():  # 结束阶段技能不复制
                continue
            tmp_skill.change_rate(1)  # 变为100%发动
            if tmp_skill.is_prep():
                # 准备阶段技能(buff在准备阶段结算)，直接发动
                if tmp_skill.is_active(friend, enemy):
                    tmp_skill.activate(friend, enemy)
            else:
                # 普通技能交由其自身阶段(buff阶段)结算，此时航向等信息已确定
                self.master.skill.append(tmp_skill)
                self.copy_skill.append(tmp_skill)


name = '旁观者'
skill = [Skill_102991_1, Skill_102991_2]
