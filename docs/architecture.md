# CodeMentor AI 系统架构

## 组件职责

```mermaid
flowchart TB
    User[学习者]
    Dify[Dify Cloud Chatflow]
    Router[问题分类与路由]
    Knowledge[教材知识点库]
    CourseMap[教材课程地图库]
    SkillGraph[Java 技能图谱库]
    API[FastAPI Memory API]
    Supabase[(Supabase learner_memories)]

    User --> Dify
    Dify --> Router
    Router --> Knowledge
    Router --> CourseMap
    Router --> SkillGraph
    Dify --> API
    API --> Supabase
```

| 组件 | 职责 |
| --- | --- |
| Dify Chatflow | 对话编排、意图分类、检索、出题、讲评、学习报告展示。 |
| 教材知识点库 | 一个知识点一个 Markdown，提供回答、讲评和题目事实依据。 |
| 教材课程地图库 | 提供稳定 topic_id、先修依赖和 `next_topic_id`，决定学习顺序。 |
| Java 技能图谱库 | 提供原子技能、技能 ID、常见误区和出题定位。 |
| FastAPI Memory API | 鉴权、待评估题管理、证据写入、状态转换和报告统计。 |
| Supabase | 每位学习者一条 JSONB 结构化 Memory 记录。 |

## 答题与 Memory 数据流

```mermaid
sequenceDiagram
    participant U as 学习者
    participant D as Dify
    participant A as Memory API
    participant S as Supabase

    U->>D: 请求练习题或面试题
    D->>A: 创建 active_assessment
    A->>S: 保存待评估题
    D-->>U: 返回一道题
    U->>D: 提交答案或代码
    D->>D: 判断 answer / cancel / new_request
    D->>D: LLM 结构化评估
    D->>A: 写入 evidence
    A->>A: 计算主题和技能状态
    A->>S: 更新结构化 Memory
    D-->>U: 返回讲评与改进建议
```

## 状态规则

主题状态由后端按有效练习题和面试题证据计算：

```mermaid
stateDiagram-v2
    [*] --> learning: 首次有效评估或学习自述
    learning --> learning: 有效评估少于 3 次
    learning --> mastered: 至少 3 次且正确率 >= 60%
    learning --> reviewing: 至少 3 次且正确率 < 60%
    reviewing --> mastered: 后续证据使正确率达到 60%
    mastered --> reviewing: 后续证据使正确率低于 60%
```

`learning` 表示开始学习，不代表完成。学习报告的课程完成率只统计 `mastered` 主题。

## 继续学习与报告

```mermaid
flowchart LR
    M[读取 Memory] --> R{主题状态}
    R -->|reviewing| Review[复习当前主题]
    R -->|learning| Practice[继续巩固当前主题]
    R -->|mastered| Next[根据 next_topic_id 进入下一主题]
    R -->|无记录| Start[从课程地图起点开始]

    M --> Report[报告 API 确定性汇总]
    Report --> View[学习报告生成器]
```

报告 API 负责统计主题数量、正确率、状态和课程完成率；Dify LLM 只负责把返回的结构化数据整理为可读文本，不能自行计算或改变状态。
