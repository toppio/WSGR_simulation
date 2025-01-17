# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38

import copy
import numpy as np

def run_hit_rate(battle, epoc):
    hit_rate = 0
    for i in range(epoc):
        tmp_battle = copy.deepcopy(battle)
        tmp_battle.start()
        log = tmp_battle.report()

        hit_rate += log['hit_rate']
        print("\r"
              f"第{i + 1}次 - 命中率: {hit_rate / (i + 1) * 100: .4f}%",
              end='',)


def run_avg_damage(battle, epoc):
    avg_damage = 0
    retreat_num = 0
    for i in range(epoc):
        tmp_battle = copy.deepcopy(battle)
        tmp_battle.start()
        log = tmp_battle.report()

        avg_damage += np.sum(log['create_damage'][1])
        retreat_num += log['enemy_retreat_num']
        print("\r"
              f"第{i + 1}次 - 平均伤害: {avg_damage / (i + 1):.3f}; "
              f"平均击沉 {retreat_num / (i + 1):.2f}",
              end='',)


def run_supply_cost(battle, epoc):
    supply = {'oil': 0, 'ammo': 0, 'steel': 0, 'almn': 0}
    for i in range(epoc):
        tmp_battle = copy.deepcopy(battle)
        tmp_battle.start()
        log = tmp_battle.report()

        supply['oil'] += log['supply']['oil']
        supply['ammo'] += log['supply']['ammo']
        supply['steel'] += log['supply']['steel']
        supply['almn'] += log['supply']['almn']
        print("\r"
              f"第{i + 1}次 - 资源消耗: "
              f"油 {supply['oil'] / (i + 1):.1f}, "
              f"弹 {supply['ammo'] / (i + 1):.1f}, "
              f"钢 {supply['steel'] / (i + 1):.1f}, "
              f"铝 {supply['almn'] / (i + 1):.1f}.",
              end='',)


def run_damaged(battle, epoc):
    damaged_rate = np.zeros((6, 2))
    for i in range(epoc):
        tmp_battle = copy.deepcopy(battle)
        tmp_battle.start()
        for j in range(6):
            ship = tmp_battle.friend.ship[j]
            if ship.damaged >= 2:
                damaged_rate[j, 0] += 1
            if ship.damaged >= 3:
                damaged_rate[j, 1] += 1
        print(f"\r第{i + 1}次 "
              f"{tmp_battle.friend.ship[0].status['name']}: "
              f"中破率 {damaged_rate[0, 0] / (i + 1) * 100:.2f}% "
              f"大破率 {damaged_rate[0, 1] / (i + 1) * 100:.2f}% "
              f"{tmp_battle.friend.ship[1].status['name']}: "
              f"中破率 {damaged_rate[1, 0] / (i + 1) * 100:.2f}% "
              f"大破率 {damaged_rate[1, 1] / (i + 1) * 100:.2f}% "
              f"{tmp_battle.friend.ship[2].status['name']}: "
              f"中破率 {damaged_rate[2, 0] / (i + 1) * 100:.2f}% "
              f"大破率 {damaged_rate[2, 1] / (i + 1) * 100:.2f}% "
              f"{tmp_battle.friend.ship[3].status['name']}: "
              f"中破率 {damaged_rate[3, 0] / (i + 1) * 100:.2f}% "
              f"大破率 {damaged_rate[3, 1] / (i + 1) * 100:.2f}% "
              f"{tmp_battle.friend.ship[4].status['name']}: "
              f"中破率 {damaged_rate[4, 0] / (i + 1) * 100:.2f}% "
              f"大破率 {damaged_rate[4, 1] / (i + 1) * 100:.2f}% "
              f"{tmp_battle.friend.ship[5].status['name']}: "
              f"中破率 {damaged_rate[5, 0] / (i + 1) * 100:.2f}% "
              f"大破率 {damaged_rate[5, 1] / (i + 1) * 100:.2f}% ",
              end='',)


def new_hit_verify(value):
    def f(cls):
        if cls.atk_body.side == 1:  # 只修改深海命中
            return False
        if cls.target.size != 1:
            return False

        verify = np.random.random()
        if verify <= value:
            cls.coef['hit_flag'] = True
            return True
        else:
            cls.coef['hit_flag'] = False
            return True
    return f


def set_supply(battle, battle_num):
    """设置弹损，battle_num输入第几战"""
    for ship in battle.friend.ship:
        ship.supply_oil -= 0.2 * (battle_num - 1)
        ship.supply_ammo -= 0.2 * (battle_num - 1)


if __name__ == '__main__':
    pass
