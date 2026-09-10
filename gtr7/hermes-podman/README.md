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
| `.env.example` | 部署参数模板；`cp .env.example .env` 后按需改，`.env` 不入库 |
| `bin/cal` | 容器内 `cal` wrapper：挑一个 ≥3.10 的 Python 跑 `/calory/cal` |
| `skills/calory/SKILL.md` | 给 agent 的 calory 用法说明（挂到 `/opt/data/skills/calory`） |

## 不变量与约定

- **数据全在宿主**：`${HERMES_DATA_DIR}`（默认 `/home/fool/.hermes`）挂到 `/opt/data`，
  含 API key（`.env`）、`config.yaml`、sessions、skills、logs。镜像无状态，升级只 pull + 重建。
  两个容器不要同时挂同一个数据目录。
- **密钥不入库**：API key 由 `hermes setup` 写进 `${HERMES_DATA_DIR}/.env`；
  本目录的 `.env` 只放镜像/路径/UID 参数，且已被根 `.gitignore` 排除。
- **属主**：`userns_mode: keep-id` + `PUID/PGID`（默认 1000/100）让容器内进程以宿主 `fool`
  身份写盘，这样 `calory/data/` 下新文件属主仍是 `fool`，git 提交与多设备同步才正常。
  镜像内服务默认跑在 UID 10000，不改这两个变量会写出宿主 subuid 属主的文件。
- **`/opt/hermes` 是只读安装树**：不要在运行时往里装东西（官方设计如此）。
  calory 是零依赖纯标准库脚本，直接挂载即可，不需要 derived image。
- **端口只绑回环**：`127.0.0.1:8642`（gateway 的 OpenAI 兼容 API）。
  要开 dashboard 需 `HERMES_DASHBOARD=1` 并自行放开 `9119`。

## 运行方式

依赖：`podman`（本机 5.8.6 已装）+ `podman-compose`（**尚未安装**）。
临时使用：`nix shell nixpkgs#podman-compose --command podman-compose up -d`；
长期使用建议把 `podman-compose` 加进 NixOS/home-manager 配置。

```bash
cd gtr7/hermes-podman
cp .env.example .env                       # 首次：按需改路径/UID

# 首次初始化：交互式向导，写入 API key 到 ${HERMES_DATA_DIR}/.env
podman-compose run --rm hermes setup

podman-compose up -d                       # 启动
podman-compose logs -f                     # 跟随日志
podman-compose down                        # 停止并删除容器（数据保留）

# 升级镜像
podman pull nousresearch/hermes-agent:latest
podman-compose up -d --force-recreate
```

宿主侧日志（容器重建后仍保留）：`${HERMES_DATA_DIR}/logs/gateways/default/current`。

## calory 接入

| 宿主 | 容器内 | 说明 |
| --- | --- | --- |
| `../../calory`（即仓库 `calory/`） | `/calory` | 读写挂载，`CALORY_HOME=/calory` |
| `skills/calory/SKILL.md` | `/opt/data/skills/calory/SKILL.md` | 只读，agent 按需加载 |
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

## 验证与排错

```bash
podman-compose config                              # 校验 compose 语法与变量替换
podman exec -it hermes python3 -V                  # 确认容器内 Python
podman exec -it hermes cal show                    # 确认 calory 可用
ls -l ../../calory/data/meals                      # 确认属主是 fool 而不是 subuid
```

- `Permission denied`：检查 `${HERMES_DATA_DIR}` 属主与 `.env` 里的 `PUID/PGID` 是否等于 `id -u` / `id -g`。
- 容器起来就退出：多为 `.env` 缺失或无效，先跑 `setup`。
- 浏览器工具报错：compose 已设 `shm_size: 1gb`，仍失败再查内存限制（默认 4G）。
- 若 `userns_mode: keep-id` 在某个 podman 版本下不生效，退化为
  `podman run --userns=keep-id`，或把 `PUID/PGID` 设成 `calory/data` 实际属主。

## 改动落点

| 需求 | 改动点 |
| --- | --- |
| 换镜像版本 / 加环境变量 | `compose.yaml` 的 `image` / `environment` |
| 改数据目录、UID/GID | `.env`（从 `.env.example` 复制） |
| 开 dashboard | `compose.yaml` 里 `HERMES_DASHBOARD: "1"` + 放开 `9119` |
| 调整 calory 用法说明 | `skills/calory/SKILL.md` |
| 调整容器内解释器选择 | `bin/cal` |
