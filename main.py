# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38

import os
import sys
import copy
import numpy as np

curDir = os.path.dirname(__file__)
srcDir = os.path.join(curDir, 'src')
sys.path.append(srcDir)

from src.utils.loadConfig import load_config
from src.utils.loadDataset import Dataset
from src.utils.runUtil import *
from src.wsgr.wsgrTimer import timer
from src.wsgr.formulas import *

def run_victory(battle, epoc):
    result = [0] * 6
    result_flag_list = ['SS', 'S', 'A', 'B', 'C', 'D']
    for i in range(epoc):
        tmp_battle = copy.deepcopy(battle)
        tmp_battle.start()
        log = tmp_battle.report()

        result_flag_id = result_flag_list.index(log['result'])
        result[result_flag_id] += 1
        print("\r"
              f"第{i + 1}次 - 战果分布: "
              f"SS {result[0] / (i + 1) * 100:.2f}% "
              f"S {result[1] / (i + 1) * 100:.2f}% "
              f"A {result[2] / (i + 1) * 100:.2f}% "
              f"B {result[3] / (i + 1) * 100:.2f}% "
              f"C {result[4] / (i + 1) * 100:.2f}% "
              f"D {result[5] / (i + 1) * 100:.2f}% ",
              end='',)
              # flush=True)
    # result = np.array(result)
    # result = result / epoc * 100
    # return result


if __name__ == '__main__':
    configDir = os.path.join(os.path.dirname(srcDir), 'config')
    # xml_file = os.path.join(configDir, r'config.xml') # 跑单例
    xml_file = os.path.join(configDir, r'config_map.xml') # 跑全图
    dependDir = os.path.join(os.path.dirname(srcDir), 'depend')
    data_file = os.path.join(dependDir, r'ship\database.xlsx')
    ds = Dataset(data_file)  # 舰船数据

    mapDir = os.path.join(dependDir, r'map')
    timer_init = timer()  # 创建时钟
    battle = load_config(xml_file, mapDir, ds, timer_init)
    del ds

    # set_supply(battle, 4)
    # for accuracy in np.arange(100, 201, 50):
    #     print(f"accuracy: {accuracy}")
    #     for ship in battle.enemy.ship:
    #         ship.status['accuracy'] = accuracy
    run_victory(battle, 1)      # 跑胜率
    # run_avg_damage(battle, 10000)
    # for hit_rate in np.arange(0.5, 1, 0.05):
    #     hit_rate = np.round(hit_rate, 2)
    #     print(f"hit_rate: {hit_rate}")
    #     NormalAtk.outer_hit_verify = new_hit_verify(hit_rate)
    #     run_damaged(battle, 1000)
