# AI Daily Report Generator

## 功能描述

### 1. 数据采集
- 使用crawl4ai进行新闻爬取 (pip install crawl4ai)
- 支持的新闻源:
    * AI专业媒体 (例如: AI News, MIT Technology Review等)
    * 主流科技媒体AI频道
    * AI研究机构官方发布
    * 优先获取"https://techcrunch.com/"网站的AI新闻内容
- 定时任务配置
- 自动去重机制

### 2. 内容处理
- 使用groq进行新闻摘要
- 新闻分类:
    * 技术创新
    * 商业应用
    * 政策法规
    * 研究进展
- 关键信息提取
- 情感分析
- 热度排序

### 3. 日报生成
- 固定栏目:
    * 今日头条
    * 技术动态
    * 产业资讯
    * 政策动向
- 格式化处理
- 图片处理
- 关键词标注

### 4. Notion集成
- API配置
- Database结构:
    * 日期索引
    * 分类标签
    * 内容字段
    * 元数据
- 自动清理历史记录
- 版本控制

### 5. 扩展功能
- 订阅推送
- 数据分析
- 周报/月报生成
- 多语言支持
- 反馈机制

## 使用说明
1. 安装依赖
2. 配置参数
3. 运行服务
4. 查看结果

## 配置项
- API密钥配置
- 爬虫参数
- 定时任务
- Notion设置
- 其他自定义项

## 注意事项
- 遵守网站爬虫规则
- API使用限制
- 数据安全
- 内容版权

## 开发计划
- [ ] 基础功能实现
- [ ] 测试和优化
- [ ] 功能扩展
- [ ] 文档完善