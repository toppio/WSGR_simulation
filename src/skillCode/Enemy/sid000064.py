# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 超重力炮·重巡

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""炮击战50%概率触发超重力炮攻击，对1-3个目标造成100%的伤害（大破无法触发）。"""


class Skill_000064(Skill):
    """炮击战50%概率触发超重力炮攻击，对1-3个目标造成100%的伤害（大破无法触发）。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            GravityAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=(ShellingPhase, NightPhase),
                num=3,
                rate=0.5
            )
        ]


class GravityAtkBuff(MultipleAtkBuff):
    """随机对n个目标发动攻击，且大破状态下不发动"""
    def active_start(self, atk, enemy, *args, **kwargs):
        assert self.master is not None
        def_list = enemy.get_atk_target(atk_type=atk)
        assert len(def_list)
        self.add_during_buff()  # 攻击时效果

        attacknum = np.random.randint(1, self.num+1)
        for i in range(attacknum):
            if not len(def_list):
                break

            tmp_atk = atk(
                timer=self.timer,
                atk_body=self.master,
                def_list=def_list,
                coef=copy.copy(self.coef),
            )
            tmp_target = tmp_atk.target_init()
            def_list.remove(tmp_target)
            yield tmp_atk

        self.remove_during_buff()  # 去除攻击时效果
        self.add_end_buff()  # 攻击结束效果

    def is_active(self, atk, enemy, *args, **kwargs):
        # if isinstance(enemy, list):
        #     def_list = enemy
        # elif isinstance(enemy, Fleet):
        #     def_list = enemy.get_atk_target(atk_type=atk)
        # else:
        #     raise TypeError('Enemy should be in form of list or Fleet')
        if self.master.damaged >= 3:  # 大破状态不能发动
            return False

        def_list = enemy.get_atk_target(atk_type=atk)
        return len(def_list) and \
               self.rate_verify() and \
               isinstance(self.timer.phase, self.phase)


name = '超重力炮·重巡'
skill = [Skill_000064]

