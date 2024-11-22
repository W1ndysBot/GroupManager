# GroupManager

## 命令

ban@ 时间 禁言 x 秒，默认 60 秒

unban@ 解除禁言

banme 随机禁言自己随机秒

banrandom 随机禁言一个群友随机秒

banall 全员禁言

unbanall 全员解禁

t@ 踢出指定用户

del 撤回消息(需要回复要撤回的消息)

vc-on 开启视频监控

vc-off 关闭视频监控

wf-on 开启欢迎欢送

wf-off 关闭欢迎欢送

## 更新日志

### 2024-11-22

- fix: 修复 banme 打破记录时，没有更新当前用户今日最高禁言记录的问题
- feat: 新增群今日禁言排行“banmerank”

### 2024-8-24

- fix: 增加一层对 user_id 和 group_id 的转换，以字符串形式存储，避免出现 int 类型比较时出现的问题

### 2024-8-12

- refactor: 重构代码，精简命令，分离大型功能
- feat: banme 新增排行榜
