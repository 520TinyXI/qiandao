import random
import datetime
from typing import Dict, Any, List, Tuple
from .database import SignDatabase

class CastleManager:
    # 城堡升级所需经验和金币
    CASTLE_UPGRADE_COSTS = {
        1: {"exp": 10000, "coins": 10000},
        2: {"exp": 30000, "coins": 26000},
        3: {"exp": 80000, "coins": 80000},
        4: {"exp": 120000, "coins": 150000},
    }
    
    # 城堡增益效果
    CASTLE_BUFFS = {
        1: {"exp_bonus": 0.002, "coin_range": (98, 189)},
        2: {"exp_bonus": 0.01, "coin_range": (158, 211)},
        3: {"exp_bonus": 0.018, "coin_range": (180, 258)},
        4: {"exp_bonus": 0.018, "coin_range": (210, 298)},
        5: {"exp_bonus": 0.018, "coin_range": (210, 298)},
    }
    
    @staticmethod
    def get_castle_exp_gain() -> int:
        """获取城堡经验随机增长"""
        return random.randint(15, 35)
    
    @staticmethod
    def format_castle_info(castle_data: Dict[str, Any], db: SignDatabase) -> str:
        """格式化城堡信息"""
        if not castle_data:
            return "该群聊还没有建造城堡哦~"
        
        # 获取领主和总管的昵称
        lord_name = "无"
        if castle_data['lord_id']:
            lord_name = db.get_user_name(castle_data['lord_id']) or castle_data['lord_id']
        
        manager_names = []
        for manager_id in castle_data['managers']:
            manager_name = db.get_user_name(manager_id) or manager_id
            manager_names.append(manager_name)
        
        managers_str = "、".join(manager_names) if manager_names else "无"
        
        # 获取城堡增益信息
        buff_info = ""
        if castle_data['level'] in CastleManager.CASTLE_BUFFS:
            buff = CastleManager.CASTLE_BUFFS[castle_data['level']]
            buff_info = f"经验加成: {buff['exp_bonus']*100:.1f}% 金币范围: {buff['coin_range'][0]}-{buff['coin_range'][1]}"
        
        return (
            f"【{castle_data['castle_name']}】\n"
            f"====================\n"
            f"城堡编号: {castle_data['castle_id']}\n"
            f"城堡等级: {castle_data['level']}级\n"
            f"城堡经验: {castle_data['exp']}\n"
            f"金币池: {castle_data['coins']}金币\n"
            f"成员人数: {len(castle_data['members'])}人\n"
            f"领主: {lord_name}\n"
            f"总管: {managers_str}\n"
            f"增益效果: {buff_info}"
        )
    
    @staticmethod
    def format_castle_ranking(ranking_data: List[tuple]) -> str:
        """格式化城堡等级排行榜"""
        if not ranking_data:
            return "城堡等级排行榜\n暂无城堡数据"
        
        result = "城堡等级排行榜\n"
        for i, (castle_id, castle_name, level, exp) in enumerate(ranking_data, 1):
            result += f"{i}. 【{castle_name}】 - {level}级 ({exp}经验)\n"
        return result.strip()
    
    @staticmethod
    def format_castle_coin_ranking(ranking_data: List[tuple]) -> str:
        """格式化城堡金币排行榜"""
        if not ranking_data:
            return "城堡金币排行榜\n暂无城堡数据"
        
        result = "城堡金币排行榜\n"
        for i, (castle_id, castle_name, coins) in enumerate(ranking_data, 1):
            result += f"{i}. 【{castle_name}】 - {coins}金币\n"
        return result.strip()
    
    @staticmethod
    def get_buffed_rewards(base_exp: int, base_coin_range: Tuple[int, int], castle_level: int) -> Tuple[int, int]:
        """根据城堡等级获取增益后的奖励"""
        if castle_level not in CastleManager.CASTLE_BUFFS:
            return base_exp, random.randint(*base_coin_range)
        
        buff = CastleManager.CASTLE_BUFFS[castle_level]
        
        # 计算经验奖励（带增益）
        exp_reward = int(base_exp * (1 + buff['exp_bonus']))
        
        # 计算金币奖励（带增益）
        coin_reward = random.randint(*buff['coin_range'])
        
        return exp_reward, coin_reward