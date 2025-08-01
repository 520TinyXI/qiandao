import random
import datetime
from typing import Dict, Any, Tuple, List
from .database import SignDatabase

class SignManager:
    @staticmethod
    def calculate_exp_reward(continuous_days: int, level: int) -> int:
        """计算经验奖励
        Args:
            continuous_days: 连续签到天数
            level: 当前等级
        Returns:
            经验奖励值
        """
        # 基础经验奖励 (10-50)
        base_exp = random.randint(10, 50)
        
        # 等级加成 (每级增加15%)
        level_bonus = base_exp * ((level - 1) * 0.15)
        
        # 连续签到加成
        continuous_bonus = 0
        if continuous_days >= 7:
            # 连续签到7天奖励升级所需经验的3%
            continuous_bonus += SignManager._get_next_level_exp(level) * 0.03
        if continuous_days >= 30:
            # 连续签到30天获得13%
            continuous_bonus += SignManager._get_next_level_exp(level) * 0.13
        
        # 连续签到30天额外获得3%
        if continuous_days >= 30:
            continuous_bonus += SignManager._get_next_level_exp(level) * 0.03
            
        return int(base_exp + level_bonus + continuous_bonus)
    
    @staticmethod
    def calculate_coin_reward(continuous_days: int, level: int) -> int:
        """计算金币奖励
        Args:
            continuous_days: 连续签到天数
            level: 当前等级
        Returns:
            金币奖励值
        """
        # 基础金币奖励 (90-180)
        base_coins = random.randint(90, 180)
        
        # 等级加成 (每级增加15%)
        level_bonus = base_coins * ((level - 1) * 0.15)
        
        # 连续签到加成
        continuous_bonus = 0
        if continuous_days >= 7:
            # 连续签到7天奖励金币的3%
            continuous_bonus += base_coins * 0.03
        if continuous_days >= 30:
            # 连续签到30天获得13%
            continuous_bonus += base_coins * 0.13
        
        # 连续签到30天额外获得3%
        if continuous_days >= 30:
            continuous_bonus += base_coins * 0.03
            
        return int(base_coins + level_bonus + continuous_bonus)
    
    @staticmethod
    def _get_next_level_exp(level: int) -> int:
        """计算下一级所需经验
        Args:
            level: 当前等级
        Returns:
            下一级所需经验
        """
        if level == 1:
            return 200
        else:
            # 每级比上一级多20%
            return int(SignManager._get_next_level_exp(level - 1) * 1.2)
    
    @staticmethod
    def calculate_level(exp: int, current_level: int) -> Tuple[int, int]:
        """计算等级和下一级所需经验
        Args:
            exp: 当前总经验
            current_level: 当前等级
        Returns:
            (新等级, 下一级所需经验)
        """
        level = current_level
        next_level_exp = SignManager._get_next_level_exp(level)
        
        # 检查是否可以升级
        while exp >= next_level_exp:
            level += 1
            next_level_exp = SignManager._get_next_level_exp(level)
            
        return level, next_level_exp
    
    @staticmethod
    def daily_sign(user_data: Dict[str, Any], group_id: str = None) -> Dict[str, Any]:
        """每日签到
        Args:
            user_data: 用户数据
            group_id: 群组ID
        Returns:
            签到结果
        """
        if not user_data:
            user_data = {
                'total_days': 0,
                'last_sign': '',
                'continuous_days': 0,
                'exp': 0,
                'level': 1,
                'next_level_exp': 200,
                'coins': 0
            }
        
        # 计算连续签到天数
        continuous_days = 1
        today = datetime.date.today()
        last_sign = user_data.get('last_sign', '')
        
        if last_sign:
            last_sign_date = datetime.datetime.strptime(last_sign, '%Y-%m-%d').date()
            if last_sign_date == today - datetime.timedelta(days=1):
                # 昨天签到了，连续签到天数+1
                continuous_days = user_data.get('continuous_days', 0) + 1
            elif last_sign_date == today:
                # 今天已经签到了
                return None
            else:
                # 断签了，重新计算连续签到天数
                continuous_days = 1
        
        # 计算奖励
        level = user_data.get('level', 1)
        exp_reward = SignManager.calculate_exp_reward(continuous_days, level)
        coin_reward = SignManager.calculate_coin_reward(continuous_days, level)
        
        # 更新经验
        total_exp = user_data.get('exp', 0) + exp_reward
        
        # 计算新等级
        new_level, next_level_exp = SignManager.calculate_level(total_exp, level)
        
        return {
            'total_days': user_data.get('total_days', 0) + 1,
            'continuous_days': continuous_days,
            'exp': total_exp,
            'level': new_level,
            'next_level_exp': next_level_exp,
            'coins': user_data.get('coins', 0) + coin_reward,
            'exp_reward': exp_reward,
            'coin_reward': coin_reward
        }
    
    @staticmethod
    def format_sign_result(result: Dict[str, Any]) -> str:
        """格式化签到结果"""
        if not result:
            return "今天已经签到过啦~"
            
        return (
            f"签到成功！\n"
            f"获得经验：{result['exp_reward']}\n"
            f"获得金币：{result['coin_reward']}\n"
            f"当前等级：{result['level']}\n"
            f"当前经验：{result['exp']}/{result['next_level_exp']}\n"
            f"累计签到：{result['total_days']}天\n"
            f"连续签到：{result['continuous_days']}天"
        )
    
    @staticmethod
    def format_user_info(user_data: Dict[str, Any]) -> str:
        """格式化用户信息 - 移除排名信息"""
        return (
            f"个人信息\n"
            f"====================\n"
            f"等级：{user_data.get('level', 1)}\n"
            f"经验：{user_data.get('exp', 0)}/{user_data.get('next_level_exp', 200)}\n"
            f"金币：{user_data.get('coins', 0)}\n"
            f"累计签到：{user_data.get('total_days', 0)}天\n"
            f"连续签到：{user_data.get('continuous_days', 0)}天"
        )
    
    @staticmethod
    def format_my_ranking(group_total_rank: int, world_total_rank: int, 
                          continuous_rank: int, level_rank: int) -> str:
        """格式化我的排名信息"""
        return (
            f"我的排行榜\n"
            f"====================\n"
            f"本群总签到排名: 第{group_total_rank}名\n"
            f"世界总签到排名: 第{world_total_rank}名\n"
            f"连续签到排名: 第{continuous_rank}名\n"
            f"等级排名: 第{level_rank}名"
        )
    
    @staticmethod
    def format_total_ranking(ranking_data: List[tuple], db: SignDatabase = None, group_id: str = None) -> str:
        """格式化总签到排行榜"""
        result = "总签到排行榜\n"
        for i, (user_id, total_days) in enumerate(ranking_data, 1):
            # 获取用户昵称
            user_name = user_id
            if db:
                user_name = db.get_user_name(user_id, group_id) or user_id
            result += f"{i}. {user_name} - {total_days}天\n"
        return result.strip()
    
    @staticmethod
    def format_continuous_ranking(ranking_data: List[tuple], db: SignDatabase = None, group_id: str = None) -> str:
        """格式化连续签到排行榜"""
        result = "连续签到排行榜\n"
        for i, (user_id, continuous_days) in enumerate(ranking_data, 1):
            # 获取用户昵称
            user_name = user_id
            if db:
                user_name = db.get_user_name(user_id, group_id) or user_id
            result += f"{i}. {user_name} - {continuous_days}天\n"
        return result.strip()
    
    @staticmethod
    def format_level_ranking(ranking_data: List[tuple], db: SignDatabase = None, group_id: str = None) -> str:
        """格式化等级排行榜"""
        result = "等级排行榜\n"
        for i, (user_id, level, exp) in enumerate(ranking_data, 1):
            # 获取用户昵称
            user_name = user_id
            if db:
                user_name = db.get_user_name(user_id, group_id) or user_id
            result += f"{i}. {user_name} - {level}级 ({exp}经验)\n"
        return result.strip()
    
    @staticmethod
    def format_world_ranking(ranking_data: List[tuple], db: SignDatabase = None, group_id: str = None) -> str:
        """格式化世界签到排行榜"""
        result = "世界签到排行榜\n"
        for i, (user_id, total_days) in enumerate(ranking_data, 1):
            # 获取用户昵称
            user_name = user_id
            if db:
                user_name = db.get_user_name(user_id, group_id) or user_id
            result += f"{i}. {user_name} - {total_days}天\n"
        return result.strip()
    
    @staticmethod
    def buy_item(user_id: str, item_name: str, quantity: int, db: SignDatabase) -> Dict[str, Any]:
        """购买物品
        Args:
            user_id: 用户ID
            item_name: 物品名称
            quantity: 数量
            db: 数据库实例
        Returns:
            购买结果
        """
        # 检查物品价格
        item_prices = {
            "补签卡": 1000
        }
        
        if item_name not in item_prices:
            return {
                'success': False,
                'message': '该物品不存在'
            }
            
        price = item_prices[item_name]
        total_cost = price * quantity
        
        # 检查用户金币
        user_data = db.get_user_data(user_id)
        if not user_data or user_data.get('coins', 0) < total_cost:
            return {
                'success': False,
                'message': '金币不足'
            }
            
        # 扣除金币
        db.update_user_data(user_id, coins=user_data['coins'] - total_cost)
        
        # 更新背包
        db.update_inventory(user_id, item_name, quantity)
        
        return {
            'success': True,
            'cost': total_cost
        }
    
    @staticmethod
    def resign(user_id: str, days: int, group_id: str, db: SignDatabase) -> Dict[str, Any]:
        """补签
        Args:
            user_id: 用户ID
            days: 补签天数
            group_id: 群组ID
            db: 数据库实例
        Returns:
            补签结果
        """
        # 检查补签卡数量
        inventory = db.get_user_inventory(user_id)
        card_count = inventory.get('补签卡', 0)
        
        if card_count < days:
            return {
                'success': False,
                'message': '补签卡数量不足'
            }
            
        # 检查是否可以补签（前三天内）
        today = datetime.date.today()
        user_data = db.get_user_data(user_id)
        last_sign = user_data.get('last_sign', '') if user_data else ''
        
        if not last_sign:
            return {
                'success': False,
                'message': '您还没有签到过，无法补签'
            }
            
        last_sign_date = datetime.datetime.strptime(last_sign, '%Y-%m-%d').date()
        
        # 检查前三天是否有未签到的日期
        missing_days = []
        for i in range(1, 4):
            check_date = today - datetime.timedelta(days=i)
            if check_date > last_sign_date:
                missing_days.append(check_date)
                
        if len(missing_days) < days:
            return {
                'success': False,
                'message': '没有足够的未签到日期可以补签'
            }
            
        # 按顺序补签
        coins_spent = 0
        for i in range(days):
            if i >= len(missing_days):
                break
                
            # 补签一天的奖励（按最低奖励计算）
            level = user_data.get('level', 1) if user_data else 1
            exp_reward = 10  # 最低经验奖励
            coin_reward = 90  # 最低金币奖励
            
            # 等级加成
            exp_reward += int(exp_reward * (level - 1) * 0.15)
            coin_reward += int(coin_reward * (level - 1) * 0.15)
            
            # 更新用户数据
            total_exp = (user_data.get('exp', 0) if user_data else 0) + exp_reward
            new_level, next_level_exp = SignManager.calculate_level(total_exp, level)
            
            user_data = {
                'total_days': (user_data.get('total_days', 0) if user_data else 0) + 1,
                'last_sign': missing_days[i].strftime('%Y-%m-%d'),
                'continuous_days': 1,  # 补签不计算连续签到
                'exp': total_exp,
                'level': new_level,
                'next_level_exp': next_level_exp,
                'coins': (user_data.get('coins', 0) if user_data else 0) + coin_reward,
                'group_id': group_id
            }
            
            # 更新数据库
            db.update_user_data(user_id, **user_data)
            db.log_sign(user_id, exp_reward, coin_reward)
            
            coins_spent += coin_reward
            
        # 扣除补签卡
        db.update_inventory(user_id, '补签卡', -days)
        
        return {
            'success': True,
            'cost': days,
            'coins': coins_spent
        }
    
    @staticmethod
    def format_inventory(inventory: Dict[str, int]) -> str:
        """格式化背包信息"""
        if not inventory:
            return "背包是空的"
            
        result = "背包\n"
        for item_name, quantity in inventory.items():
            result += f"{item_name}: {quantity}张\n"
        return result.strip()