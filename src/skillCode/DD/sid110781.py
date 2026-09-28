# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# Z24改-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""自身鱼雷值的40%视为火力值。
炮击战阶段自身命中率提高18%，30%概率同时攻击2个目标，
队伍中每有1艘Z驱都会增加10%发动概率。"""


class Skill_110781_1(Skill):
    """自身鱼雷值的40%视为火力值。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBasedBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=0.4,
                bias_or_weight=0,
                base='torpedo'
            )
        ]


class Skill_110781_2(Skill):
    """炮击战阶段自身命中率提高18%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='hit_rate',
                phase=ShellingPhase,
                value=0.18,
                bias_or_weight=0
            )
        ]


class Skill_110781_3(Skill):
    """炮击战阶段30%概率同时攻击2个目标，
    队伍中每有1艘Z驱都会增加10%发动概率。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            SkillMultiAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=ShellingPhase,
                num=2,
                rate=0.3
            )
        ]

    def activate(self, friend, enemy):
        buff_0 = copy.copy(self.buff[0])
        target_z = TagTarget(side=1, tag='z-ship').get_target(friend, enemy)
        buff_0.rate += 0.1 * len(target_z)
        self.master.add_buff(buff_0)


class SkillMultiAtkBuff(MultipleAtkBuff):
    """对2个目标发动攻击，可分别选择反潜目标和炮击目标"""
    def active_start(self, atk: ATK, enemy: Fleet, *args, **kwargs):
        assert self.master is not None
        self.add_during_buff()  # 攻击时效果

        first_target = None
        for i in range(self.num):
            atk = self.raise_atk(enemy, first_target)
            if atk is None:
                break
            first_target = atk.target_init()  # 设定初始目标(挡枪判定前)
            yield atk

        self.remove_during_buff()  # 去除攻击时效果
        self.add_end_buff()  # 攻击结束效果

    def raise_atk(self, target_fleet: Fleet, first_target) -> ATK:
        """通过技能代码重构Z24炮击战逻辑
        同时具备反潜和炮击能力，优先反潜"""
        atk = None

        # 优先反潜
        if self.master.check_anti_sub():
            def_list = target_fleet.get_atk_target(
                atk_type=self.master.anti_sub_atk)
            if first_target is not None and first_target in def_list:
                def_list.remove(first_target)  # 移除第一次攻击目标
            if len(def_list):
                atk = self.master.anti_sub_atk(
                    timer=self.timer,
                    source=self.master,
                    def_list=def_list,
                    coef=self.coef
                )

        # 普通炮击
        if atk is None:  # 无反潜
            def_list = target_fleet.get_atk_target(
                atk_type=self.master.normal_atk)
            if first_target is not None and first_target in def_list:
                def_list.remove(first_target)  # 移除第一次攻击目标
            if len(def_list):
                atk = self.master.normal_atk(
                    timer=self.timer,
                    source=self.master,
                    def_list=def_list,
                    coef=self.coef
                )

        return atk  # 当技能发动时只剩一个目标存活，第二次攻击判定可能生成None


name = '示警炮击'
skill = [Skill_110781_1, Skill_110781_2, Skill_110781_3]
