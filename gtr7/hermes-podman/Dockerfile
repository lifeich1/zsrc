# Derived image —— 只打一个 keep-id 兼容补丁。
#
# 背景：compose 用 `userns_mode: keep-id`（rootless podman 下让容器内 uid 1000
# 映射到宿主 fool:1000，写盘属主才正确）。keep-id 会向容器注入与宿主 UID 匹配的
# 用户条目（如 `fool:*:1000:100`），而官方镜像 stage2-hook.sh 在收到 PUID=1000
# 时执行 `usermod -u 1000 hermes`，撞上已存在的 UID 1000 报
# `usermod: UID '1000' already exists`；脚本带 `set -eu`，usermod 失败即整体
# 退出，后续 chown /opt/data 被跳过，启动连锁 Permission denied。
#
# 修复：给 usermod 加 `-o`（允许非唯一 UID）——与脚本里 groupmod 已带的
# `-o ... || true` 容错同一思路。改后 hermes 与注入的 fool 共享 uid 1000，
# 后续 `chown hermes:hermes` 正确落到宿主 1000:100，写盘与 calory 属主全对。
#
# 升级流程：先 `podman pull nousresearch/hermes-agent:latest`，再 rebuild 本镜像。
FROM nousresearch/hermes-agent:latest

# 只匹配 `usermod -u `（脚本里唯一的一处是 UID remap；`usermod -aG` 不受影响）
RUN sed -i 's/usermod -u /usermod -o -u /' /opt/hermes/docker/stage2-hook.sh

# compose.yaml 把 ./skills/calory 挂到 /opt/hermes-skills-calory（独立路径，
# 不嵌套在 /opt/data 下，避免 Podman keep-id 的子路径嵌套冲突）。
# 在 Hermes 启动前创建软链接 /opt/data/skills/calory -> /opt/hermes-skills-calory。
# 可写：agent 对 SKILL.md 的修改会写回仓库，容器重启不丢。
RUN mkdir -p /etc/cont-init.d && \
    printf '%s\n' \
      '#!/bin/sh' \
      'if [ -d /opt/hermes-skills-calory ]; then' \
      '  mkdir -p /opt/data/skills' \
      '  ln -sf /opt/hermes-skills-calory /opt/data/skills/calory' \
      'fi' \
    > /etc/cont-init.d/50-link-skills && \
    chmod +x /etc/cont-init.d/50-link-skills
