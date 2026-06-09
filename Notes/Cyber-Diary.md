## 2026-06-04

### 😊 心情：复杂但充实的

凌晨四点睡不着，下着小雨出门溜达，耳机里放着《Towards the Light》。

### 📖 今天学到的

**1. Git & GitHub 全流程**
- `git config` 配置用户名和邮箱
- `ssh-keygen` 生成 SSH 密钥连接 GitHub
- `git init` → `git add .` → `git commit -m "xxx"` → `git push`
- 用 `gh` CLI 创建仓库、Personal Access Token 认证

**2. Python 函数（def）**
- `def xxx():` 定义函数，把代码打包
- 参数：`def save_study(study, mood):` 把数据传进去
- Cyber Mentor 从流水账重构为4个函数：`welcome()` `show_history()` `save_study()` `update_diary()`

**3. RAG（检索增强生成）**
- 模型记忆有限，需要外部存储
- RAG = 检索 + 生成：先把相关内容搜出来，再喂给模型
- 手搓了一个简易 RAG 系统：`rag.py`，用关键词从日记和学习记录中检索

**4. 系统运维**
- 代理 `127.0.0.1:7897` 掉线会导致 Telegram 失联
- 电脑休眠会让 Gateway 冻结
- 调了电源设置：插电永不睡眠

### 💡 今天的感悟

> 学了 `def` 马上就用到自己的项目里——学以致用是最好的学习方式。
> 
> RAG 这个概念，跟硅谷砸几亿美金做的企业级系统，底层逻辑是一样的。
> 
> GitHub 不是炫耀，是把自己放在一个"被看见"的位置。

### 🚀 AI-system 进度

| 版本 | 更新 |
|---|---|
| V0.1-V0.3 | Cyber Mentor 学习记录器 |
| V2.0.5 | 函数化重构 |
| V0.3 RAG | 简易检索系统 |
| V3.0 | 菜单交互 + RAG v0.2 接真模型 |

## 2026-06-06

### 😊 心情：还行

通宵打游戏到天亮，刷抖音看到"缺少变现环境"的说法，跟小刘聊了一晚上。

### 📖 今天做的

**Cyber Mentor 大升级**
- `main.py` V3.0：加了5选项菜单（记录学习/查看历史/搜索记忆/AI问答/退出）
- `src/rag.py` V0.2：检索结果可以喂给 AI 模型做智能问答
- 装了 `openai` 和 `python-dotenv` 库
- 配了 `.env` 文件，接 DeepSeek API（还没填 key）
- 修了 Windows 终端 emoji 编码问题

### 💡 小刘说的

> 用三个东西描述需求：痛点（哪里不爽）→ 目标（想变成啥样）→ 上下文（学到哪了）
> 
> 这样我才能精准动手。

### 🚀 待办

- [ ] 去 DeepSeek 注册拿 API Key，填进 .env
- [ ] 跑 `python main.py` 选 4 试试 AI 问答

## 2026-06-09

- ?? ���飺8/10
- ??? ��ǩ��AI����Ŀ������
- ?? ѧϰ����TradingAgents�������彻��ϵͳ��BTC��ETH�ز�,AI����Underweight/Hold�ź�,�����ж���ȷ���˽���100x�ܸ˱��ַ���(���vsȫ������)��Cyber Mentor������v4.1(��ǩ����+TF-IDF��������+jieba�ִ�)��TradingAgents CLI�������̡�
