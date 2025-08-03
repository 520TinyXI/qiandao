from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import os
import datetime
import random

from .database import SignDatabase
from .image_generator import ImageGenerator
from .sign_manager import SignManager
from .castle_manager import CastleManager

@register("astrbot_plugin_advanced_sign", "XiaoJie", "一个高级签到插件，包含等级系统、排行榜、商店系统", "1.0.0", "https://github.com/XiaoJie/astrbot_plugin_advanced_sign")
class AdvancedSignPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.db = SignDatabase(os.path.dirname(__file__))
        self.img_gen = ImageGenerator(os.path.dirname(__file__))
        
    @filter.command("签到")
    async def sign(self, event: AstrMessageEvent):
        '''每日签到'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            today = datetime.date.today().strftime('%Y-%m-%d')
            
            user_data = self.db.get_user_data(user_id)
            
            if user_data and user_data.get('last_sign') == today:
                image_path = await self.img_gen.create_sign_image("今天已经签到过啦~")
                if image_path:
                    yield event.image_result(image_path)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                return

            # 执行签到逻辑
            result = SignManager.daily_sign(user_data, group_id, self.db)
            
            # 更新用户数据
            self.db.update_user_data(
                user_id,
                group_id=group_id,
                total_days=result['total_days'],
                last_sign=today,
                continuous_days=result['continuous_days'],
                exp=result['exp'],
                coins=result['coins'],
                level=result['level'],
                next_level_exp=result['next_level_exp']
            )

            # 存储用户昵称
            user_name = event.get_sender_name()
            self.db.update_user_name(user_id, user_name, group_id)
            
            # 处理新获得的称号
            new_titles = result.get('new_titles', [])
            for title in new_titles:
                self.db.add_user_title(user_id, title)
            
            # 如果获得了【七日先锋】或【永恒裁决者】称号，但之前有断签，则需要收回称号
            if result['continuous_days'] < 7 and '七日先锋' not in new_titles:
                # 检查用户是否拥有【七日先锋】称号
                user_titles = self.db.get_user_titles(user_id)
                for title, is_active in user_titles:
                    if title == "七日先锋":
                        # 移除称号
                        self.db.cursor.execute(
                            'DELETE FROM user_titles WHERE user_id = ? AND title = ?', 
                            (user_id, "七日先锋")
                        )
                        self.db.conn.commit()
                        break
            
            if result['continuous_days'] < 30 and '永恒裁决者' not in new_titles:
                # 检查用户是否拥有【永恒裁决者】称号
                user_titles = self.db.get_user_titles(user_id)
                for title, is_active in user_titles:
                    if title == "永恒裁决者":
                        # 移除称号
                        self.db.cursor.execute(
                            'DELETE FROM user_titles WHERE user_id = ? AND title = ?', 
                            (user_id, "永恒裁决者")
                        )
                        self.db.conn.commit()
                        break
            
            # 记录签到历史
            self.db.log_sign(user_id, result['exp'], result['coins'])
            
            # 生成结果消息
            result_text = SignManager.format_sign_result(result, group_id, self.db)

            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"签到失败: {str(e)}")
            yield event.plain_result("签到失败了~请联系管理员检查日志")
            
    @filter.command("个人信息")
    async def user_info(self, event: AstrMessageEvent):
        '''查看个人信息'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            user_data = self.db.get_user_data(user_id)
            if not user_data:
                yield event.plain_result("您还没有签到过哦~")
                return
                
            # 获取用户当前激活的称号
            active_title = self.db.get_active_title(user_id)
                
            result_text = SignManager.format_user_info(user_data, active_title)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"获取个人信息失败: {str(e)}")
            yield event.plain_result("获取个人信息失败~请联系管理员检查日志")
            

    @filter.command("连续签到排行榜")
    async def continuous_ranking(self, event: AstrMessageEvent):
        '''连续签到排行榜'''
        try:
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            ranking_data = self.db.get_continuous_sign_ranking(10)
            result_text = SignManager.format_continuous_ranking(ranking_data, self.db)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"获取连续签到排行榜失败: {str(e)}")
            yield event.plain_result("获取连续签到排行榜失败~请联系管理员检查日志")
            
    @filter.command("等级排行榜")
    async def level_ranking(self, event: AstrMessageEvent):
        '''等级排行榜'''
        try:
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            ranking_data = self.db.get_level_ranking(10)
            result_text = SignManager.format_level_ranking(ranking_data, self.db)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"获取等级排行榜失败: {str(e)}")
            yield event.plain_result("获取等级排行榜失败~请联系管理员检查日志")
            
    @filter.command("世界排行榜")
    async def world_ranking(self, event: AstrMessageEvent):
        '''世界总签到排行榜'''
        try:
            ranking_data = self.db.get_world_sign_ranking(10)
            result_text = SignManager.format_world_ranking(ranking_data, self.db)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"获取世界排行榜失败: {str(e)}")
            yield event.plain_result("获取世界排行榜失败~请联系管理员检查日志")
            
    @filter.command("称号")
    async def titles_handler(self, event: AstrMessageEvent):
        '''显示已获得的称号'''
        try:
            user_id = event.get_sender_id()
            
            # 获取用户所有称号
            user_titles = self.db.get_user_titles(user_id)
            
            if not user_titles:
                yield event.plain_result("您还没有获得任何称号哦~")
                return
            
            # 格式化称号列表
            title_list = "\n".join([f"【{title}】" for title, is_active in user_titles])
            result_text = f"您已获得的称号:\n{title_list}"
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
        
        except Exception as e:
            logger.error(f"获取称号列表失败: {str(e)}")
            yield event.plain_result("获取称号列表失败~请联系管理员检查日志")
            
    @filter.command("使用称号")
    async def use_title_handler(self, event: AstrMessageEvent):
        '''使用称号'''
        try:
            user_id = event.get_sender_id()
            args = event.message_str.split()[1:]
            
            if len(args) < 1:
                yield event.plain_result("命令格式错误，请使用: /使用称号 称号名称")
                return
                
            title_name = "".join(args)
            
            # 检查用户是否拥有该称号
            user_titles = self.db.get_user_titles(user_id)
            title_exists = any(title == title_name for title, _ in user_titles)
            
            if not title_exists:
                yield event.plain_result(f"您还没有获得称号【{title_name}】哦~")
                return
            
            # 激活称号
            self.db.activate_title(user_id, title_name)
            
            yield event.plain_result(f"成功使用称号【{title_name}】!")
            
        except Exception as e:
            logger.error(f"使用称号失败: {str(e)}")
            yield event.plain_result("使用称号失败~请联系管理员检查日志")
            
    @filter.command("不使用称号")
    async def unset_title_handler(self, event: AstrMessageEvent):
        '''取消使用称号'''
        try:
            user_id = event.get_sender_id()
            
            # 取消激活所有称号
            self.db.deactivate_all_titles(user_id)
            
            yield event.plain_result("已取消使用称号!")
            
        except Exception as e:
            logger.error(f"取消使用称号失败: {str(e)}")
            yield event.plain_result("取消使用称号失败~请联系管理员检查日志")
            
    @filter.command("称号大全")
    async def all_titles_handler(self, event: AstrMessageEvent):
        '''显示所有称号和获得途径'''
        try:
            # 定义所有称号和获得途径
            all_titles = [
                "【签到新人】 - 首次签到获得",
                "【签到达人】 - 累计签到7天获得",
                "【月神之誓】 - 累计签到30天获得",
                "【七日先锋】 - 连续签到7天获得（断签会收回）",
                "【永恒裁决者】 - 连续签到30天获得（断签会收回）"
            ]
            
            # 格式化称号列表
            title_list = "\n".join(all_titles)
            result_text = f"所有称号和获得途径:\n{title_list}"
            
            yield event.plain_result(result_text)
            
        except Exception as e:
            logger.error(f"获取称号大全失败: {str(e)}")
            yield event.plain_result("获取称号大全失败~请联系管理员检查日志")
            
    @filter.command("购买")
    async def buy_item(self, event: AstrMessageEvent):
        '''购买物品'''
        try:
            user_id = event.get_sender_id()
            args = event.message_str.split()[1:]
            
            if len(args) < 2:
                yield event.plain_result("命令格式错误，请使用: /购买 补签卡 数量")
                return
                
            item_name = args[0]
            try:
                quantity = int(args[1])
            except ValueError:
                yield event.plain_result("数量必须是数字")
                return
                
            if item_name != "补签卡":
                yield event.plain_result("目前只能购买补签卡")
                return
                
            # 执行购买逻辑
            result = SignManager.buy_item(user_id, item_name, quantity, self.db)
            
            if result['success']:
                yield event.plain_result(f"购买成功！花费了{result['cost']}金币，获得了{quantity}张补签卡")
            else:
                yield event.plain_result(f"购买失败：{result['message']}")

        except Exception as e:
            logger.error(f"购买物品失败: {str(e)}")
            yield event.plain_result("购买物品失败~请联系管理员检查日志")
            
    @filter.command("补签")
    async def resign(self, event: AstrMessageEvent):
        '''补签'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            args = event.message_str.split()[1:]
            
            try:
                days = int(args[0]) if args else 1
            except ValueError:
                yield event.plain_result("补签天数必须是数字")
                return
                
            # 执行补签逻辑
            result = SignManager.resign(user_id, days, group_id, self.db)
            
            if result['success']:
                yield event.plain_result(f"补签成功！消耗了{result['cost']}张补签卡和{result['coins']}金币")
            else:
                yield event.plain_result(f"补签失败：{result['message']}")

        except Exception as e:
            logger.error(f"补签失败: {str(e)}")
            yield event.plain_result("补签失败~请联系管理员检查日志")
            
    @filter.command("查看背包")
    async def view_inventory(self, event: AstrMessageEvent):
        '''查看背包'''
        try:
            user_id = event.get_sender_id()
            
            inventory = self.db.get_user_inventory(user_id)
            result_text = SignManager.format_inventory(inventory)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"查看背包失败: {str(e)}")
            yield event.plain_result("查看背包失败~请联系管理员检查日志")
            
    @filter.command("签到商店")
    async def sign_shop(self, event: AstrMessageEvent):
        '''签到商店'''
        try:
            # 显示商店商品信息
            shop_items = [
                ("补签卡", 100, "用于补签，每次补签消耗1张补签卡和10金币"),
            ]
            
            result_text = "签到商店\n"
            result_text += "=" * 20 + "\n"
            for item_name, price, description in shop_items:
                result_text += f"{item_name} - {price}金币\n{description}\n\n"
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"查看签到商店失败: {str(e)}")
            yield event.plain_result("查看签到商店失败~请联系管理员检查日志")
            
    @filter.command("我的排名")
    async def my_ranking(self, event: AstrMessageEvent):
        '''显示自己在世界排行榜、连续签到排行榜和等级排行榜的排名'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            # 获取用户数据
            user_data = self.db.get_user_data(user_id)
            if not user_data:
                yield event.plain_result("您还没有签到过哦~")
                return
                
            # 获取各项排名（使用修复后的方法）
            world_total_rank = self.db.get_world_sign_rank(user_id)
            continuous_rank = self.db.get_continuous_sign_rank(user_id)
            
            # 获取等级排名
            self.db.cursor.execute('''
                SELECT COUNT(*) + 1 FROM sign_data
                WHERE level > ? OR (level = ? AND exp > ?)
            ''', (user_data['level'], user_data['level'], user_data['exp']))
            level_rank_row = self.db.cursor.fetchone()
            level_rank = level_rank_row[0] if level_rank_row else 1
            
            # 格式化结果
            result_text = SignManager.format_my_ranking(
                world_total_rank=world_total_rank,
                continuous_rank=continuous_rank,
                level_rank=level_rank
            )
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"获取我的排名失败: {str(e)}")
            yield event.plain_result("获取我的排名失败~请联系管理员检查日志")
            
    from .castle_manager import CastleManager
    
    @filter.command("创建城堡")
    async def create_castle(self, event: AstrMessageEvent):
        '''创建城堡'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中创建城堡哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if castle:
                yield event.plain_result("该群聊已经有城堡了哦~")
                return
                
            args = event.message_str.split()[1:]
            if len(args) < 1:
                yield event.plain_result("命令格式错误，请使用: /创建城堡 城堡名称 [参与者1] [参与者2] ... [参与者5]")
                return
                
            castle_name = args[0]
            
            # 检查城堡名称是否已存在
            if self.db.check_castle_name_exists(castle_name):
                yield event.plain_result("城堡名称已存在，请换一个名称~")
                return
                
            # 获取参与者列表
            participant_ids = args[1:6]  # 最多5个参与者
            
            # 创建城堡
            if self.db.create_castle(group_id, castle_name, user_id, participant_ids):
                # 选举创建者为领主
                self.db.elect_lord(group_id, user_id)
                yield event.plain_result(f"城堡【{castle_name}】创建成功！创建者{user_id}自动成为领主。")
            else:
                yield event.plain_result("创建城堡失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"创建城堡失败: {str(e)}")
            yield event.plain_result("创建城堡失败~请联系管理员检查日志")
            
    @filter.command("查看城堡")
    async def view_castle(self, event: AstrMessageEvent):
        '''查看城堡信息'''
        try:
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中查看城堡哦~")
                return
                
            castle = self.db.get_castle_by_group(group_id)
            result_text = CastleManager.format_castle_info(castle, self.db)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"查看城堡失败: {str(e)}")
            yield event.plain_result("查看城堡失败~请联系管理员检查日志")
            
    @filter.command("加入城堡")
    async def join_castle(self, event: AstrMessageEvent):
        '''加入城堡'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中加入城堡哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if not castle:
                yield event.plain_result("该群聊还没有建造城堡哦~")
                return
                
            # 加入城堡
            if self.db.join_castle(group_id, user_id):
                yield event.plain_result("成功加入城堡！")
            else:
                yield event.plain_result("加入城堡失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"加入城堡失败: {str(e)}")
            yield event.plain_result("加入城堡失败~请联系管理员检查日志")
            
    @filter.command("退出城堡")
    async def leave_castle(self, event: AstrMessageEvent):
            '''退出城堡'''
            try:
                user_id = event.get_sender_id()
                group_id = event.get_group_id() if event.message_obj.group_id else None
                
                if not group_id:
                    yield event.plain_result("只能在群聊中退出城堡哦~")
                    return
                    
                # 检查是否已有城堡
                castle = self.db.get_castle_by_group(group_id)
                if not castle:
                    yield event.plain_result("该群聊还没有建造城堡哦~")
                    return
                    
                # 退出城堡
                if self.db.leave_castle(group_id, user_id):
                    yield event.plain_result("成功退出城堡！")
                else:
                    yield event.plain_result("退出城堡失败，请稍后再试~")
                    
            except Exception as e:
                logger.error(f"退出城堡失败: {str(e)}")
                yield event.plain_result("退出城堡失败~请联系管理员检查日志")
                
    @filter.command("升级城堡")
    async def upgrade_castle(self, event: AstrMessageEvent):
        '''升级城堡'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中升级城堡哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if not castle:
                yield event.plain_result("该群聊还没有建造城堡哦~")
                return
                
            # 检查是否是领主
            if castle['lord_id'] != user_id:
                yield event.plain_result("只有领主才能升级城堡哦~")
                return
                
            # 获取升级成本
            level = castle['level']
            if level >= 5:
                yield event.plain_result("城堡已达到最高等级！")
                return
                
            upgrade_cost = CastleManager.CASTLE_UPGRADE_COSTS.get(level)
            if not upgrade_cost:
                yield event.plain_result("无法获取升级成本信息，请联系管理员~")
                return
                
            # 检查资源是否足够
            if castle['exp'] < upgrade_cost['exp'] or castle['coins'] < upgrade_cost['coins']:
                yield event.plain_result(f"城堡资源不足！需要经验:{upgrade_cost['exp']}, 金币:{upgrade_cost['coins']}")
                return
                
            # 升级城堡
            if self.db.upgrade_castle(group_id, upgrade_cost['exp'], upgrade_cost['coins']):
                yield event.plain_result(f"城堡升级成功！当前等级:{level+1}")
            else:
                yield event.plain_result("升级城堡失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"升级城堡失败: {str(e)}")
            yield event.plain_result("升级城堡失败~请联系管理员检查日志")
            
    @filter.command("捐献金币")
    async def donate_coins(self, event: AstrMessageEvent):
        '''捐献金币到城堡'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中捐献金币哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if not castle:
                yield event.plain_result("该群聊还没有建造城堡哦~")
                return
                
            args = event.message_str.split()[1:]
            if len(args) < 1:
                yield event.plain_result("命令格式错误，请使用: /捐献金币 金币数量")
                return
                
            try:
                amount = int(args[0])
            except ValueError:
                yield event.plain_result("金币数量必须是数字")
                return
                
            if amount <= 0:
                yield event.plain_result("金币数量必须大于0")
                return
                
            # 检查用户是否有足够金币
            user_data = self.db.get_user_data(user_id)
            if not user_data or user_data['coins'] < amount:
                yield event.plain_result("您的金币不足！")
                return
                
            # 捐献金币
            if self.db.donate_coins(group_id, user_id, amount):
                # 扣除用户金币
                self.db.update_user_data(user_id, coins=user_data['coins'] - amount)
                # 增加城堡经验
                castle_exp_gain = CastleManager.get_castle_exp_gain()
                self.db.add_castle_exp(group_id, castle_exp_gain)
                yield event.plain_result(f"成功捐献{amount}金币到城堡！城堡获得{castle_exp_gain}经验。")
            else:
                yield event.plain_result("捐献金币失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"捐献金币失败: {str(e)}")
            yield event.plain_result("捐献金币失败~请联系管理员检查日志")
            
    @filter.command("选举领主")
    async def elect_lord(self, event: AstrMessageEvent):
        '''选举领主'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中选举领主哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if not castle:
                yield event.plain_result("该群聊还没有建造城堡哦~")
                return
                
            # 检查是否是领主
            if castle['lord_id'] != user_id:
                yield event.plain_result("只有领主才能选举新的领主哦~")
                return
                
            args = event.message_str.split()[1:]
            if len(args) < 1:
                yield event.plain_result("命令格式错误，请使用: /选举领主 @用户")
                return
                
            # 解析被选举用户ID
            target_user_id = args[0]
            if target_user_id.startswith("@"):
                target_user_id = target_user_id[1:]
                
            # 检查用户是否是城堡成员
            if target_user_id not in castle['members']:
                yield event.plain_result("被选举用户不是城堡成员！")
                return
                
            # 选举领主
            if self.db.elect_lord(group_id, target_user_id):
                yield event.plain_result(f"成功选举{target_user_id}为新领主！")
            else:
                yield event.plain_result("选举领主失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"选举领主失败: {str(e)}")
            yield event.plain_result("选举领主失败~请联系管理员检查日志")
            
    @filter.command("选举总管")
    async def elect_manager(self, event: AstrMessageEvent):
        '''选举总管'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中选举总管哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if not castle:
                yield event.plain_result("该群聊还没有建造城堡哦~")
                return
                
            # 检查是否是领主
            if castle['lord_id'] != user_id:
                yield event.plain_result("只有领主才能选举总管哦~")
                return
                
            args = event.message_str.split()[1:]
            if len(args) < 1:
                yield event.plain_result("命令格式错误，请使用: /选举总管 @用户")
                return
                
            # 解析被选举用户ID
            target_user_id = args[0]
            if target_user_id.startswith("@"):
                target_user_id = target_user_id[1:]
                
            # 检查用户是否是城堡成员
            if target_user_id not in castle['members']:
                yield event.plain_result("被选举用户不是城堡成员！")
                return
                
            # 选举总管
            if self.db.elect_manager(group_id, target_user_id):
                yield event.plain_result(f"成功选举{target_user_id}为总管！")
            else:
                yield event.plain_result("选举总管失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"选举总管失败: {str(e)}")
            yield event.plain_result("选举总管失败~请联系管理员检查日志")
            
    @filter.command("罢免总管")
    async def dismiss_manager(self, event: AstrMessageEvent):
        '''罢免总管'''
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id() if event.message_obj.group_id else None
            
            if not group_id:
                yield event.plain_result("只能在群聊中罢免总管哦~")
                return
                
            # 检查是否已有城堡
            castle = self.db.get_castle_by_group(group_id)
            if not castle:
                yield event.plain_result("该群聊还没有建造城堡哦~")
                return
                
            # 检查是否是领主
            if castle['lord_id'] != user_id:
                yield event.plain_result("只有领主才能罢免总管哦~")
                return
                
            args = event.message_str.split()[1:]
            if len(args) < 1:
                yield event.plain_result("命令格式错误，请使用: /罢免总管 @用户")
                return
                
            # 解析被罢免用户ID
            target_user_id = args[0]
            if target_user_id.startswith("@"):
                target_user_id = target_user_id[1:]
                
            # 检查用户是否是总管
            if target_user_id not in castle['managers']:
                yield event.plain_result("被罢免用户不是总管！")
                return
                
            # 罢免总管
            if self.db.dismiss_manager(group_id, target_user_id):
                yield event.plain_result(f"成功罢免{target_user_id}的总管职务！")
            else:
                yield event.plain_result("罢免总管失败，请稍后再试~")
                
        except Exception as e:
            logger.error(f"罢免总管失败: {str(e)}")
            yield event.plain_result("罢免总管失败~请联系管理员检查日志")
            
    @filter.command("城堡排行榜")
    async def castle_ranking(self, event: AstrMessageEvent):
        '''城堡等级排行榜'''
        try:
            ranking_data = self.db.get_castle_ranking(10)
            result_text = CastleManager.format_castle_ranking(ranking_data)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"获取城堡排行榜失败: {str(e)}")
            yield event.plain_result("获取城堡排行榜失败~请联系管理员检查日志")
            
    @filter.command("城堡金币榜")
    async def castle_coin_ranking(self, event: AstrMessageEvent):
        '''城堡金币排行榜'''
        try:
            ranking_data = self.db.get_castle_coin_ranking(10)
            result_text = CastleManager.format_castle_coin_ranking(ranking_data)
            
            image_path = await self.img_gen.create_sign_image(result_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"获取城堡金币排行榜失败: {str(e)}")
            yield event.plain_result("获取城堡金币排行榜失败~请联系管理员检查日志")