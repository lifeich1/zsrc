# gtr7/hermes-podman —— Hermes Agent 容器

> 给维护者与 AI 助手的索引：先读本文件，**不要为看结构而通读 compose.yaml**。
> 上游文档：[Hermes Docker Setup](https://hermes-agent.nousresearch.com/docs/user-guide/docker)。

## 职责

在 GTR7（`nixos-gtr7`）上用 podman + compose 常驻运行 Nous Research 的
[Hermes Agent](https://github.com/NousResearch/hermes-agent)（`gateway run` 模式），
并把仓库里的 [`calory`](../../calory/README.md) CLI 挂进容器，
让 agent 能记录/查询每日热量。

## 文件一览

| 路径 | 内容 |
| --- | --- |
| `compose.yaml` | 服务定义：镜像、端口、挂载、环境变量、userns、资源限制 |
| `Dockerfile` | derived image：给 `stage2-hook.sh` 打 keep-id 兼容补丁（`usermod -o`） |
| `.env.example` | 部署参数模板；`cp .env.example .env` 后按需改，`.env` 不入库 |
| `bin/cal` | 容器内 `cal` wrapper：挑一个 ≥3.10 的 Python 跑 `/calory/cal` |
| `skills/calory/SKILL.md` | 给 agent 的 calory 用法说明（通过 cont-init.d 脚本软链接到 `/opt/data/skills/calory`，见 `Dockerfile`） |

## 不变量与约定

- **数据全在宿主**：`${HERMES_DATA_DIR}`（默认 `/home/fool/.hermes`）挂到 `/opt/data`，
  含 API key（`.env`）、`config.yaml`、sessions、skills、logs。容器无状态；
  升级 = pull 上游镜像 + rebuild derived image + 重建容器。
  两个容器不要同时挂同一个数据目录。
- **密钥不入库**：API key 由 `hermes setup` 写进 `${HERMES_DATA_DIR}/.env`；
  本目录的 `.env` 只放镜像/路径/UID 参数，且已被根 `.gitignore` 排除。
- **属主**：`userns_mode: keep-id` + `PUID/PGID`（默认 1000/100）让容器内进程以宿主 `fool`
  身份写盘，这样 `calory/data/` 下新文件属主仍是 `fool`，git 提交与多设备同步才正常。
  镜像内服务默认跑在 UID 10000，不改这两个变量会写出宿主 subuid 属主的文件。
  keep-id 会在容器内注入宿主 UID 的用户条目（`fool:1000`），与仓里 `PUID=1000` 的
  usermod 冲突。`Dockerfile` 给 `usermod` 加 `-o`（允许非唯一 UID）绕过此冲突。
- **`/opt/hermes` 是只读安装树**：不要在运行时往里装东西（官方设计如此）。
  `Dockerfile` 只打两个补丁：`stage2-hook.sh` 的一行 sed（`usermod -o`）
  和 `cont-init.d/50-link-skills`（启动时把 calory skill 软链接进数据目录），
  不改变镜像的只读设计。
- **skills 挂载不嵌套**：Podman `keep-id` 下，往已挂载的 `/opt/data` 子路径再挂载
  （如 `/opt/data/skills/calory`）会因用户命名空间遮蔽而失效。calory skill 挂到独立路径
  `/opt/hermes-skills-calory`，由 `50-link-skills` 在 Hermes 启动前软链接到
  `/opt/data/skills/calory`；可写——agent 对 `SKILL.md` 的修改会写回仓库，容器重启不丢，
  但改动会让 `git status` 变脏，注意取舍。
  `HERMES_WRITE_SAFE_ROOT` 设为 `"/opt/data:/opt/hermes-skills-calory"`，
  因此 write_file/patch 也能直接写 `/opt/hermes-skills-calory/SKILL.md`，不依赖 shell 命令。
- **两个端口，暴露面不同**：`127.0.0.1:8642` 是 gateway 的 OpenAI 兼容 API，只绑回环；
  `9119` 是 dashboard backend（Hermes 客户端与手机浏览器连的就是它），按 `.env` 里的
  `HERMES_DASHBOARD_BIND` 绑到局域网（默认 `0.0.0.0`）。
- **dashboard 强制认证**：绑定非回环地址时 Hermes 强制启用认证 gate，没配 provider 就
  fail closed 不启动。凭据（`HERMES_DASHBOARD_BASIC_AUTH_USERNAME` / `_PASSWORD` / `_SECRET`）
  放在仓库外的 `.env` 里，不入库。
- **宿主防火墙是另一层**：NixOS firewall 默认拒绝未声明入站，需在 nixcf 的 GTR7 host
  配置里放行 9119，局域网才连得上（那个仓库不在本目录范围内）。

## 运行方式

依赖：`podman`（本机 5.8.6 已装）+ `podman-compose`（**尚未安装**）。
临时使用：`nix shell nixpkgs#podman-compose --command podman-compose up -d`；
长期使用建议把 `podman-compose` 加进 NixOS/home-manager 配置。

```bash
cd gtr7/hermes-podman
cp .env.example .env                       # 首次：按需改路径/UID

# 首次：构建 derived image（stage2-hook.sh 的 keep-id 补丁，见 Dockerfile）
podman build -t hermes-agent:local .

# 局域网开放 dashboard 前必须填好这三项，否则 dashboard fail closed 起不来：
#   HERMES_DASHBOARD_BASIC_AUTH_USERNAME / _PASSWORD
#   HERMES_DASHBOARD_BASIC_AUTH_SECRET=$(openssl rand -base64 32)

# 首次初始化：交互式向导，写入 API key 到 ${HERMES_DATA_DIR}/.env
podman-compose run --rm hermes setup

podman-compose up -d                       # 启动
podman-compose logs -f                     # 跟随日志
podman-compose down                        # 停止并删除容器（数据保留）

# 升级镜像（derived image：先 pull 上游，再 rebuild）
podman pull nousresearch/hermes-agent:latest
podman build -t hermes-agent:local .
podman-compose up -d --force-recreate
```

宿主侧日志（容器重建后仍保留）：`${HERMES_DATA_DIR}/logs/gateways/default/current`。

## calory 接入

| 宿主 | 容器内 | 说明 |
| --- | --- | --- |
| `../../calory`（即仓库 `calory/`） | `/calory` | 读写挂载，`CALORY_HOME=/calory` |
| `skills/calory/SKILL.md` | `/opt/hermes-skills-calory/SKILL.md` ⤵ `/opt/data/skills/calory/SKILL.md` | 可写软链接（cont-init.d），agent 可修改，重启不丢；已入 `HERMES_WRITE_SAFE_ROOT` 白名单，write_file 也能写 |
| `bin/cal` | `/usr/local/bin/cal` | 只读，容器内直接 `cal show` |

容器内等价命令：

```bash
podman exec -it hermes cal show          # 当天明细与合计
podman exec -it hermes cal add lunch 鸡胸肉 200g
podman exec -it hermes cal week
```

`cal` 会自动挑选解释器：优先系统 `python3`，否则用镜像自带的
`/opt/hermes/.venv/bin/python`（官方镜像基于 debian:13.4，Python 3.13）。

**写入后的收尾**：agent 记录的内容是仓库 `calory/data/` 下的 JSON，
需要在宿主手动 `git add calory/data && git commit` 才会同步。

## 局域网接入（Hermes 客户端 / 手机浏览器）

dashboard backend 已在 compose 里开好（`HERMES_DASHBOARD=1` +
`HERMES_DASHBOARD_HOST=0.0.0.0`），局域网地址是 `http://<gtr7-ip>:9119`：

1. 先确认 `.env` 里三项凭据都已填（见「运行方式」），再 `podman-compose up -d`；
2. Hermes 客户端：Settings → Gateways → Remote gateway，URL 填 `http://<gtr7-ip>:9119`，
   用 `.env` 里的用户名/密码登录；手机浏览器直接打开同一个 URL 也能用 web dashboard；
3. 客户端只需要这一个端口——profile 切换、chat 都走 9119，不必再连 8642。

确认认证 gate 已生效：

```bash
curl -s http://<gtr7-ip>:9119/api/status | python3 -m json.tool | head -5
# 期望 auth_required=true 且 auth_providers 含 "basic"
```

安全提示：非回环绑定必定要求登录，但**不要**把它暴露到公网——按上游建议走可信网络
（Tailscale 等），或把 `HERMES_DASHBOARD_BIND` 收窄到具体 IP。

## 验证与排错

```bash
podman-compose config                              # 校验 compose 语法与变量替换
podman exec -it hermes python3 -V                  # 确认容器内 Python
podman exec -it hermes cal show                    # 确认 calory 可用
ls -l ../../calory/data/meals                      # 确认属主是 fool 而不是 subuid
curl -s http://127.0.0.1:9119/api/status           # dashboard 是否起来（auth_required 应为 true）
ss -ltnp | grep 9119                               # 确认宿主在 0.0.0.0:9119 监听
```

- `Permission denied`：检查 `${HERMES_DATA_DIR}` 属主与 `.env` 里的 `PUID/PGID` 是否等于 `id -u` / `id -g`。
- 启动日志出现 `usermod: UID '...' already exists` 后连锁 `Permission denied`：keep-id 已注入宿主
  uid 条目，`PUID` 触发的 `usermod` 撞车导致 stage2 提前退出、chown 被跳过。先 rebuild
  derived image（`podman build -t hermes-agent:local .`）再重建容器；补丁原理见 `Dockerfile`。
- 容器起来就退出：多为 `.env` 缺失或无效，先跑 `setup`。
- dashboard 起不来、日志出现 fail-closed 提示：`.env` 少了 `HERMES_DASHBOARD_BASIC_AUTH_*`（非回环绑定必须配 provider）。
- 本机能开 9119、局域网连不上：NixOS firewall 未放行该端口（见 nixcf 的 GTR7 host 配置）。
- 每次重启都要重新登录：`HERMES_DASHBOARD_BASIC_AUTH_SECRET` 没设或每次都在变。
- 浏览器工具报错：compose 已设 `shm_size: 1gb`，仍失败再查内存限制（默认 4G）。
- 若 `userns_mode: keep-id` 在某个 podman 版本下不生效，退化为
  `podman run --userns=keep-id`，或把 `PUID/PGID` 设成 `calory/data` 实际属主。

## 改动落点

| 需求 | 改动点 |
| --- | --- |
| 换上游镜像版本 / 加环境变量 | `compose.yaml` 的 `image` / `build` / `environment`，改完 rebuild |
| 改 keep-id 兼容补丁 / 启动时 skills 软链接 | `Dockerfile`（`stage2-hook.sh` 的 sed 补丁 + `50-link-skills` 脚本） |
| 改数据目录、UID/GID | `.env`（从 `.env.example` 复制） |
| 关闭 / 收窄局域网访问 | `.env` 里 `HERMES_DASHBOARD_BIND=127.0.0.1`，或删掉 `compose.yaml` 的 9119 映射并设 `HERMES_DASHBOARD: "0"` |
| 改 dashboard 凭据 | `.env`（`HERMES_DASHBOARD_BASIC_AUTH_USERNAME` / `_PASSWORD` / `_SECRET`） |
| 调整 calory 用法说明 | `skills/calory/SKILL.md` |
| 调整容器内解释器选择 | `bin/cal` |
