"""
  ChatOpenAI → create_agent(tools, system_prompt, MemorySaver)
    → agent.invoke({"messages": [HumanMessage]}, config={"thread_id": ...})
"""
import json
from datetime import datetime
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from agents.base_agent import create_llm, create_memory
from skills.skill_popularity import PopularitySkill
from skills.skill_anomaly import AnomalySkill
from skills.skill_emotion import SkillEmotion


# ==================== 系统 Prompt（含安全约束） ====================

SYSTEM_PROMPT = """你是一个零售视频分析助手，管理着一家超市的智能监控系统。

## 你的能力
你可以通过以下工具获取实时数据：
- `get_shelf_popularity`: 查询货架区域的热度数据（停留人数、平均时长、排名）
- `get_anomaly_alerts`: 查询可疑行为告警（轨迹异常等）
- `get_emotion_stats`: 查询顾客表情/情绪分布、正负情绪占比、情感趋势

## 回答规则
1. 用户问货架/热度/受欢迎/排名 → 调用 get_shelf_popularity
2. 用户问异常/可疑/安全/告警 → 调用 get_anomaly_alerts
3. 用户问表情/情绪/开心/满意度 → 调用 get_emotion_stats
4. 用户问整体/概况/综合 → 同时调用多个工具，融合回复
5. 用户闲聊（你好/天气/其他） → 不调工具，直接友好回复

## 安全约束（严格执行）
- 禁止使用"偷窃"、"盗窃"、"小偷"等法律定性词汇
- 使用"可疑行为"、"异常模式"、"需要关注"等中性措辞
- 所有高风险结论必须附带"建议人工复核"

## 货架配置
系统当前配置3个货架：1号货架（零食区）、2号货架（饮料区）、3号货架（日用品区）。
如果用户问货架数量或配置，直接根据此信息回答。

## 回复风格
简洁、专业、友好。1-3句话即可，不要过度推销。
"""


def build_dashboard_snapshot(popularity_skill, anomaly_skill) -> dict:
    """构造仪表盘快照，不创建 LLM/Agent，供报表接口直接调用。"""
    pop_data = popularity_skill.get_stats()
    anom_summary = anomaly_skill.get_alert_summary()

    zones = pop_data.get("zones", {})
    ranking = sorted(
        zones.values(),
        key=lambda z: z.get("count", 0), reverse=True,
    )

    return {
        "timestamp": datetime.now().isoformat(),
        "popularity": {
            "top_zone": pop_data.get("top_zone"),
            "total_visitors": pop_data.get("total_visitors", 0),
            "ranking": [
                {
                    "zone_id": r.get("zone_id", ""),
                    "label": r.get("zone_label", ""),
                    "count": r.get("count", 0),
                    "avg_dwell": r.get("avg_dwell_seconds", 0),
                    "current_visitors": r.get("current_visitors", 0),
                }
                for r in ranking
            ],
        },
        "anomaly": {
            "total_alerts": anom_summary.get("total_alerts", 0),
            "high_risk_count": anom_summary.get("high_risk_count", 0),
            "watch_count": anom_summary.get("watch_count", 0),
        },
        "status": "running",
    }


# ==================== MasterAgent 类 ====================

class MasterAgent:
    """LangChain Agent 封装

    使用 create_agent 创建 LLM 驱动的 tool-calling agent，
    替代手写的意图分类和路由逻辑。
    """

    def __init__(
        self,
        popularity_skill: PopularitySkill,
        anomaly_skill: AnomalySkill,
        emotion_skill: SkillEmotion | None = None,
    ):
        """
        Args:
            popularity_skill: SKII-1 货架热度技能实例
            anomaly_skill: SKII-2 异常检测技能实例
            emotion_skill: SKII-3 表情分析技能实例（可选）
        """
        self.pop_skill = popularity_skill
        self.anom_skill = anomaly_skill
        self.emo_skill = emotion_skill

        # 创建 LLM
        self.llm = create_llm()

        # 定义 tools（闭包捕获 skill 实例）
        pop_skill_ref = popularity_skill
        anom_skill_ref = anomaly_skill

        @tool
        def get_shelf_popularity(query: str) -> str:
            """查询货架区域的实时热度数据。
返回每个货架的感兴趣人数、平均停留秒数、当前活跃访客数、热度排名。
当用户询问货架热度、哪个区域受欢迎、客流量、停留时长时调用此工具。

参数 query: 用户的问题（用于理解上下文）
            """
            stats = pop_skill_ref.get_stats()
            return json.dumps(stats, ensure_ascii=False, indent=2, default=str)

        @tool
        def get_anomaly_alerts(query: str) -> str:
            """查询可疑行为告警数据。
返回高风险告警列表、需关注告警列表、总告警数。
当用户询问异常行为、可疑人员、安全问题、告警情况时调用此工具。
注意：返回的是"可疑行为评分"，不是"偷窃判定"，所有高风险需人工复核。

参数 query: 用户的问题（用于理解上下文）
            """
            summary = anom_skill_ref.get_alert_summary()
            return json.dumps(summary, ensure_ascii=False, indent=2, default=str)

        emo_skill_ref = emotion_skill

        @tool
        def get_emotion_stats(query: str) -> str:
            """查询顾客表情/情绪统计数据。
返回表情分布（开心/悲伤/生气等）、正负情绪占比、情感趋势分析。
当用户询问顾客情绪、表情、心情、开心程度、满意度时调用此工具。

参数 query: 用户的问题（用于理解上下文）
            """
            if emo_skill_ref is None:
                return json.dumps({"error": "表情分析模块未启用"}, ensure_ascii=False)
            stats = emo_skill_ref.get_stats()
            trend = emo_skill_ref.get_trend()
            return json.dumps({"stats": stats, "trend": trend}, ensure_ascii=False, indent=2, default=str)

        self.tools = [get_shelf_popularity, get_anomaly_alerts]
        if emotion_skill is not None:
            self.tools.append(get_emotion_stats)

        # 创建 LangChain agent
        self.memory = create_memory()
        self.agent = create_agent(
            self.llm,
            self.tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self.memory,
        )

        # 会话历史（前端展示用）
        self._conversation_history: list[dict] = []

    # ==================== 主入口：自然语言查询 ====================

    def handle_query(
        self,
        query: str,
        context: dict | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """处理用户自然语言查询

        Args:
            query: 用户问题
            context: 可选的会话上下文
            session_id: 会话ID（thread_id，用于多轮对话记忆）

        Returns:
            {
                "answer": str,         # Agent 的自然语言回答
                "intent": str,         # 推测意图（从tool_calls反推）
                "confidence": float,
                "data": dict,          # 结构化数据（供前端图表）
                "alerts": list,        # 异常告警列表
                "suggestions": list,   # 建议操作
                "timestamp": str,
            }
        """
        try:
            # 调用 LangChain agent
            result = self.agent.invoke(
                {"messages": [HumanMessage(content=query)]},
                config={"thread_id": session_id},
            )
            answer = result["messages"][-1].content

            # 从 tool_calls 反推意图 + 数据
            intent = "general"
            pop_data = None
            anom_data = None
            for msg in result["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if "shelf_popularity" in tc.get("name", ""):
                            intent = "popularity"
                            pop_data = json.loads(tc.get("args", "{}").get("query", "{}"))
                        elif "anomaly_alerts" in tc.get("name", ""):
                            anom_data = json.loads(tc.get("args", "{}").get("query", "{}"))
                            if intent == "popularity":
                                intent = "both"
                            else:
                                intent = "anomaly"

            # 获取实际数据（如果 tool 被调用了）
            if pop_data is None and intent in ("popularity", "both", "general"):
                pop_data = self.pop_skill.get_stats()
            if anom_data is None and intent in ("anomaly", "both", "general"):
                anom_data = self.anom_skill.get_alert_summary()

            alerts = anom_data.get("high_risk", []) if anom_data else []
            suggestions = self._make_suggestions(pop_data, anom_data)

        except Exception as e:
            print(f"[MasterAgent] Agent 调用失败: {e}")
            # 降级：直接用 skill 数据拼回答
            pop_data = self.pop_skill.get_stats()
            anom_data = self.anom_skill.get_alert_summary()
            intent = "both"
            answer = self._fallback_answer(pop_data, anom_data)
            alerts = anom_data.get("high_risk", [])
            suggestions = self._make_suggestions(pop_data, anom_data)

        # 记录历史
        self._conversation_history.append({
            "query": query,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
        })
        if len(self._conversation_history) > 100:
            self._conversation_history = self._conversation_history[-50:]

        return {
            "answer": answer,
            "intent": intent,
            "confidence": 0.7,
            "data": {
                "popularity": pop_data,
                "anomaly": anom_data,
            },
            "alerts": alerts,
            "suggestions": suggestions,
            "timestamp": datetime.now().isoformat(),
        }

    # ==================== 事件驱动调度（保持纯数据，不经过 LLM） ====================

    def handle_event(self, event_type: str, event_data: dict) -> dict:
        """处理视频事件（自动触发，不走 LLM）"""
        if event_type == "crowd_gathering":
            return {
                "triggered_agent": "popularity",
                "message": f"检测到 {event_data.get('zone_id')} 区域人群聚集",
                "data": self.pop_skill.get_stats(),
            }
        elif event_type in ("trajectory_anomaly", "checkout_skip"):
            return {
                "triggered_agent": "anomaly",
                "message": f"检测到人员轨迹异常",
                "data": self.anom_skill.get_alert_summary(),
            }
        return {"triggered_agent": None, "message": "未知事件类型"}

    # ==================== 仪表盘快照（不经过 LLM） ====================

    def get_dashboard_snapshot(self) -> dict:
        """获取仪表盘数据"""
        return build_dashboard_snapshot(self.pop_skill, self.anom_skill)

    # ==================== 内部方法 ====================

    def _make_suggestions(self, pop_data: dict | None, anom_data: dict | None) -> list[str]:
        """生成建议"""
        suggestions = []
        if pop_data:
            zones = pop_data.get("zones", {})
            top_labels = []
            low_labels = []
            for zid, zdata in zones.items():
                if zdata.get("count", 0) > 10:
                    top_labels.append(zdata.get("zone_label", zid))
                elif zdata.get("count", 0) == 0:
                    low_labels.append(zdata.get("zone_label", zid))
            if top_labels:
                suggestions.append(f"热门区域 {', '.join(top_labels)} 客流集中，建议及时补货。")
            if low_labels:
                suggestions.append(f"{', '.join(low_labels)} 暂无顾客停留，可考虑调整陈列。")
        if anom_data:
            high_count = anom_data.get("high_risk_count", 0)
            if high_count > 0:
                suggestions.append(f"有 {high_count} 起高风险告警需立即人工复核。")
        return suggestions

    def _fallback_answer(self, pop_data: dict, anom_data: dict) -> str:
        """LLM 不通时的降级回答"""
        parts = []
        total = pop_data.get("total_visitors", 0)
        parts.append(f"当前累计 {total} 人次对货架商品感兴趣。")
        total_alerts = anom_data.get("total_alerts", 0)
        if total_alerts > 0:
            parts.append(f"发现 {total_alerts} 起可疑行为告警，建议查看仪表盘详情。")
        else:
            parts.append("暂无异常告警。")
        return " ".join(parts)

    # ==================== 流式输出 ====================

    async def handle_query_stream(self, query: str, session_id: str = "default"):
        """处理自然语言查询 — 流式返回每个 token

        Yields:
            str: 逐 token 输出，前端可实时渲染
        """
        try:
            async for event in self.agent.astream_events(
                {"messages": [HumanMessage(content=query)]},
                config={"thread_id": session_id},
                version="v2",
            ):
                kind = event.get("event", "")
                # 只推送 LLM 生成的 token，跳过 tool 调用事件
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield chunk.content

        except Exception as e:
            print(f"[MasterAgent] 流式调用失败: {e}")
            # 降级为非流式
            result = self.handle_query(query, session_id=session_id)
            yield result["answer"]

    def clear_history(self):
        self._conversation_history.clear()
