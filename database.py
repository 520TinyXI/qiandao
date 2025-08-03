import sqlite3
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# 创建简单的logger替代astrbot.api.logger
class SimpleLogger:
    def error(self, msg):
        print(f"ERROR: {msg}")
    
    def info(self, msg):
        print(f"INFO: {msg}")

logger = SimpleLogger()

class SignDatabase:
    def __init__(self, plugin_dir: str):
        db_dir = os.path.join(plugin_dir, "plugins_db")
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.db_path = os.path.join(db_dir, "astrbot_plugin_advanced_sign.db")
        self.init_db()
        
    def init_db(self):
        """初始化数据库连接和表结构"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 创建所需的表
        tables = [
            '''CREATE TABLE IF NOT EXISTS sign_data (
                user_id TEXT PRIMARY KEY,
                total_days INTEGER DEFAULT 0,
                last_sign TEXT DEFAULT '',
                continuous_days INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                next_level_exp INTEGER DEFAULT 200,
                coins INTEGER DEFAULT 0,
                group_id TEXT DEFAULT ''
            )''',
            '''CREATE TABLE IF NOT EXISTS sign_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id TEXT,
                exp INTEGER,
                coins INTEGER,
                sign_date TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS inventory (
                user_id TEXT,
                item_name TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, item_name)
            )''',
            '''CREATE TABLE IF NOT EXISTS user_names (
                user_id TEXT PRIMARY KEY,
                user_name TEXT,
                group_id TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS user_titles (
                user_id TEXT,
                title TEXT,
                acquired_date TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, title)
            )''',
            '''CREATE TABLE IF NOT EXISTS castle_data (
                castle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT UNIQUE,
                castle_name TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                lord_id TEXT,
                managers TEXT DEFAULT '[]',
                members TEXT DEFAULT '[]',
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        
        for table in tables:
            self.cursor.execute(table)
        self.conn.commit()

    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户数据"""
        self.cursor.execute('SELECT * FROM sign_data WHERE user_id = ?', (user_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['user_id', 'total_days', 'last_sign', 'continuous_days', 'exp', 'level', 'next_level_exp', 'coins', 'group_id']
        return dict(zip(columns, row))

    def update_user_data(self, user_id: str, **kwargs):
        """更新用户数据"""
        # 确保包含群组信息
        if 'group_id' not in kwargs:
            # 尝试获取现有群组信息
            existing_data = self.get_user_data(user_id)
            if existing_data and existing_data.get('group_id'):
                kwargs['group_id'] = existing_data['group_id']
                
        if not self.get_user_data(user_id):
            self.cursor.execute('INSERT INTO sign_data (user_id) VALUES (?)', (user_id,))
            
        update_fields = []
        values = []
        for key, value in kwargs.items():
            update_fields.append(f"{key} = ?")
            values.append(value)
        values.append(user_id)
        
        sql = f"UPDATE sign_data SET {', '.join(update_fields)} WHERE user_id = ?"
        self.cursor.execute(sql, values)
        self.conn.commit()
        
    def update_user_name(self, user_id: str, user_name: str, group_id: str = None):
        """更新用户昵称"""
        # 检查是否已存在（基于user_id，忽略group_id）
        self.cursor.execute('SELECT user_id FROM user_names WHERE user_id = ?', (user_id,))
        if self.cursor.fetchone():
            # 如果用户已存在，更新其昵称和群组ID
            self.cursor.execute('UPDATE user_names SET user_name = ?, group_id = ? WHERE user_id = ?', 
                              (user_name, group_id, user_id))
        else:
            # 如果用户不存在，插入新记录
            self.cursor.execute('INSERT INTO user_names (user_id, user_name, group_id) VALUES (?, ?, ?)', 
                              (user_id, user_name, group_id))
        self.conn.commit()
        
    def get_user_name(self, user_id: str, group_id: str = None) -> str:
        """获取用户昵称 - 添加缓存逻辑"""
        # 优先从user_names表获取
        if group_id:
            self.cursor.execute('SELECT user_name FROM user_names WHERE user_id = ? AND group_id = ?',
                              (user_id, group_id))
        else:
            self.cursor.execute('SELECT user_name FROM user_names WHERE user_id = ?', (user_id,))
        
        row = self.cursor.fetchone()
        if row:
            return row[0]
        
        # 如果没有记录，返回用户ID
        return user_id

    def log_sign(self, user_id: str, exp: int, coins: int):
        """记录签到历史"""
        self.cursor.execute(
            'INSERT INTO sign_history (user_id, exp, coins, sign_date) VALUES (?, ?, ?, ?)',
            (user_id, exp, coins, datetime.now().strftime('%Y-%m-%d'))
        )
        self.conn.commit()
        
    def get_user_inventory(self, user_id: str) -> Dict[str, int]:
        """获取用户背包"""
        self.cursor.execute('SELECT item_name, quantity FROM inventory WHERE user_id = ?', (user_id,))
        rows = self.cursor.fetchall()
        return {row[0]: row[1] for row in rows}
        
    def update_inventory(self, user_id: str, item_name: str, quantity: int):
        """更新用户背包"""
        # 检查是否已存在
        self.cursor.execute('SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?', (user_id, item_name))
        row = self.cursor.fetchone()
        if row:
            new_quantity = row[0] + quantity
            if new_quantity <= 0:
                self.cursor.execute('DELETE FROM inventory WHERE user_id = ? AND item_name = ?', (user_id, item_name))
            else:
                self.cursor.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?', 
                                  (new_quantity, user_id, item_name))
        elif quantity > 0:
            self.cursor.execute('INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)', 
                              (user_id, item_name, quantity))
        self.conn.commit()
        

    def get_continuous_sign_ranking(self, limit: int = 10) -> List[tuple]:
        """获取连续签到排行榜（全局）
        按连续签到次数降序排列，次数相同的按照先来后到排序
        """
        self.cursor.execute('''
            SELECT sd.user_id, un.user_name, sd.continuous_days 
            FROM sign_data sd
            LEFT JOIN user_names un ON sd.user_id = un.user_id
            ORDER BY sd.continuous_days DESC, sd.last_sign ASC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
        
    def get_level_ranking(self, limit: int = 10) -> List[tuple]:
        """获取等级排行榜（全局）"""
        self.cursor.execute('''
            SELECT sd.user_id, un.user_name, sd.level, sd.exp
            FROM sign_data sd
            LEFT JOIN user_names un ON sd.user_id = un.user_id
            ORDER BY sd.level DESC, sd.exp DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
        
    def get_world_sign_ranking(self, limit: int = 10) -> List[tuple]:
        """获取世界签到排行榜
        按总签到次数降序排列，次数相同则按当天签到时间早的排前面
        """
        self.cursor.execute('''
            SELECT sd.user_id, un.user_name, sd.total_days
            FROM sign_data sd
            LEFT JOIN user_names un ON sd.user_id = un.user_id
            ORDER BY sd.total_days DESC, sd.last_sign ASC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
        
    def get_continuous_sign_rank(self, user_id: str) -> int:
        """获取连续签到排名（修复版）"""
        # 获取当前用户的连续签到天数
        self.cursor.execute('SELECT continuous_days FROM sign_data WHERE user_id = ?', (user_id,))
        user_continuous_days = self.cursor.fetchone()
        if not user_continuous_days:
            return 0
        user_continuous_days = user_continuous_days[0]
        
        # 计算比当前用户连续签到天数多的用户数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM sign_data 
            WHERE continuous_days > ? 
        ''', (user_continuous_days,))
        row = self.cursor.fetchone()
        
        # 计算与当前用户相同天数但更早签到的用户数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM sign_data sd1
            JOIN sign_history sh1 ON sd1.user_id = sh1.user_id
            WHERE sd1.continuous_days = ? 
            AND sh1.timestamp < (
                SELECT sh2.timestamp FROM sign_history sh2
                WHERE sh2.user_id = ?
                ORDER BY sh2.timestamp DESC LIMIT 1
            )
        ''', (user_continuous_days, user_id))
        same_days_row = self.cursor.fetchone()
        
        return (row[0] if row else 0) + (same_days_row[0] if same_days_row else 0) + 1
        
    def get_group_sign_rank(self, group_id: str, user_id: str) -> int:
        """获取群内签到排名（修复版）"""
        # 如果没有群组ID，则返回世界排名
        if not group_id:
            return self.get_world_sign_rank(user_id)
        
        # 获取当前用户的总签到天数
        self.cursor.execute('SELECT total_days FROM sign_data WHERE user_id = ?', (user_id,))
        user_total_days = self.cursor.fetchone()
        if not user_total_days:
            return 0
        user_total_days = user_total_days[0]
        
        # 计算群内比当前用户签到天数多的用户数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM sign_data 
            WHERE group_id = ? AND total_days > ? 
        ''', (group_id, user_total_days))
        row = self.cursor.fetchone()
        
        return row[0] + 1 if row else 1  # 排名 = 比自己多的用户数 + 1
        
    def get_world_sign_rank(self, user_id: str) -> int:
        """获取世界签到排名（修复版）"""
        # 获取当前用户的总签到天数
        self.cursor.execute('SELECT total_days FROM sign_data WHERE user_id = ?', (user_id,))
        user_total_days = self.cursor.fetchone()
        if not user_total_days:
            return 0
        user_total_days = user_total_days[0]
        
        # 计算比当前用户签到天数多的用户数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM sign_data 
            WHERE total_days > ? 
        ''', (user_total_days,))
        row = self.cursor.fetchone()
        
        # 计算与当前用户相同天数但更早签到的用户数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM sign_data sd1
            JOIN sign_history sh1 ON sd1.user_id = sh1.user_id
            WHERE sd1.total_days = ? 
            AND sh1.timestamp < (
                SELECT sh2.timestamp FROM sign_history sh2
                WHERE sh2.user_id = ?
                ORDER BY sh2.timestamp DESC LIMIT 1
            )
        ''', (user_total_days, user_id))
        same_days_row = self.cursor.fetchone()
        
        return (row[0] if row else 0) + (same_days_row[0] if same_days_row else 0) + 1
        
    def close(self):
        """关闭数据库连接"""

        self.conn.close()
        
    def add_user_title(self, user_id: str, title: str):
        """为用户添加称号"""
        try:
            self.cursor.execute(
                'INSERT OR IGNORE INTO user_titles (user_id, title) VALUES (?, ?)', 
                (user_id, title)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加用户称号失败: {str(e)}")
            return False
            
    def get_user_titles(self, user_id: str) -> List[tuple]:
        """获取用户的所有称号"""
        self.cursor.execute('SELECT title, is_active FROM user_titles WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()
        
    def activate_title(self, user_id: str, title: str):
        """激活用户称号"""
        self.cursor.execute(
            'UPDATE user_titles SET is_active = 1 WHERE user_id = ? AND title = ?', 
            (user_id, title)
        )
        self.conn.commit()
        
    def deactivate_all_titles(self, user_id: str):
        """取消激活用户的所有称号"""
        self.cursor.execute(
            'UPDATE user_titles SET is_active = 0 WHERE user_id = ?', 
            (user_id,)
        )
        self.conn.commit()
        
    def get_active_title(self, user_id: str) -> str:
        """获取用户当前激活的称号"""
        self.cursor.execute(
            'SELECT title FROM user_titles WHERE user_id = ? AND is_active = 1', 
            (user_id,)
        )
        row = self.cursor.fetchone()
        return row[0] if row else ""

    def get_castle_by_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据群组ID获取城堡信息"""
        self.cursor.execute('SELECT * FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['castle_id', 'group_id', 'castle_name', 'level', 'exp', 'coins', 'lord_id', 'managers', 'members', 'created_date']
        result = dict(zip(columns, row))
        
        # 解析JSON字段
        try:
            result['managers'] = json.loads(result['managers'])
        except:
            result['managers'] = []
            
        try:
            result['members'] = json.loads(result['members'])
        except:
            result['members'] = []
            
        return result
    
    def get_castle_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡等级排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, level, exp
            FROM castle_data
            ORDER BY level DESC, exp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_coin_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡金币排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, coins
            FROM castle_data
            ORDER BY coins DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def check_castle_name_exists(self, castle_name: str) -> bool:
        """检查城堡名称是否已存在"""
        self.cursor.execute('SELECT castle_id FROM castle_data WHERE castle_name = ?', (castle_name,))
        return self.cursor.fetchone() is not None
    
    def get_castle_id_by_group(self, group_id: str) -> Optional[int]:
        """根据群组ID获取城堡编号"""
        self.cursor.execute('SELECT castle_id FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    def create_castle(self, group_id: str, castle_name: str, creator_id: str, participant_ids: List[str] = None) -> bool:
        """创建城堡，创建人和5个参与用户自动加入城堡"""
        try:
            # 初始化成员列表，包含创建者和参与者
            members = [creator_id]
            if participant_ids:
                # 限制最多5个参与者
                members.extend(participant_ids[:5])
            
            self.cursor.execute('''
                INSERT INTO castle_data (group_id, castle_name, members) 
                VALUES (?, ?, ?)
            ''', (group_id, castle_name, json.dumps(members)))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"创建城堡失败: {str(e)}")
            return False
    
    def join_castle(self, group_id: str, user_id: str) -> bool:
        """加入城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否已经是成员
            if user_id in castle['members']:
                return False
            
            # 添加用户到成员列表
            castle['members'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET members = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            return False
    
    def leave_castle(self, group_id: str, user_id: str) -> bool:
        """退出城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 从成员列表中移除用户
            castle['members'].remove(user_id)
            
            # 如果是领主，清空领主ID
            if castle['lord_id'] == user_id:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, lord_id = NULL 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            # 如果是总管，从总管列表中移除
            elif user_id in castle['managers']:
                castle['managers'].remove(user_id)
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, managers = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), json.dumps(castle['managers']), group_id))
            else:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"退出城堡失败: {str(e)}")
            return False
    
    def upgrade_castle(self, group_id: str, exp_cost: int, coin_cost: int) -> bool:
        """升级城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查资源是否足够
            if castle['exp'] < exp_cost or castle['coins'] < coin_cost:
                return False
            
            # 扣除资源并升级
            new_level = castle['level'] + 1
            new_exp = castle['exp'] - exp_cost
            new_coins = castle['coins'] - coin_cost
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET level = ?, exp = ?, coins = ? 
                WHERE group_id = ?
            ''', (new_level, new_exp, new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            return False
    
    def donate_coins(self, group_id: str, user_id: str, amount: int) -> bool:
        """捐献金币到城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡金币
            new_coins = castle['coins'] + amount
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET coins = ? 
                WHERE group_id = ?
            ''', (new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            return False
    
    def add_castle_exp(self, group_id: str, exp: int) -> bool:
        """增加城堡经验"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡经验
            new_exp = castle['exp'] + exp
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET exp = ? 
                WHERE group_id = ?
            ''', (new_exp, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加城堡经验失败: {str(e)}")
            return False
    
    def elect_lord(self, group_id: str, user_id: str) -> bool:
        """选举领主"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET lord_id = ? 
                WHERE group_id = ?
            ''', (user_id, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            return False
    
    def elect_manager(self, group_id: str, user_id: str) -> bool:
        """选举总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 检查是否已经是总管
            if user_id in castle['managers']:
                return False
            
            # 添加到总管列表
            castle['managers'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            return False
    
    def dismiss_manager(self, group_id: str, user_id: str) -> bool:
        """罢免总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查是否是总管
            if user_id not in castle['managers']:
                return False
            
            # 从总管列表中移除
            castle['managers'].remove(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            return False
    
    def destroy_castle(self, group_id: str) -> bool:
        """拆除城堡"""
        try:
            self.cursor.execute('DELETE FROM castle_data WHERE group_id = ?', (group_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"拆除城堡失败: {str(e)}")
            return False
    
    def get_castle_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡等级排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, level, exp
            FROM castle_data
            ORDER BY level DESC, exp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_coin_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡金币排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, coins
            FROM castle_data
            ORDER BY coins DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_by_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据群组ID获取城堡信息"""
        self.cursor.execute('SELECT * FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['castle_id', 'group_id', 'castle_name', 'level', 'exp', 'coins', 'lord_id', 'managers', 'members', 'created_date']
        result = dict(zip(columns, row))
        
        # 解析JSON字段
        try:
            result['managers'] = json.loads(result['managers'])
        except:
            result['managers'] = []
            
        try:
            result['members'] = json.loads(result['members'])
        except:
            result['members'] = []
            
        return result
    

    
    def join_castle(self, group_id: str, user_id: str) -> bool:
        """加入城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否已经是成员
            if user_id in castle['members']:
                return False
            
            # 添加用户到成员列表
            castle['members'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET members = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            return False
    
    def leave_castle(self, group_id: str, user_id: str) -> bool:
        """退出城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 从成员列表中移除用户
            castle['members'].remove(user_id)
            
            # 如果是领主，清空领主ID
            if castle['lord_id'] == user_id:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, lord_id = NULL 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            # 如果是总管，从总管列表中移除
            elif user_id in castle['managers']:
                castle['managers'].remove(user_id)
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, managers = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), json.dumps(castle['managers']), group_id))
            else:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"退出城堡失败: {str(e)}")
            return False
    
    def upgrade_castle(self, group_id: str, exp_cost: int, coin_cost: int) -> bool:
        """升级城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查资源是否足够
            if castle['exp'] < exp_cost or castle['coins'] < coin_cost:
                return False
            
            # 扣除资源并升级
            new_level = castle['level'] + 1
            new_exp = castle['exp'] - exp_cost
            new_coins = castle['coins'] - coin_cost
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET level = ?, exp = ?, coins = ? 
                WHERE group_id = ?
            ''', (new_level, new_exp, new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            return False
    
    def donate_coins(self, group_id: str, user_id: str, amount: int) -> bool:
        """捐献金币到城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡金币
            new_coins = castle['coins'] + amount
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET coins = ? 
                WHERE group_id = ?
            ''', (new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            return False
    
    def add_castle_exp(self, group_id: str, exp: int) -> bool:
        """增加城堡经验"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡经验
            new_exp = castle['exp'] + exp
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET exp = ? 
                WHERE group_id = ?
            ''', (new_exp, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加城堡经验失败: {str(e)}")
            return False
    
    def elect_lord(self, group_id: str, user_id: str) -> bool:
        """选举领主"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET lord_id = ? 
                WHERE group_id = ?
            ''', (user_id, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            return False
    
    def elect_manager(self, group_id: str, user_id: str) -> bool:
        """选举总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 检查是否已经是总管
            if user_id in castle['managers']:
                return False
            
            # 添加到总管列表
            castle['managers'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            return False
    
    def dismiss_manager(self, group_id: str, user_id: str) -> bool:
        """罢免总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查是否是总管
            if user_id not in castle['managers']:
                return False
            
            # 从总管列表中移除
            castle['managers'].remove(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            return False
    
    def destroy_castle(self, group_id: str) -> bool:
        """拆除城堡"""
        try:
            self.cursor.execute('DELETE FROM castle_data WHERE group_id = ?', (group_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"拆除城堡失败: {str(e)}")
            return False
    
    def get_castle_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡等级排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, level, exp
            FROM castle_data
            ORDER BY level DESC, exp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_coin_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡金币排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, coins
            FROM castle_data
            ORDER BY coins DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_by_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据群组ID获取城堡信息"""
        self.cursor.execute('SELECT * FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['castle_id', 'group_id', 'castle_name', 'level', 'exp', 'coins', 'lord_id', 'managers', 'members', 'created_date']
        result = dict(zip(columns, row))
        
        # 解析JSON字段
        try:
            result['managers'] = json.loads(result['managers'])
        except:
            result['managers'] = []
            
        try:
            result['members'] = json.loads(result['members'])
        except:
            result['members'] = []
            
        return result
    

    
    def join_castle(self, group_id: str, user_id: str) -> bool:
        """加入城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否已经是成员
            if user_id in castle['members']:
                return False
            
            # 添加用户到成员列表
            castle['members'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET members = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            return False
    
    def leave_castle(self, group_id: str, user_id: str) -> bool:
        """退出城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 从成员列表中移除用户
            castle['members'].remove(user_id)
            
            # 如果是领主，清空领主ID
            if castle['lord_id'] == user_id:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, lord_id = NULL 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            # 如果是总管，从总管列表中移除
            elif user_id in castle['managers']:
                castle['managers'].remove(user_id)
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, managers = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), json.dumps(castle['managers']), group_id))
            else:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"退出城堡失败: {str(e)}")
            return False
    
    def upgrade_castle(self, group_id: str, exp_cost: int, coin_cost: int) -> bool:
        """升级城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查资源是否足够
            if castle['exp'] < exp_cost or castle['coins'] < coin_cost:
                return False
            
            # 扣除资源并升级
            new_level = castle['level'] + 1
            new_exp = castle['exp'] - exp_cost
            new_coins = castle['coins'] - coin_cost
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET level = ?, exp = ?, coins = ? 
                WHERE group_id = ?
            ''', (new_level, new_exp, new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            return False
    
    def donate_coins(self, group_id: str, user_id: str, amount: int) -> bool:
        """捐献金币到城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡金币
            new_coins = castle['coins'] + amount
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET coins = ? 
                WHERE group_id = ?
            ''', (new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            return False
    
    def add_castle_exp(self, group_id: str, exp: int) -> bool:
        """增加城堡经验"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡经验
            new_exp = castle['exp'] + exp
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET exp = ? 
                WHERE group_id = ?
            ''', (new_exp, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加城堡经验失败: {str(e)}")
            return False
    
    def elect_lord(self, group_id: str, user_id: str) -> bool:
        """选举领主"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET lord_id = ? 
                WHERE group_id = ?
            ''', (user_id, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            return False
    
    def elect_manager(self, group_id: str, user_id: str) -> bool:
        """选举总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 检查是否已经是总管
            if user_id in castle['managers']:
                return False
            
            # 添加到总管列表
            castle['managers'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            return False
    
    def dismiss_manager(self, group_id: str, user_id: str) -> bool:
        """罢免总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查是否是总管
            if user_id not in castle['managers']:
                return False
            
            # 从总管列表中移除
            castle['managers'].remove(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            return False
    
    def destroy_castle(self, group_id: str) -> bool:
        """拆除城堡"""
        try:
            self.cursor.execute('DELETE FROM castle_data WHERE group_id = ?', (group_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"拆除城堡失败: {str(e)}")
            return False
    
    def get_castle_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡等级排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, level, exp
            FROM castle_data
            ORDER BY level DESC, exp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_coin_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡金币排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, coins
            FROM castle_data
            ORDER BY coins DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_by_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据群组ID获取城堡信息"""
        self.cursor.execute('SELECT * FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['castle_id', 'group_id', 'castle_name', 'level', 'exp', 'coins', 'lord_id', 'managers', 'members', 'created_date']
        result = dict(zip(columns, row))
        
        # 解析JSON字段
        try:
            result['managers'] = json.loads(result['managers'])
        except:
            result['managers'] = []
            
        try:
            result['members'] = json.loads(result['members'])
        except:
            result['members'] = []
            
        return result
    

    
    def join_castle(self, group_id: str, user_id: str) -> bool:
        """加入城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否已经是成员
            if user_id in castle['members']:
                return False
            
            # 添加用户到成员列表
            castle['members'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET members = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            return False
    
    def leave_castle(self, group_id: str, user_id: str) -> bool:
        """退出城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 从成员列表中移除用户
            castle['members'].remove(user_id)
            
            # 如果是领主，清空领主ID
            if castle['lord_id'] == user_id:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, lord_id = NULL 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            # 如果是总管，从总管列表中移除
            elif user_id in castle['managers']:
                castle['managers'].remove(user_id)
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, managers = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), json.dumps(castle['managers']), group_id))
            else:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"退出城堡失败: {str(e)}")
            return False
    
    def upgrade_castle(self, group_id: str, exp_cost: int, coin_cost: int) -> bool:
        """升级城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查资源是否足够
            if castle['exp'] < exp_cost or castle['coins'] < coin_cost:
                return False
            
            # 扣除资源并升级
            new_level = castle['level'] + 1
            new_exp = castle['exp'] - exp_cost
            new_coins = castle['coins'] - coin_cost
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET level = ?, exp = ?, coins = ? 
                WHERE group_id = ?
            ''', (new_level, new_exp, new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            return False
    
    def donate_coins(self, group_id: str, user_id: str, amount: int) -> bool:
        """捐献金币到城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡金币
            new_coins = castle['coins'] + amount
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET coins = ? 
                WHERE group_id = ?
            ''', (new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            return False
    
    def add_castle_exp(self, group_id: str, exp: int) -> bool:
        """增加城堡经验"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡经验
            new_exp = castle['exp'] + exp
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET exp = ? 
                WHERE group_id = ?
            ''', (new_exp, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加城堡经验失败: {str(e)}")
            return False
    
    def elect_lord(self, group_id: str, user_id: str) -> bool:
        """选举领主"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET lord_id = ? 
                WHERE group_id = ?
            ''', (user_id, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            return False
    
    def elect_manager(self, group_id: str, user_id: str) -> bool:
        """选举总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 检查是否已经是总管
            if user_id in castle['managers']:
                return False
            
            # 添加到总管列表
            castle['managers'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            return False
    
    def dismiss_manager(self, group_id: str, user_id: str) -> bool:
        """罢免总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查是否是总管
            if user_id not in castle['managers']:
                return False
            
            # 从总管列表中移除
            castle['managers'].remove(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            return False
    
    def destroy_castle(self, group_id: str) -> bool:
        """拆除城堡"""
        try:
            self.cursor.execute('DELETE FROM castle_data WHERE group_id = ?', (group_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"拆除城堡失败: {str(e)}")
            return False
    
    def get_castle_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡等级排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, level, exp
            FROM castle_data
            ORDER BY level DESC, exp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_coin_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡金币排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, coins
            FROM castle_data
            ORDER BY coins DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_by_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据群组ID获取城堡信息"""
        self.cursor.execute('SELECT * FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['castle_id', 'group_id', 'castle_name', 'level', 'exp', 'coins', 'lord_id', 'managers', 'members', 'created_date']
        result = dict(zip(columns, row))
        
        # 解析JSON字段
        try:
            result['managers'] = json.loads(result['managers'])
        except:
            result['managers'] = []
            
        try:
            result['members'] = json.loads(result['members'])
        except:
            result['members'] = []
            
        return result
    

    
    def join_castle(self, group_id: str, user_id: str) -> bool:
        """加入城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否已经是成员
            if user_id in castle['members']:
                return False
            
            # 添加用户到成员列表
            castle['members'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET members = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            return False
    
    def leave_castle(self, group_id: str, user_id: str) -> bool:
        """退出城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 从成员列表中移除用户
            castle['members'].remove(user_id)
            
            # 如果是领主，清空领主ID
            if castle['lord_id'] == user_id:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, lord_id = NULL 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            # 如果是总管，从总管列表中移除
            elif user_id in castle['managers']:
                castle['managers'].remove(user_id)
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, managers = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), json.dumps(castle['managers']), group_id))
            else:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"退出城堡失败: {str(e)}")
            return False
    
    def upgrade_castle(self, group_id: str, exp_cost: int, coin_cost: int) -> bool:
        """升级城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查资源是否足够
            if castle['exp'] < exp_cost or castle['coins'] < coin_cost:
                return False
            
            # 扣除资源并升级
            new_level = castle['level'] + 1
            new_exp = castle['exp'] - exp_cost
            new_coins = castle['coins'] - coin_cost
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET level = ?, exp = ?, coins = ? 
                WHERE group_id = ?
            ''', (new_level, new_exp, new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            return False
    
    def donate_coins(self, group_id: str, user_id: str, amount: int) -> bool:
        """捐献金币到城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡金币
            new_coins = castle['coins'] + amount
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET coins = ? 
                WHERE group_id = ?
            ''', (new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            return False
    
    def add_castle_exp(self, group_id: str, exp: int) -> bool:
        """增加城堡经验"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡经验
            new_exp = castle['exp'] + exp
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET exp = ? 
                WHERE group_id = ?
            ''', (new_exp, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加城堡经验失败: {str(e)}")
            return False
    
    def elect_lord(self, group_id: str, user_id: str) -> bool:
        """选举领主"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET lord_id = ? 
                WHERE group_id = ?
            ''', (user_id, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            return False
    
    def elect_manager(self, group_id: str, user_id: str) -> bool:
        """选举总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 检查是否已经是总管
            if user_id in castle['managers']:
                return False
            
            # 添加到总管列表
            castle['managers'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            return False
    
    def dismiss_manager(self, group_id: str, user_id: str) -> bool:
        """罢免总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查是否是总管
            if user_id not in castle['managers']:
                return False
            
            # 从总管列表中移除
            castle['managers'].remove(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            return False
    
    def destroy_castle(self, group_id: str) -> bool:
        """拆除城堡"""
        try:
            self.cursor.execute('DELETE FROM castle_data WHERE group_id = ?', (group_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"拆除城堡失败: {str(e)}")
            return False
    
    def get_castle_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡等级排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, level, exp
            FROM castle_data
            ORDER BY level DESC, exp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_coin_ranking(self, limit: int = 10) -> List[tuple]:
        """获取城堡金币排行榜"""
        self.cursor.execute('''
            SELECT castle_id, castle_name, coins
            FROM castle_data
            ORDER BY coins DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_castle_by_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据群组ID获取城堡信息"""
        self.cursor.execute('SELECT * FROM castle_data WHERE group_id = ?', (group_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = ['castle_id', 'group_id', 'castle_name', 'level', 'exp', 'coins', 'lord_id', 'managers', 'members', 'created_date']
        result = dict(zip(columns, row))
        
        # 解析JSON字段
        try:
            result['managers'] = json.loads(result['managers'])
        except:
            result['managers'] = []
            
        try:
            result['members'] = json.loads(result['members'])
        except:
            result['members'] = []
            
        return result
    

    
    def join_castle(self, group_id: str, user_id: str) -> bool:
        """加入城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否已经是成员
            if user_id in castle['members']:
                return False
            
            # 添加用户到成员列表
            castle['members'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET members = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            return False
    
    def leave_castle(self, group_id: str, user_id: str) -> bool:
        """退出城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 从成员列表中移除用户
            castle['members'].remove(user_id)
            
            # 如果是领主，清空领主ID
            if castle['lord_id'] == user_id:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, lord_id = NULL 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            # 如果是总管，从总管列表中移除
            elif user_id in castle['managers']:
                castle['managers'].remove(user_id)
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ?, managers = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), json.dumps(castle['managers']), group_id))
            else:
                self.cursor.execute('''
                    UPDATE castle_data 
                    SET members = ? 
                    WHERE group_id = ?
                ''', (json.dumps(castle['members']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"退出城堡失败: {str(e)}")
            return False
    
    def upgrade_castle(self, group_id: str, exp_cost: int, coin_cost: int) -> bool:
        """升级城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查资源是否足够
            if castle['exp'] < exp_cost or castle['coins'] < coin_cost:
                return False
            
            # 扣除资源并升级
            new_level = castle['level'] + 1
            new_exp = castle['exp'] - exp_cost
            new_coins = castle['coins'] - coin_cost
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET level = ?, exp = ?, coins = ? 
                WHERE group_id = ?
            ''', (new_level, new_exp, new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            return False
    
    def donate_coins(self, group_id: str, user_id: str, amount: int) -> bool:
        """捐献金币到城堡"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡金币
            new_coins = castle['coins'] + amount
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET coins = ? 
                WHERE group_id = ?
            ''', (new_coins, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            return False
    
    def add_castle_exp(self, group_id: str, exp: int) -> bool:
        """增加城堡经验"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 增加城堡经验
            new_exp = castle['exp'] + exp
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET exp = ? 
                WHERE group_id = ?
            ''', (new_exp, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加城堡经验失败: {str(e)}")
            return False
    
    def elect_lord(self, group_id: str, user_id: str) -> bool:
        """选举领主"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET lord_id = ? 
                WHERE group_id = ?
            ''', (user_id, group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            return False
    
    def elect_manager(self, group_id: str, user_id: str) -> bool:
        """选举总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查用户是否是成员
            if user_id not in castle['members']:
                return False
            
            # 检查是否已经是总管
            if user_id in castle['managers']:
                return False
            
            # 添加到总管列表
            castle['managers'].append(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            return False
    
    def dismiss_manager(self, group_id: str, user_id: str) -> bool:
        """罢免总管"""
        try:
            castle = self.get_castle_by_group(group_id)
            if not castle:
                return False
            
            # 检查是否是总管
            if user_id not in castle['managers']:
                return False
            
            # 从总管列表中移除
            castle['managers'].remove(user_id)
            
            self.cursor.execute('''
                UPDATE castle_data 
                SET managers = ? 
                WHERE group_id = ?
            ''', (json.dumps(castle['managers']), group_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            return False
    
    def destroy_castle(self, group_id: str) -> bool:
        """销毁城堡"""
        try:
            self.cursor.execute('''
                DELETE FROM castle_data 
                WHERE group_id = ?
            ''', (group_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"销毁城堡失败: {str(e)}")
            return False

    def __del__(self):
        """析构函数，关闭数据库连接"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
