import os
import sqlite3
from pathlib import Path
from nonebot.log import logger

from .db_image import DB_path

DB_control = Path(os.path.join(DB_path, "control.db"))


class DBCONTROL:
    _has_init = False

    def __init__(self):
        if not DBCONTROL._has_init:
            if not DB_path.exists():
                DB_control.mkdir(parents=True)
            self.database_path = DB_control
            self.conn = sqlite3.connect(self.database_path)
            # 打印sql日志
            # self.conn.set_trace_callback(print)
            self._create_table()
            logger.info("控制数据库连接！")

    def close(self):
        """关闭数据库"""
        self.conn.close()
        logger.info("控制数据库关闭")

    def _create_table(self):
        """创建表"""
        # 创建消息管理表
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS  MESSAGE_CONTROL(
                  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                  "bot_adapter" text,
                  "bot_id" text,
                  "msg_source_type" text,
                  "msg_source_parent_id" text,
                  "msg_source_parent_name" text,
                  "msg_source_id" text,
                  "msg_source_name" text,
                  "status" integer,
                  "active_push" integer
                );"""
        )
        # msg_source_id 值可能为:服务器id,qq群群号,频道号,频道用户id,qq号;
        # msg_source_type 消息来源类型 guild,channel,private,group,c2c  private为频道发起私聊 c2c为qq私聊;
        # status 是否启用  0为false 1为true;
        # active_push 是否主动推送 0为false 1为true;
        self.conn.commit()

    def check_msg_permission(self, bot_adapter: str, bot_id: str, msg_source_type: str, msg_source_id: str) -> bool:
        """查询sql 检查消息来源权限 资源消耗过多，非必要不要使用"""
        sql = (
            f"select * from MESSAGE_CONTROL where bot_adapter=? and bot_id=? and msg_source_type=? and msg_source_id=?"
        )
        c = self.conn.cursor()
        c.execute(sql, (bot_adapter, bot_id, msg_source_type, msg_source_id))
        row = c.fetchone()
        if not row:
            return True
        else:
            # 查询有结果时将查询结果转换为字典
            result = dict(zip([column[0] for column in c.description], row))
            if result.get("status") == "0":
                return False
            else:
                return True

    def get_all_blacklist(self) -> [dict]:
        """获取全部黑名单"""
        sql = f"select * from MESSAGE_CONTROL ORDER BY 'bot_adapter', 'bot_id', 'msg_source_type', 'msg_source_parent_id', 'msg_source_id'"
        c = self.conn.cursor()
        c.execute(
            sql,
        )
        rows = c.fetchall()
        results: [dict] = []
        if rows is not None:
            # 查询有结果时将查询结果转换为字典
            for row in rows:
                result = dict(zip([column[0] for column in c.description], row))
                results.append(result)
        self.conn.commit()
        return results

    def get_all_push(self, bot_adapter: str, bot_id: str) -> [dict]:
        """获取全部推送目标"""
        sql = f"select * from MESSAGE_CONTROL where bot_adapter=? and bot_id=? and active_push == 1"
        c = self.conn.cursor()
        c.execute(sql, (bot_adapter, bot_id))
        rows = c.fetchall()
        results: [dict] = []
        if rows is not None:
            # 查询有结果时将查询结果转换为字典
            for row in rows:
                result = dict(zip([column[0] for column in c.description], row))
                results.append(result)
        self.conn.commit()
        return results

    def add_or_modify_MESSAGE_CONTROL(
        self,
        bot_adapter: str,
        bot_id: str,
        msg_source_type: str,
        msg_source_id: str,
        msg_source_name: str = None,
        msg_source_parent_id: str = None,
        msg_source_parent_name: str = None,
        status: int = None,
        active_push: int = None,
    ):
        """添加或修改 消息控制表"""
        sql = (
            f"select * from MESSAGE_CONTROL where bot_adapter=? and bot_id=? and msg_source_type=? and msg_source_id=?"
        )
        c = self.conn.cursor()
        c.execute(sql, (bot_adapter, bot_id, msg_source_type, msg_source_id))
        row = c.fetchone()
        if not row:  # create
            sql = f"INSERT INTO MESSAGE_CONTROL (bot_adapter, bot_id,msg_source_type,msg_source_id,msg_source_name,msg_source_parent_id,msg_source_parent_name,status,active_push) VALUES (?,?,?,?,?,?,?,?,?);"
            c.execute(
                sql,
                (
                    bot_adapter,
                    bot_id,
                    msg_source_type,
                    msg_source_id,
                    msg_source_name,
                    msg_source_parent_id,
                    msg_source_parent_name,
                    status,
                    active_push,
                ),
            )
        else:
            result = dict(zip([column[0] for column in c.description], row))
            _id = result["id"]
            # 缺省时不改变值
            if msg_source_parent_id is None:
                msg_source_parent_id = result["msg_source_parent_id"]
            if msg_source_parent_name is None:
                msg_source_parent_name = result["msg_source_parent_name"]
            if msg_source_name is None:
                msg_source_name = result["msg_source_name"]
            if status is None:
                status = result["status"]
            if active_push is None:
                active_push = result["active_push"]
            sql = f"UPDATE MESSAGE_CONTROL set msg_source_name=?,msg_source_parent_id=?, msg_source_parent_name=?,status=?,active_push=? where id=?"
            c.execute(sql, (msg_source_name, msg_source_parent_id, msg_source_parent_name, status, active_push, _id))


db_control = DBCONTROL()
