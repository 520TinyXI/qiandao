import sqlite3
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

class SignDatabase:
    def __init__(self, plugin_dir: str):
        db_dir = os.path.join(os.path.dirname(os.path.dirname(plugin_dir)), "plugins_db")
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
        # 检查是否已存在
        self.cursor.execute('SELECT user_id FROM user_names WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        if self.cursor.fetchone():
            self.cursor.execute('UPDATE user_names SET user_name = ? WHERE user_id = ? AND group_id = ?', 
                              (user_name, user_id, group_id))
        else:
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
        
    def get_total_sign_ranking(self, group_id: str = None, limit: int = 10) -> List[tuple]:
        """获取总签到排行榜"""
        if group_id:
            self.cursor.execute('''
                SELECT user_id, total_days FROM sign_data
                WHERE group_id = ?
                ORDER BY total_days DESC LIMIT ?
            ''', (group_id, limit))
        else:
            self.cursor.execute('''
                SELECT user_id, total_days FROM sign_data
                ORDER BY total_days DESC LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()
        
    def get_continuous_sign_ranking(self, group_id: str = None, limit: int = 10) -> List[tuple]:
        """获取连续签到排行榜"""
        if group_id:
            self.cursor.execute('''
                SELECT user_id, continuous_days FROM sign_data
                WHERE group_id = ?
                ORDER BY continuous_days DESC LIMIT ?
            ''', (group_id, limit))
        else:
            self.cursor.execute('''
                SELECT user_id, continuous_days FROM sign_data
                ORDER BY continuous_days DESC LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()
        
    def get_level_ranking(self, group_id: str = None, limit: int = 10) -> List[tuple]:
        """获取等级排行榜"""
        if group_id:
            self.cursor.execute('''
                SELECT user_id, level, exp FROM sign_data
                WHERE group_id = ?
                ORDER BY level DESC, exp DESC LIMIT ?
            ''', (group_id, limit))
        else:
            self.cursor.execute('''
                SELECT user_id, level, exp FROM sign_data
                ORDER BY level DESC, exp DESC LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()
        
    def get_world_sign_ranking(self, limit: int = 10) -> List[tuple]:
        """获取世界签到排行榜"""
        self.cursor.execute('''
            SELECT user_id, total_days FROM sign_data
            ORDER BY total_days DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
        
    def get_group_sign_rank(self, group_id: str, user_id: str) -> int:
        """获取群内签到排名"""
        if not group_id:
            return 0
        self.cursor.execute('''
            SELECT COUNT(*) + 1 FROM sign_data 
            WHERE group_id = ? AND total_days > (
                SELECT total_days FROM sign_data WHERE user_id = ?
            )
        ''', (group_id, user_id))
        row = self.cursor.fetchone()
        return row[0] if row else 0
        
    def get_world_sign_rank(self, user_id: str) -> int:
        """获取世界签到排名"""
        self.cursor.execute('''
            SELECT COUNT(*) + 1 FROM sign_data 
            WHERE total_days > (
                SELECT total_days FROM sign_data WHERE user_id = ?
            )
        ''', (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0
        
    def close(self):
        """关闭数据库连接"""
        self.conn.close()